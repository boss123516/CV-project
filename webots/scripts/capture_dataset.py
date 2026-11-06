#!/usr/bin/env python3
"""Save synchronized stereo frames plus simulator-generated YOLO labels."""
import argparse
from collections import OrderedDict
from pathlib import Path
import json
import time
import cv2
import numpy as np
import rclpy
from sensor_msgs.msg import Image
from std_msgs.msg import String

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[2]/'datasets'/'sidewalk')
parser.add_argument('--count',type=int,default=60)
parser.add_argument('--interval',type=float,default=.5,help='Seconds of simulation time between samples')
args=parser.parse_args()
if args.count<=0 or args.interval<=0: parser.error('count and interval must be positive')
# Each invocation has its own run directory so earlier samples cannot be overwritten.
out=args.output/time.strftime('%Y%m%d_%H%M%S')
for sub in ['images','right_images','labels','metadata']: (out/sub).mkdir(parents=True,exist_ok=True)
catalog=json.loads((Path(__file__).resolve().parents[1]/'config/object_classes.json').read_text())
classes={name:definition['id'] for name,definition in catalog.items()}
(out/'classes.txt').write_text('\n'.join(classes)+'\n')
rclpy.init(); node=rclpy.create_node('assistive_dataset_capture')
packets=OrderedDict(); saved=0; last=-1e9; received=time.monotonic()

def key_of(msg): return msg.header.stamp.sec*10**9+msg.header.stamp.nanosec

def put(key,kind,value):
    global received
    received=time.monotonic()
    packets.setdefault(key,{})[kind]=value
    while len(packets)>80: packets.popitem(last=False)

def truth(msg):
    data=json.loads(msg.data)
    put(round(data['simulation_time']*1e9),'truth',data)

for side in ['left','right']:
    node.create_subscription(Image,f'/assistive/stereo/{side}/image_raw',lambda m,s=side:put(key_of(m),s,m),4)
node.create_subscription(String,'/assistive/ground_truth/objects',truth,4)
try:
    while saved<args.count:
        rclpy.spin_once(node,timeout_sec=.1)
        if time.monotonic()-received>20: raise RuntimeError('No simulator data received in 20 s')
        for key,packet in list(packets.items()):
            if not all(k in packet for k in ['left','right','truth']): continue
            del packets[key]
            seconds=key/1e9
            if seconds-last<args.interval: continue
            stem=f'{saved:06d}'
            for side,folder in [('left','images'),('right','right_images')]:
                m=packet[side]; channels=4 if m.encoding=='bgra8' else 3
                raw=np.frombuffer(m.data,np.uint8).reshape(m.height,m.step)[:,:m.width*channels].reshape(m.height,m.width,channels)
                if not cv2.imwrite(str(out/folder/f'{stem}.png'),raw[:,:,:3]): raise RuntimeError('Image write failed')
            width=packet['left'].width; height=packet['left'].height; lines=[]
            for obj in packet['truth']['objects']:
                if obj['class'] not in classes: continue
                x,y=obj['center_px']; w,h=obj['size_px']
                x1=max(0.,x-w/2); x2=min(width,x+w/2); y1=max(0.,y-h/2); y2=min(height,y+h/2)
                if x2<=x1 or y2<=y1: continue
                lines.append(f"{classes[obj['class']]} {(x1+x2)/2/width:.6f} {(y1+y2)/2/height:.6f} {(x2-x1)/width:.6f} {(y2-y1)/height:.6f}")
            (out/'labels'/f'{stem}.txt').write_text('\n'.join(lines)+'\n' if lines else '')
            (out/'metadata'/f'{stem}.json').write_text(json.dumps(packet['truth'],indent=2))
            saved+=1; last=seconds
            print(f'{saved}/{args.count} synchronized pair | t={seconds:.3f} | {len(lines)} label(s)',flush=True)
            if saved>=args.count: break
    print(f'Saved to {out}\nLabels are Webots ground truth. Split separate runs into train/val before YOLO training.',flush=True)
finally:
    node.destroy_node(); rclpy.shutdown()
