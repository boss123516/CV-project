#!/usr/bin/env python3
"""Validate actual stereo timing, calibration and reference-data sparsity."""
from pathlib import Path
import json
import math
import time
import numpy as np
import rclpy
from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import String
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from perception.stereo import clock_direction

# Known left/right bearings catch a mirrored clock-direction implementation.
for bearing,hour in [(0,12),(-30,11),(30,1),(-60,10),(60,2)]:
    forward=3.;left=-math.tan(math.radians(bearing))*forward
    actual_bearing,actual_hour=clock_direction(forward,left)
    assert actual_hour==hour,(bearing,actual_hour)

rclpy.init(); node=rclpy.create_node('assistive_stream_check')
frames={'left':{},'right':{}}; infos={}; counts=[]; statuses=[]
start=time.monotonic()
def receive(side,msg):
    assert (msg.width,msg.height,msg.encoding,msg.step)==(640,480,'bgra8',2560)
    assert len(msg.data)==640*480*4
    stamp=msg.header.stamp.sec*10**9+msg.header.stamp.nanosec
    frames[side][stamp]=np.frombuffer(msg.data,np.uint8).reshape(480,640,4)[:,:,:3].copy()

def status(msg):
    data=json.loads(msg.data); counts.append(data['visible_objects']); statuses.append(data)

for side in frames:
    node.create_subscription(Image,f'/assistive/stereo/{side}/image_raw',lambda msg,s=side:receive(s,msg),4)
    node.create_subscription(CameraInfo,f'/assistive/stereo/{side}/camera_info',lambda msg,s=side:infos.__setitem__(s,msg),4)
node.create_subscription(String,'/assistive/status',status,10)
try:
    while time.monotonic()-start<35:
        rclpy.spin_once(node,timeout_sec=.1)
        common=sorted(frames['left'].keys()&frames['right'].keys())
        if len(common)>=60 and len(infos)==2 and counts: break
    assert len(common)>=30,f'Too few synchronized pairs: {len(common)}'
    assert len(infos)==2,'Missing calibration'
    diffs=np.diff(common)/1e9
    assert np.allclose(diffs,.064,atol=1e-6),f'Unexpected frame intervals: {np.unique(diffs)}'
    assert all(k%64000000==0 for k in common),'Image timestamps not aligned to camera refresh'
    fx=infos['left'].k[0]; baseline=-infos['right'].p[3]/fx
    assert abs(baseline-.12)<1e-9
    assert max(counts)<=5,f'Too many reference objects: {max(counts)}'
    sample=common[-1]; left=frames['left'][sample]; right=frames['right'][sample]
    assert np.std(left)>5,'Blank camera frame'
    assert np.mean(np.abs(left.astype(float)-right.astype(float)))>.05,'Identical stereo images'
    result={'passed':True,'synchronized_pairs':len(common),'simulation_fps':float(1/np.median(diffs)),'baseline_m':baseline,'image_shape':list(left.shape),'max_visible_targets':max(counts),'clock_direction_cases':5,'measured_wall_fps':len(common)/(time.monotonic()-start),'classes_observed':sorted({o['class'] for st in statuses for o in st['objects']})}
    target=Path(__file__).resolve().parents[1]/'logs/validation.json';target.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:
    node.destroy_node();rclpy.shutdown()
