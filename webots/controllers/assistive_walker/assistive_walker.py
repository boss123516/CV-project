"""Walking animation and synchronized stereo ROS 2 bridge (no detector)."""
from pathlib import Path
import json
import math
import numpy as np
import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import TransformStamped
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Bool, Float32, String
from tf2_ros import TransformBroadcaster
from upstream_pedestrian import Pedestrian

ROOT = Path(__file__).resolve().parents[2]
BASELINE = 0.12
PERIOD_MS = 64


def quaternion(m):
    # Eigenvector formulation also handles 180 degree rotations.
    from math import sqrt
    trace = float(np.trace(m))
    if trace > 0:
        s = sqrt(trace + 1) * 2
        return [(m[2,1]-m[1,2])/s, (m[0,2]-m[2,0])/s, (m[1,0]-m[0,1])/s, s/4]
    i = int(np.argmax(np.diag(m))); j = (i+1)%3; k = (i+2)%3
    s = sqrt(1 + m[i,i] - m[j,j] - m[k,k]) * 2
    q = [0.,0.,0.,0.]; q[i]=s/4; q[j]=(m[i,j]+m[j,i])/s; q[k]=(m[i,k]+m[k,i])/s; q[3]=(m[k,j]-m[j,k])/s
    return q


def tf_message(parent, child, translation, rotation, stamp):
    t=TransformStamped(); t.header.stamp=stamp; t.header.frame_id=parent; t.child_frame_id=child
    t.transform.translation.x=float(translation[0]); t.transform.translation.y=float(translation[1]); t.transform.translation.z=float(translation[2])
    q=quaternion(rotation)
    t.transform.rotation.x=float(q[0]); t.transform.rotation.y=float(q[1]); t.transform.rotation.z=float(q[2]); t.transform.rotation.w=float(q[3])
    return t


