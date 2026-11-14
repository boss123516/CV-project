#!/usr/bin/env python3
"""Audit the running image-based pipeline without supplying it any true distances."""
from pathlib import Path
from collections import Counter
import argparse
import json
import math
import time
import rclpy
from std_msgs.msg import Bool,String

parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=150)
parser.add_argument('--resume',action='store_true');args=parser.parse_args()
rclpy.init();node=rclpy.create_node('assistive_runtime_validation')
scenarios=set();classes=Counter();invalid=Counter();valid_count=0;packets=0;max_visible=0;box_packets=0;extrinsics=Counter()
last_announce=None;paused=True;processing=[];start=time.monotonic();last_print=start

def perception(msg):
    global packets,valid_count
    data=json.loads(msg.data);assert data['source']=='stereo_sgbm'
    assert data['detector_source'] in ['webots_box_adapter_NOT_yolo','yolo26']
    packets+=1;processing.append(data['processing_ms']);extrinsics[data['extrinsic_source']]+=1
    for obj in data['objects']:
        assert 'camera_position_m' not in obj
        if not obj['valid']:
            assert 'distance_m' not in obj
            invalid[obj['reason']]+=1;continue
        valid_count+=1;classes[obj['class']]+=1
        x,y,z=obj['person_xyz_m']
        assert abs(obj['distance_m']-math.hypot(x,y))<.002
        assert abs(obj['bearing_deg']-math.degrees(math.atan2(-y,x)))<.02
        assert obj['inlier_pixels']>=24
        assert .6<=obj['depth_m']<=10

def detection(msg):
    global box_packets
    data=json.loads(msg.data);box_packets+=1
    for obj in data['detections']:
        assert set(obj)=={'id','class','bbox_xyxy','confidence'},'Simulator geometry leaked into detection input'

def status(msg):
    global max_visible,paused
    data=json.loads(msg.data);paused=data['paused'];scenarios.add(data['scenario_id']);max_visible=max(max_visible,data['visible_objects'])

def announcement(msg):
    global last_announce
    last_announce=msg.data

node.create_subscription(String,'/assistive/perception/objects',perception,10)
node.create_subscription(String,'/assistive/detections',detection,10)
node.create_subscription(String,'/assistive/status',status,10)
node.create_subscription(String,'/assistive/announcements',announcement,10)
pause=node.create_publisher(Bool,'/assistive/pause',10)
try:
    last_resume=0.
    while time.monotonic()-start<args.seconds:
        rclpy.spin_once(node,timeout_sec=.03)
        if args.resume and paused and pause.get_subscription_count()>0 and time.monotonic()-last_resume>1:
            pause.publish(Bool(data=False));last_resume=time.monotonic()
        if time.monotonic()-last_print>15:
            print(f'{packets} measured pairs | {valid_count} valid object measurements | scenarios {sorted(scenarios)}',flush=True)
            last_print=time.monotonic()
        if len(scenarios)>=6 and packets>=60:break
    assert packets>=30 and valid_count>=10 and box_packets>0,'Insufficient live measurements'
    assert max_visible<=5,f'Unexpected target density {max_visible}'
    report={'passed':True,'stereo_packets':packets,'valid_object_measurements':valid_count,
            'classes_measured':dict(classes),'rejections':dict(invalid),'scenarios_observed':sorted(scenarios),
            'max_visible_targets':max_visible,'extrinsic_sources':dict(extrinsics),
            'mean_sgbm_ms':round(sum(processing)/len(processing),2),
            'no_ground_truth_coordinates_in_detection_input':True,'last_spoken_text':last_announce}
    (Path(__file__).resolve().parents[1]/'logs/runtime_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
finally:node.destroy_node();rclpy.shutdown()
