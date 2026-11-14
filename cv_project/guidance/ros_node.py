"""Measured objects -> Korean guidance. Speech engine runs out of process."""
import json
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
        self.speaking=None;self.last_time=-100.;self.last_key=None;self.received_at=-100.
        self.text_pub=self.create_publisher(String,'/assistive/announcements',10)
        self.guide_pub=self.create_publisher(String,'/assistive/guidance',10)
        self.create_subscription(String,'/assistive/perception/objects',self.receive,2)
        self.create_subscription(Bool,'/assistive/voice_enabled',self.enable,10)
        self.get_logger().info('Guidance uses measured stereo distances; detector source is carried in every packet.')

    def receive(self,message):
        packet=json.loads(message.data)
        self.latest=[value for obj in packet['objects'] if (value:=describe_estimate(obj)) is not None]
        self.received_at=time.monotonic()
        self.guide_pub.publish(String(data=json.dumps({'source':packet['source'],
            'detector_source':packet.get('detector_source'),'objects':self.latest},ensure_ascii=False)))

    def enable(self,message):self.enabled=message.data

    def process(self):
        now=time.monotonic()
        if not self.enabled or now-self.received_at>2:return
        candidates=[obj for obj in self.latest if .5<=obj['distance_m']<=self.settings['max_distance_m']]
        if not candidates:return
        obj=min(candidates,key=lambda value:value['distance_m'])
        key=(obj.get('object_id') if obj.get('object_id') is not None else obj['class'],
             obj['clock_hour'],obj['spoken_distance_m'])
        if now-self.last_time<self.settings['minimum_interval_s'] or key==self.last_key:return
        if self.speaking is not None and self.speaking.poll() is None:return
        self.text_pub.publish(String(data=obj['text']));self.get_logger().info(obj['text'])
        with (runtime_dir()/'announcements.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(obj,ensure_ascii=False)+'\n')
        self.speaking=subprocess.Popen([sys.executable,'-m','cv_project.guidance.korean_tts',
            obj['text'],str(runtime_dir()/'last_announcement.wav'),'--play'])
        self.last_time=now;self.last_key=key


def main():
    rclpy.init();node=GuidanceNode()
    try:
        while rclpy.ok():rclpy.spin_once(node,timeout_sec=.05);node.process()
    finally:
        if node.speaking is not None and node.speaking.poll() is None:node.speaking.terminate()
        node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