class AssistiveWalker(Pedestrian):
    def __init__(self):
        super().__init__()
        self.dt=int(self.getBasicTimeStep()); self.root=self.getSelf()
        self.position=self.root.getField('translation')
        self.joints={name:self.root.getField(name) for name in self.joint_names}
        self.cane=self.getFromDef('CANE_SWEEP').getField('rotation')
        self.x=0.; self.distance=0.; self.speed=0.65; self.paused=False
        self.hold=0.; self.stations=set(); self.lap=0; self.frame=0
        self.active_stage=-1
        self.targets=[self.getFromDef(name).getField('translation') for name in ['BENCH','CONE','TARGET_PERSON']]
        self.last_publish=-1.; self.last_status=-1.; self.last_save=-1.
        self.keyboard=self.getKeyboard(); self.keyboard.enable(self.dt); self.previous_key=-1
        rclpy.init(args=[]); self.node=rclpy.create_node('assistive_walker')
        self.clock=self.node.create_publisher(Clock,'/clock',10)
        self.status=self.node.create_publisher(String,'/assistive/status',10)
        self.ground_truth=self.node.create_publisher(String,'/assistive/ground_truth/objects',10)
        self.tf=TransformBroadcaster(self.node)
        self.node.create_subscription(Bool,'/assistive/pause',lambda m:setattr(self,'paused',m.data),10)
        self.node.create_subscription(Float32,'/assistive/speed',lambda m:setattr(self,'speed',max(0.,min(1.2,float(m.data)))),10)
        self.cameras=[]
        for side in ['left','right']:
            c=self.getDevice(side+'_camera'); c.enable(PERIOD_MS)
            if side=='left': c.recognitionEnable(PERIOD_MS)
            f=c.getWidth()/(2*math.tan(c.getFov()/2)); cx=c.getWidth()/2; cy=c.getHeight()/2
            info=CameraInfo(width=c.getWidth(),height=c.getHeight(),distortion_model='plumb_bob')
            info.header.frame_id=f'assistive/{side}_camera_optical_frame'
            info.d=[0.]*5; info.k=[f,0.,cx,0.,f,cy,0.,0.,1.]; info.r=[1.,0.,0.,0.,1.,0.,0.,0.,1.]
            info.p=[f,0.,cx,-f*BASELINE if side=='right' else 0.,0.,f,cy,0.,0.,0.,1.,0.]
            prefix=f'/assistive/stereo/{side}'
            self.cameras.append((side,c,self.node.create_publisher(Image,prefix+'/image_raw',2),self.node.create_publisher(CameraInfo,prefix+'/camera_info',2),info))
        pitch=.12; cp=math.cos(pitch); sp=math.sin(pitch)
        self.camera_rotation=np.array([[cp,0,sp],[0,1,0],[-sp,0,cp]]) @ np.array([[0,0,1],[-1,0,0],[0,-1,0]])
        self.node.get_logger().info('Stereo ready: /assistive/stereo/{left,right}/image_raw | 640x480 | 15.625 Hz | baseline 0.12 m')
        self.node.get_logger().info('P: pause/resume walking | R: restart route | speed/pause also available as ROS topics. Ground truth is SIMULATOR data, not YOLO.')

    def reset_route(self):
        self.x=0.; self.distance=0.; self.stations.clear(); self.hold=0.; self.lap+=1

    def update_walking(self):
        key=self.keyboard.getKey()
        if key != self.previous_key:
            if key in [ord('P'),ord(' ')]: self.paused=not self.paused
            if key==ord('R'): self.reset_route()
        self.previous_key=key
        moving=not self.paused and self.hold<=0
        if not self.paused:
            if self.hold>0: self.hold=max(0.,self.hold-self.dt/1000)
            else:
                dx=self.speed*self.dt/1000; self.x+=dx; self.distance+=dx
                for station in [3.,11.,19.]:
                    if self.x>=station and station not in self.stations:
                        self.stations.add(station); self.hold=2.5
                if self.x>25.5: self.reset_route()
        phase=self.distance/self.CYCLE_TO_DISTANCE_RATIO
        sequence=int(phase)%8; ratio=phase-int(phase)
        for i,name in enumerate(self.joint_names):
            value=self.angles[i][sequence]*(1-ratio)+self.angles[i][(sequence+1)%8]*ratio
            if name=='headAngle': value=0.
            if name=='rightArmAngle': value=-.12
            if name=='rightLowerArmAngle': value=-.25
            self.joints[name].setSFFloat(value)
        # Restrained vertical motion keeps the stereo rig parallel while walking.
        bob=.012*math.sin(phase*math.pi/2) if moving else 0.
        self.position.setSFVec3f([self.x,0.,1.27+bob])
        self.cane.setSFRotation([0.,0.,1.,.22*math.sin(phase*math.pi/4)])
        stage=min(2,int(self.x//8))
        if stage!=self.active_stage:
            for i,field in enumerate(self.targets):
                poses=[[6.,1.02,0.],[14.,-.78,0.],[22.,.85,1.27]]
                pose=poses[i]
                if i!=stage: pose[1]=40.
                field.setSFVec3f(pose)
            self.active_stage=stage
        return bob

    def run(self):
        while rclpy.ok():
            rclpy.spin_once(self.node,timeout_sec=0.)
            bob=self.update_walking()
            if self.step(self.dt)==-1: break
            seconds=self.getTime(); ns=round(seconds*1e9)
            stamp=Time(sec=ns//10**9,nanosec=ns%10**9)
            self.clock.publish(Clock(clock=stamp))
            # Pose is set before step; camera pixels, time and TF describe the same simulation tick.
            transforms=[tf_message('world','assistive/base_link',[self.x,0,0],np.eye(3),stamp)]
            for side,c,_,_,_ in self.cameras:
                transforms.append(tf_message('assistive/base_link',f'assistive/{side}_camera_optical_frame',[.235,.06 if side=='left' else -.06,1.67+bob],self.camera_rotation,stamp))
            self.tf.sendTransform(transforms)
            if ns % (PERIOD_MS*1_000_000) != 0: continue
            self.last_publish=seconds
            for side,c,pub,info_pub,info in self.cameras:
                data=c.getImage()
                if not data: continue
                msg=Image(); msg.header.stamp=stamp; msg.header.frame_id=info.header.frame_id
                msg.width=c.getWidth(); msg.height=c.getHeight(); msg.encoding='bgra8'; msg.step=msg.width*4; msg.data=bytes(data)
                pub.publish(msg); info.header.stamp=stamp; info_pub.publish(info)
            self.frame+=1
            objects=[]
            for obj in self.cameras[0][1].getRecognitionObjects():
                p=list(obj.getPosition()); center=list(obj.getPositionOnImage()); size=list(obj.getSizeOnImage())
                label=obj.getModel(); label=label.decode() if isinstance(label,bytes) else label
                objects.append({'id':obj.getId(),'class':label,'range_m':round(math.sqrt(sum(v*v for v in p)),3),'camera_position_m':p,'center_px':center,'size_px':size})
            self.ground_truth.publish(String(data=json.dumps({'source':'webots_recognition_ground_truth','simulation_time':seconds,'objects':objects})))
            if seconds-self.last_status>=.25:
                state={'source':'simulation_only_no_yolo','simulation_time':round(seconds,3),'x_m':round(self.x,3),'speed_mps':self.speed,'paused':self.paused,'holding':self.hold>0,'lap':self.lap,'frames':self.frame,'visible_objects':len(objects),'baseline_m':BASELINE,'objects':objects}
                self.status.publish(String(data=json.dumps(state))); self.last_status=seconds
                (ROOT/'logs/status.json').write_text(json.dumps(state,indent=2))
            if seconds-self.last_save>=2:
                for side,c,_,_,_ in self.cameras: c.saveImage(str(ROOT/f'logs/{side}_latest.png'),100)
                self.last_save=seconds
        self.node.destroy_node(); rclpy.shutdown()


if __name__=='__main__':
    AssistiveWalker().run()
