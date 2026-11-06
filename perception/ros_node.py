"""ROS adapter for the stereo core. Object coordinates never enter this node."""
from collections import OrderedDict
from array import array
from pathlib import Path
import json
import time
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image,CameraInfo
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage
from perception.stereo import CameraModel,StereoEstimator,optical_to_person_transform

ROOT=Path(__file__).resolve().parents[1]
cv2.setNumThreads(2)


def image_key(message):
    return message.header.stamp.sec*10**9+message.header.stamp.nanosec


def unpack_image(message):
    channels={'bgra8':4,'bgr8':3,'rgb8':3,'mono8':1}.get(message.encoding)
    if channels is None: raise ValueError('Unsupported image encoding: '+message.encoding)
    raw=np.frombuffer(message.data,np.uint8).reshape(message.height,message.step)
    raw=raw[:,:message.width*channels].reshape(message.height,message.width,channels)
    if channels==1:return raw[:,:,0].copy()
    return cv2.cvtColor(raw,cv2.COLOR_RGB2BGR) if message.encoding=='rgb8' else raw[:,:,:3].copy()


class StereoPerception(Node):
    def __init__(self):
        super().__init__('assistive_stereo_perception')
        config=json.loads((ROOT/'webots/config/stereo_rig.json').read_text())
        self.matcher_options=config['matcher'];rig=config['left_camera_to_person']
        self.extrinsic=optical_to_person_transform(rig['translation_m'],rig['downward_pitch_rad'])
        self.images={s:OrderedDict() for s in ['left','right']}
        self.extrinsics=OrderedDict()
        self.calibration={};self.frames=OrderedDict();self.detections=OrderedDict();self.estimator=None
        self.objects_pub=self.create_publisher(String,'/assistive/perception/objects',4)
        self.left_rect_pub=self.create_publisher(Image,'/assistive/stereo/left/image_rect',2)
        self.debug_pub=self.create_publisher(Image,'/assistive/stereo/disparity_visualization',2)
        for side in self.images:
            self.create_subscription(Image,f'/assistive/stereo/{side}/image_raw',lambda m,s=side:self.on_image(s,m),4)
            self.create_subscription(CameraInfo,f'/assistive/stereo/{side}/camera_info',lambda m,s=side:self.on_info(s,m),4)
        self.create_subscription(String,'/assistive/detections',self.on_detections,8)
        self.create_subscription(TFMessage,'/tf',self.on_tf,16)
        self.last_report=time.monotonic();self.processed=0
        self.get_logger().info('Stereo image measurements active; detections supply class/bbox only. No ground-truth distance fallback.')

    @staticmethod
    def trim(cache,limit=16):
        while len(cache)>limit: cache.popitem(last=False)

    def on_image(self,side,message):
        self.images[side][image_key(message)]=message;self.trim(self.images[side])

    def on_info(self,side,message):
        if side not in self.calibration:self.calibration[side]=CameraModel.from_ros(message)

    def on_tf(self,message):
        for transform in message.transforms:
            if transform.header.frame_id!='assistive/base_link' or transform.child_frame_id!='assistive/left_camera_optical_frame':continue
            q=transform.transform.rotation;x,y,z,w=q.x,q.y,q.z,q.w
            rotation=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                               [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                               [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
            translation=transform.transform.translation
            matrix=np.eye(4);matrix[:3,:3]=rotation;matrix[:3,3]=[translation.x,translation.y,translation.z]
            self.extrinsics[image_key(transform)]=matrix;self.trim(self.extrinsics,64)

    def on_detections(self,message):
        packet=json.loads(message.data)
        self.detections[int(packet['stamp_ns'])]=packet;self.trim(self.detections,32)

    @staticmethod
    def image_message(image,header):
        message=Image();message.header=header;message.height,message.width=image.shape[:2]
        message.encoding='bgr8';message.step=message.width*3;message.data=array("B",np.ascontiguousarray(image).tobytes())
        return message

    def process(self):
        if self.estimator is None:
            if len(self.calibration)!=2:return
            self.estimator=StereoEstimator(self.calibration['left'],self.calibration['right'],self.extrinsic,**self.matcher_options)
            self.get_logger().info(f'Calibrated: fx={self.estimator.fx:.3f}px, baseline={self.estimator.baseline:.3f}m')
        common=self.images['left'].keys()&self.images['right'].keys()
        if common:
            # Latest complete pair bounds latency if the CPU cannot process every frame.
            key=max(common);left=self.images['left'][key];right=self.images['right'][key]
            frame=self.estimator.compute(unpack_image(left),unpack_image(right))
            self.frames[key]=(frame,left.header);self.trim(self.frames)
            self.left_rect_pub.publish(self.image_message(frame.rectified_left,left.header))
            debug=cv2.applyColorMap(np.uint8(np.clip(frame.disparity_px/self.estimator.num_disparities*255,0,255)),cv2.COLORMAP_TURBO)
            debug[~frame.valid_mask]=0
            self.debug_pub.publish(self.image_message(debug,left.header))
            for side in self.images:
                for old in list(self.images[side]):
                    if old<=key:del self.images[side][old]
        ready=sorted(self.frames.keys()&self.detections.keys())
        for key in ready:
            frame,header=self.frames.pop(key);detections=self.detections.pop(key)
            self.estimator.person_from_optical=self.extrinsics.get(key,self.extrinsic)
            objects=[self.estimator.localize(frame,d) for d in detections['detections']]
            packet={'stamp_ns':key,'simulation_time':key/1e9,'source':'stereo_sgbm',
                    'detector_source':detections.get('source','external_detector'),
                    'frame_id':'assistive/base_link','baseline_m':self.estimator.baseline,
                    'processing_ms':round(frame.processing_ms,2),'objects':objects,
                    'extrinsic_source':'tf_at_capture' if key in self.extrinsics else 'rig_config',
                    'measurement_definition':'representative_visible_surface_in_person_frame'}
            self.objects_pub.publish(String(data=json.dumps(packet,ensure_ascii=False)))
            self.processed+=1
            if time.monotonic()-self.last_report>5:
                valid=sum(o['valid'] for o in objects)
                self.get_logger().info(f'{self.processed} measured pairs | {valid}/{len(objects)} valid objects | SGBM {frame.processing_ms:.1f} ms')
                (ROOT/'webots/logs/perception.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2))
                self.last_report=time.monotonic()


def main():
    rclpy.init();node=StereoPerception()
    try:
        while rclpy.ok():
            for _ in range(8):rclpy.spin_once(node,timeout_sec=.001)
            node.process()
    finally:
        node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
