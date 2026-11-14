#!/usr/bin/env python3
"""Display the actual ROS image topics with clearly identified simulator reference data."""
import json
import time
import cv2
import os
os.environ["QT_QPA_FONTDIR"]="/usr/share/fonts/truetype/dejavu"
import numpy as np
import rclpy
from PIL import Image as PILImage, ImageDraw, ImageFont
from cv_project.guidance.formatter import describe_estimate
from mission_panel import render_panel,PHASES
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String

rclpy.init()
node=rclpy.create_node('assistive_stereo_viewer')
announcement='음성 안내 준비 중'; guidance=[]; perception={}
korean_font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22)
small_korean_font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',16)
cv2.setNumThreads(1)
images={}; arrivals={}; status={}; counts={'left':0,'right':0}

def receive(side,msg):
    raw=np.frombuffer(msg.data,dtype=np.uint8).reshape(msg.height,msg.step)
    channels=4 if msg.encoding=='bgra8' else 3
    images[side]=raw[:,:msg.width*channels].reshape(msg.height,msg.width,channels)[:,:,:3].copy()
    arrivals[side]=time.monotonic(); counts[side]+=1

def on_status(msg):
    global status
    status=json.loads(msg.data)

def on_announcement(msg):
    global announcement
    announcement=msg.data

def on_guidance(msg):
    global guidance
    guidance=json.loads(msg.data)['objects']

def on_perception(msg):
    global perception,guidance
    perception=json.loads(msg.data)
    guidance=[value for obj in perception.get('objects',[]) if (value:=describe_estimate(obj)) is not None]

node.create_subscription(String,'/assistive/perception/objects',on_perception,4)
node.create_subscription(String,'/assistive/announcements',on_announcement,10)
node.create_subscription(String,'/assistive/guidance',on_guidance,10)
for side in ['left','right']:
    node.create_subscription(Image,f'/assistive/stereo/{side}/image_raw',lambda msg,s=side:receive(s,msg),2)
node.create_subscription(String,'/assistive/status',on_status,10)
pause_pub=node.create_publisher(Bool,'/assistive/pause',10)
name='Assistive Vision - Stereo ROS Monitor'
cv2.namedWindow(name,cv2.WINDOW_NORMAL); cv2.resizeWindow(name,1600,720); cv2.moveWindow(name,80,160)
font=cv2.FONT_HERSHEY_SIMPLEX
try:
    while rclpy.ok():
        frame_start=time.monotonic()
        for _ in range(10):rclpy.spin_once(node,timeout_sec=0.)
        canvas=np.full((720,1600,3),(25,21,18),np.uint8)
        cv2.putText(canvas,'ASSISTIVE VISION  /  DESTINATION MISSIONS',(24,34),font,.8,(235,238,242),2,cv2.LINE_AA)
        for i,side in enumerate(['left','right']):
            x=i*640
            if side in images:
                canvas[98:578,x:x+640]=images[side]
                if side=='left':
                    for obj in perception.get('objects',[]):
                        a,b,c,d=[int(v) for v in obj['bbox_xyxy']]
                        color=(100,220,110) if obj['valid'] else (70,160,240)
                        cv2.rectangle(canvas,(max(0,a),98+max(0,b)),(min(639,c),98+min(479,d)),color,1)
                        label=f"{obj['class']}  {obj['clock_hour']}h  {obj['distance_m']:.1f}m" if obj['valid'] else obj['class']+' | depth unavailable'
                        cv2.putText(canvas,label,(max(4,a),98+max(25,b-7)),font,.42,color,1,cv2.LINE_AA)
            cv2.line(canvas,(x+320,98),(x+320,578),(180,190,190),1)
            for px,hour in [(60,11),(320,12),(580,1)]:
                cv2.putText(canvas,f'{hour}h',(x+px-12,120),font,.48,(80,235,245),1,cv2.LINE_AA)
            stale=time.monotonic()-arrivals.get(side,0)>2
            label=f'{side.upper()} CAMERA  '+('WAITING FOR TOPIC' if stale else 'LIVE')
            cv2.putText(canvas,label,(x+16,88),font,.51,(90,210,245) if not stale else (90,90,235),1,cv2.LINE_AA)
        walk='PAUSED' if status.get('paused') else (status['mission']['phase'].upper() if status.get('mission') else ('OBSERVATION STOP' if status.get('holding') else 'WALKING'))
        location=f"({status.get('x_m',0):.1f}, {status.get('y_m',0):.1f}) m"
        text=f"{walk}   |   {location}   |   {status.get('speed_mps',0):.2f} m/s   |   lap {status.get('lap',0)+1}   |   P: pause / resume    Q: close monitor"
        cv2.putText(canvas,text,(18,604),font,.51,(230,230,230),1,cv2.LINE_AA)
        objects=perception.get('objects',[])
        reference='  /  '.join(f"{o['class']}: {o['distance_m']:.1f}m" if o['valid'] else f"{o['class']}: unavailable" for o in objects) or 'no target currently visible'
        cv2.putText(canvas,'STEREO DISTANCE: '+reference,(18,635),font,.51,(90,190,240),1,cv2.LINE_AA)
        cv2.putText(canvas,f"SGBM {perception.get('processing_ms',0):.0f} ms  |  detector: {perception.get('detector_source','waiting')}  |  distance / bearing: IMAGE MEASUREMENTS",(18,658),font,.43,(145,145,145),1,cv2.LINE_AA)
        pil=PILImage.fromarray(cv2.cvtColor(canvas,cv2.COLOR_BGR2RGB)); draw=ImageDraw.Draw(pil)
        current=min(guidance,key=lambda g:g['distance_m'])['text'] if guidance else ('영상으로 거리를 측정할 수 없습니다.' if objects else '전방에 표시할 대상이 없습니다.')
        traffic=status.get('mission',{}).get('traffic')
        if traffic:
            current='빨간불입니다. 기다리세요.' if traffic['pedestrian_signal']=='red' else '초록불 · 차량 정지 확인 후 횡단'
        draw.text((18,673),current,font=korean_font,fill=(240,220,120))
        draw.text((24,50),status.get('scenario_name_ko','상가 앞 보도')+' · '+status.get('challenge_ko',''),font=small_korean_font,fill=(165,192,200),anchor='lt')
        canvas=cv2.cvtColor(np.asarray(pil),cv2.COLOR_RGB2BGR)
        render_panel(canvas,status,korean_font,small_korean_font)
        cv2.imshow(name,canvas)
        key=cv2.waitKey(1)&255
        if key in [ord('q'),27]: break
        if key in [ord('p'),ord(' ')]: pause_pub.publish(Bool(data=not status.get('paused',False)))
        if cv2.getWindowProperty(name,cv2.WND_PROP_VISIBLE)<1: break
        time.sleep(max(0.,1/15-(time.monotonic()-frame_start)))
finally:
    cv2.destroyAllWindows(); node.destroy_node(); rclpy.shutdown()
