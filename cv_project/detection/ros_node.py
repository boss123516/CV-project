"""One ROS detection boundary with explicit simulator and YOLO26 backends."""
import json
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_project.config import pipeline_config
from cv_project.contracts import detection_packet
from cv_project.detection.simulator import convert_simulator_packet


class DetectionNode(Node):
    def __init__(self):
        super().__init__('cv_project_detector')
        config=pipeline_config()['detector']
        self.backend=config['backend'];self.latest=None;self.detector=None
        self.publisher=self.create_publisher(String,'/assistive/detections',8)
        if self.backend=='simulator':
            self.create_subscription(String,'/assistive/ground_truth/objects',self.on_simulator,8)
            self.get_logger().info('Explicit simulator-box backend. Distances/positions are discarded.')
        else:
            from cv_project.detection.yolo26 import YOLO26Detector
            self.detector=YOLO26Detector(**{key:value for key,value in config.items() if key!='backend'})
            self.create_subscription(Image,'/assistive/stereo/left/image_rect',self.on_image,2)
            self.get_logger().info('YOLO26 backend: rectified-left image -> class/bbox; no simulator subscription.')

    def on_simulator(self,message):
        packet=convert_simulator_packet(json.loads(message.data))
        self.publisher.publish(String(data=json.dumps(packet)))

    def on_image(self,message):
        self.latest=message

    def process(self):
        if self.latest is None:return
        from cv_project.pipeline.stereo_node import image_key,unpack_image
        message=self.latest;self.latest=None
        detections=self.detector.detect(unpack_image(message))
        packet=detection_packet(image_key(message),detections,'yolo26')
        self.publisher.publish(String(data=json.dumps(packet)))


def main():
    rclpy.init();node=DetectionNode()
    try:
        while rclpy.ok():
            for _ in range(4):rclpy.spin_once(node,timeout_sec=.005)
            node.process()
    finally:node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
