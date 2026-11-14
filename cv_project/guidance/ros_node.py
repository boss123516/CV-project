"""Measured objects -> Korean guidance. Speech engine runs out of process."""
import json
import os
import signal
import subprocess
import sys
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool,String
from cv_project.config import pipeline_config,runtime_dir
from cv_project.guidance.formatter import describe_estimate


class GuidanceNode(Node):
    def __init__(self):
        super().__init__('assistive_voice_guidance')
        self.settings=pipeline_config()['guidance'];self.latest=[];self.enabled=True
        self.alert_queue=[];self.seen_alerts=set();self.traffic_blocking=False
        self.speaking=None;self.last_time=-100.;self.last_key=None;self.received_at=-100.
        self.text_pub=self.create_publisher(String,'/assistive/announcements',10)
        self.guide_pub=self.create_publisher(String,'/assistive/guidance',10)
        self.create_subscription(String,'/assistive/perception/objects',self.receive,2)
        self.create_subscription(Bool,'/assistive/voice_enabled',self.enable,10)
        self.create_subscription(String,'/assistive/mission/events',self.mission_event,10)
        self.alert_pub=self.create_publisher(String,'/assistive/mission/alerts',10)
        self.get_logger().info('Guidance uses measured stereo distances; detector source is carried in every packet.')

    def receive(self,message):
        packet=json.loads(message.data)
        self.latest=[value for obj in packet['objects'] if (value:=describe_estimate(obj)) is not None]
        self.received_at=time.monotonic()
        self.guide_pub.publish(String(data=json.dumps({'source':packet['source'],
            'detector_source':packet.get('detector_source'),'objects':self.latest},ensure_ascii=False)))

    def mission_event(self,message):
        event=json.loads(message.data)
        if event.get('source')!='scenario_script':return
        texts={'pedestrian_red_wait':'빨간불입니다. 기다리세요.',
               'pedestrian_green_clear':'초록불로 바뀌었습니다. 차량이 멈춘 것을 확인하고 건너세요.'}
        kind=event.get('type')
        if kind not in texts:return
        key=(event.get('lap'),kind)
        if key in self.seen_alerts:return
        self.seen_alerts.add(key)
        self.traffic_blocking=kind=='pedestrian_red_wait'
        packet=dict(event,text=texts[kind])
        if self.enabled:self.alert_queue.append(packet)
        self.alert_pub.publish(String(data=json.dumps(packet,ensure_ascii=False)))

    def enable(self,message):
        self.enabled=message.data
        if not self.enabled:self.alert_queue.clear()

    def speak(self,text):
        self.text_pub.publish(String(data=text));self.get_logger().info(text)
        self.speaking=subprocess.Popen([sys.executable,'-m','cv_project.guidance.korean_tts',
            text,str(runtime_dir()/'last_announcement.wav'),'--play'],start_new_session=True)

    def process(self):
        now=time.monotonic()
        if not self.enabled:return
        if self.alert_queue:
            packet=self.alert_queue.pop(0)
            if self.speaking is not None and self.speaking.poll() is None:
                try:os.killpg(self.speaking.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:self.speaking.wait(timeout=.25)
                except subprocess.TimeoutExpired:pass
            self.speak(packet['text'])
            with (runtime_dir()/'announcements.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(packet,ensure_ascii=False)+'\n')
            self.last_time=now
            return
        if self.traffic_blocking or now-self.received_at>2:return
        candidates=[obj for obj in self.latest if .5<=obj['distance_m']<=self.settings['max_distance_m']]
        if not candidates:return
        obj=min(candidates,key=lambda value:value['distance_m'])
        key=(obj.get('object_id') if obj.get('object_id') is not None else obj['class'],
             obj['clock_hour'],obj['spoken_distance_m'])
        if now-self.last_time<self.settings['minimum_interval_s'] or key==self.last_key:return
        if self.speaking is not None and self.speaking.poll() is None:return
        self.speak(obj['text'])
        with (runtime_dir()/'announcements.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(obj,ensure_ascii=False)+'\n')
        self.last_time=now;self.last_key=key


def main():
    rclpy.init();node=GuidanceNode()
    try:
        while rclpy.ok():rclpy.spin_once(node,timeout_sec=.05);node.process()
    finally:
        if node.speaking is not None and node.speaking.poll() is None:node.speaking.terminate()
        node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
