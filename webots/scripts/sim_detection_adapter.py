#!/usr/bin/env python3
"""Temporary detector adapter: publish ONLY names/boxes, never true positions."""
import json
import rclpy
from std_msgs.msg import String
rclpy.init();node=rclpy.create_node('simulator_box_adapter')
publisher=node.create_publisher(String,'/assistive/detections',8)

def receive(message):
    data=json.loads(message.data);detections=[]
    for obj in data['objects']:
        x,y=obj['center_px'];w,h=obj['size_px']
        detections.append({'id':obj['id'],'class':obj['class'],
                           'bbox_xyxy':[x-w/2,y-h/2,x+w/2,y+h/2]})
    publisher.publish(String(data=json.dumps({'stamp_ns':round(data['simulation_time']*1e9),
        'source':'webots_box_adapter_NOT_yolo','coordinate_space':'rectified_left',
        'detections':detections})))

node.create_subscription(String,'/assistive/ground_truth/objects',receive,8)
node.get_logger().info('Temporary class/bbox adapter. Object position and distance fields are intentionally discarded.')
try:rclpy.spin(node)
finally:node.destroy_node();rclpy.shutdown()
