"""Walking animation and synchronized stereo ROS 2 bridge (no detector)."""
from pathlib import Path
from array import array
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
from walking_motion import walking_pose,STRIDE_M

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
        self.viewpoint=self.getFromDef('OVERVIEW')
        self.view_position=np.array([-4.,-6.,4.])
        self.follow_view=True
        self.joints={name:self.root.getField(name) for name in self.joint_names}
        self.cane=self.getFromDef('CANE_SWEEP').getField('rotation')
        self.x=0.; self.y=0.; self.heading=0.; self.distance=0.; self.speed=.72; self.actual_speed=0.; self.paused=False
        self.scene=json.loads((ROOT/"config/urban_scene.json").read_text())
        self.path=np.array(self.scene["path_xy"],float)
        self.crossing_progress=None
        self.hold=0.; self.stations=set(); self.lap=0; self.frame=0
        self.target_person=self.getFromDef('TARGET_PERSON')
        self.target_person_joints={name:self.target_person.getField(name) for name in self.joint_names}
        self.root_rotation=self.root.getField('rotation')
        self.last_publish=-1.; self.last_status=-1.; self.last_save=-1.
        self.scenario=self.scene["scenarios"][0]
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
        self.node.get_logger().info('Urban route: fixed obstacles and a crossing pedestrian. Gait uses stance-foot IK. Perception runs in a separate stereo image node.')

    def reset_route(self):
        self.x=0.;self.y=0.;self.heading=0.;self.distance=0.;self.actual_speed=0.
        self.stations.clear();self.hold=0.;self.lap+=1;self.crossing_progress=None

    def path_y(self,x):
        i=max(0,min(len(self.path)-2,int(np.searchsorted(self.path[:,0],x)-1)))
        x0,y0=self.path[i];x1,y1=self.path[i+1];t=max(0.,min(1.,(x-x0)/(x1-x0)))
        i0=max(0,i-1);i1=min(len(self.path)-1,i+2)
        m0=(y1-self.path[i0,1])/(x1-self.path[i0,0])
        m1=(self.path[i1,1]-y0)/(self.path[i1,0]-x0)
        return float((2*t**3-3*t*t+1)*y0+(t**3-2*t*t+t)*m0*(x1-x0)+(-2*t**3+3*t*t)*y1+(t**3-t*t)*m1*(x1-x0))

    def update_walking(self):
        dt=self.dt/1000
        key=self.keyboard.getKey()
        if key!=self.previous_key:
            if key in [ord('P'),ord(' ')]:self.paused=not self.paused
            if key==ord('R'):self.reset_route()
            if key==ord('V'):self.follow_view=not self.follow_view
        self.previous_key=key
        if self.x>=29.5 and 29.5 not in self.stations:
            self.stations.add(29.5);self.hold=3.4
        if not self.paused:self.hold=max(0.,self.hold-dt)
        cruise=self.speed
        for lo,hi,limit in [(8,13.5,.55),(16,20,.60),(23,27,.50),(28,34.5,.45)]:
            if lo<=self.x<hi:cruise=min(cruise,limit)
        target=0. if self.paused or self.hold>0 else cruise
        acceleration=.65 if target>self.actual_speed else 1.05
        self.actual_speed+=max(-acceleration*dt,min(acceleration*dt,target-self.actual_speed))
        slope=(self.path_y(self.x+.15)-self.path_y(self.x-.15))/.30
        ds=self.actual_speed*dt
        self.x+=ds/math.sqrt(1+slope*slope);self.distance+=ds
        if self.x>self.scene['route_end_m']:self.reset_route()
        cycle=self.distance/STRIDE_M;blend=min(1.,self.actual_speed/.18)
        self.y=self.path_y(self.x)+.009*math.sin(2*math.pi*cycle)*blend
        wanted=math.atan2(self.path_y(self.x+.25)-self.path_y(self.x-.25),.50)
        error=math.atan2(math.sin(wanted-self.heading),math.cos(wanted-self.heading))
        self.heading+=error*min(1.,dt*4)
        height=1.215+.006*math.cos(4*math.pi*cycle)*blend
        for name,value in walking_pose(self.distance,height,self.actual_speed).items():
            self.joints[name].setSFFloat(value)
        self.position.setSFVec3f([self.x,self.y,height])
        self.root_rotation.setSFRotation([0.,0.,1.,self.heading])
        self.cane.setSFRotation([0.,0.,1.,.34*math.sin(2*math.pi*cycle+math.pi/3)*blend])
        if self.follow_view:
            desired=np.array([self.x-4.,self.y-6.,4.])
            if np.linalg.norm(desired-self.view_position)>8:self.view_position=desired
            self.view_position+=(desired-self.view_position)*min(1.,dt*2.5)
            self.viewpoint.getField('position').setSFVec3f(self.view_position.tolist())
        # The oncoming pedestrian traverses the sidewalk when the observer approaches.
        if self.x>=28 and self.crossing_progress is None:self.crossing_progress=0.
        if self.crossing_progress is not None and not self.paused:
            self.crossing_progress=min(4.0,self.crossing_progress+dt*.85)
        progress=self.crossing_progress or 0.
        target_y=1.30-progress
        ground=-.16*max(0.,min(1.,(-1.4-target_y)/.3))
        self.target_person.getField('translation').setSFVec3f([32.,target_y,1.215+ground])
        self.target_person.getField('rotation').setSFRotation([0.,0.,1.,-math.pi/2])
        person_speed=.85 if self.crossing_progress is not None and progress<4 else 0.
        for name,value in walking_pose(progress,1.215,person_speed).items():
            self.target_person_joints[name].setSFFloat(value)
        self.scenario=next(s for s in reversed(self.scene['scenarios']) if self.x>=s['start_m'])
        return height-1.27

    def run(self):
        while rclpy.ok():
            rclpy.spin_once(self.node,timeout_sec=0.)
            bob=self.update_walking()
            if self.step(self.dt)==-1: break
            seconds=self.getTime(); ns=round(seconds*1e9)
            stamp=Time(sec=ns//10**9,nanosec=ns%10**9)
            self.clock.publish(Clock(clock=stamp))
            # Pose is set before step; camera pixels, time and TF describe the same simulation tick.
            c=math.cos(self.heading);s=math.sin(self.heading)
            yaw_rotation=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])
            transforms=[tf_message('world','assistive/base_link',[self.x,self.y,0],yaw_rotation,stamp)]
            for side,c,_,_,_ in self.cameras:
                transforms.append(tf_message('assistive/base_link',f'assistive/{side}_camera_optical_frame',[.235,.06 if side=='left' else -.06,1.67+bob],self.camera_rotation,stamp))
            self.tf.sendTransform(transforms)
            if ns % (PERIOD_MS*1_000_000) != 0: continue
            self.last_publish=seconds
            for side,c,pub,info_pub,info in self.cameras:
                data=c.getImage()
                if not data: continue
                msg=Image(); msg.header.stamp=stamp; msg.header.frame_id=info.header.frame_id
                msg.width=c.getWidth(); msg.height=c.getHeight(); msg.encoding='bgra8'; msg.step=msg.width*4; msg.data=array("B",data)
                pub.publish(msg); info.header.stamp=stamp; info_pub.publish(info)
            self.frame+=1
            objects=[]
            for obj in self.cameras[0][1].getRecognitionObjects():
                p=list(obj.getPosition()); center=list(obj.getPositionOnImage()); size=list(obj.getSizeOnImage())
                label=obj.getModel(); label=label.decode() if isinstance(label,bytes) else label
                objects.append({'id':obj.getId(),'class':label,'range_m':round(math.sqrt(sum(v*v for v in p)),3),'camera_position_m':p,'center_px':center,'size_px':size})
            self.ground_truth.publish(String(data=json.dumps({'source':'webots_recognition_ground_truth','simulation_time':seconds,'objects':objects})))
            if seconds-self.last_status>=.25:
                state={'source':'simulation_only_no_yolo','simulation_time':round(seconds,3),'x_m':round(self.x,3),'y_m':round(self.y,3),'heading_rad':self.heading,'speed_mps':round(self.actual_speed,3),'requested_speed_mps':self.speed,'scenario_id':self.scenario['id'],'scenario_name_ko':self.scenario['name_ko'],'challenge_ko':self.scenario['challenge_ko'],'paused':self.paused,'holding':self.hold>0,'lap':self.lap,'frames':self.frame,'visible_objects':len(objects),'baseline_m':BASELINE,'objects':objects}
                self.status.publish(String(data=json.dumps(state))); self.last_status=seconds
                (ROOT/'logs/status.json').write_text(json.dumps(state,indent=2))
            if seconds-self.last_save>=2:
                for side,c,_,_,_ in self.cameras: c.saveImage(str(ROOT/f'logs/{side}_latest.png'),100)
                self.last_save=seconds
        self.node.destroy_node(); rclpy.shutdown()


if __name__=='__main__':
    AssistiveWalker().run()
