#!/usr/bin/env python3
"""Publish and speak Korean reference guidance from stereo image measurements."""
from pathlib import Path
import json
import subprocess
import sys
import time
import rclpy
from std_msgs.msg import Bool, String
from guidance import describe_estimate

ROOT=Path(__file__).resolve().parents[1]
rclpy.init(); node=rclpy.create_node('assistive_voice_guidance')
text_pub=node.create_publisher(String,'/assistive/announcements',10)
guide_pub=node.create_publisher(String,'/assistive/guidance',10)
latest=[]; enabled=True; speaking=None; last_time=-100.; last_key=None

def receive(msg):
    global latest
    latest=[g for o in json.loads(msg.data)['objects'] if (g:=describe_estimate(o)) is not None]
    guide_pub.publish(String(data=json.dumps({'source':'stereo_sgbm','objects':latest},ensure_ascii=False)))

def enable(msg):
    global enabled
    enabled=msg.data

node.create_subscription(String,'/assistive/perception/objects',receive,2)
node.create_subscription(Bool,'/assistive/voice_enabled',enable,10)
node.get_logger().info('Offline Korean voice enabled. Distance/direction source: STEREO IMAGES. Class/bbox currently from simulator adapter. /assistive/voice_enabled controls audio.')
try:
    while rclpy.ok():
        rclpy.spin_once(node,timeout_sec=.05)
        now=time.monotonic()
        candidates=[g for g in latest if .5<=g['distance_m']<=6.]
        if not candidates: continue
        g=min(candidates,key=lambda v:v['distance_m'])
        key=(g['object_id'],g['clock_hour'],g['spoken_distance_m'])
        if not enabled or now-last_time<5 or key==last_key: continue
        if speaking is not None and speaking.poll() is None: continue
        text_pub.publish(String(data=g['text']))
        node.get_logger().info(g['text'])
        with (ROOT/'logs/announcements.jsonl').open('a') as f: f.write(json.dumps(g,ensure_ascii=False)+'\n')
        speaking=subprocess.Popen([sys.executable,str(ROOT/'scripts/korean_tts.py'),g['text'],str(ROOT/'logs/last_announcement.wav'),'--play'])
        last_time=now; last_key=key
finally:
    if speaking is not None and speaking.poll() is None: speaking.terminate()
    node.destroy_node(); rclpy.shutdown()
