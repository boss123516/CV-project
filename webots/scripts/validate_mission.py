#!/usr/bin/env python3
"""Validate destination/traffic choreography using simulator telemetry only."""
import argparse
import json
import time
from pathlib import Path
import rclpy
from std_msgs.msg import String
from cv_project.config import runtime_dir

parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=100)
parser.add_argument('--scenario',required=True);args=parser.parse_args()
rclpy.init();node=rclpy.create_node('destination_mission_validation')
phases=set();events=[];positions=[];signals=set();vehicle_speed=0.;arrived=False;profile=None;frames=0

def status(message):
    global arrived,profile,frames,vehicle_speed
    packet=json.loads(message.data)
    if packet.get('scenario_profile')!=args.scenario:return
    profile=packet['scenario_profile'];mission=packet.get('mission',{})
    phases.add(mission.get('phase'));arrived=arrived or mission.get('arrived',False)
    positions.append([packet['x_m'],packet['y_m']]);frames+=1
    if traffic:=mission.get('traffic'):
        signals.add(traffic['pedestrian_signal'])
        vehicle_speed=max(vehicle_speed,max(v['speed_mps'] for v in traffic['vehicles']))
        if mission['action_id']=='cross_road' and abs(packet['y_m'])<3.6:
            assert traffic['pedestrian_signal']=='green','Entered road on red'
            assert traffic['crosswalk_clear'],'Entered occupied crossing'

def event(message):
    packet=json.loads(message.data)
    assert packet['source']=='scenario_script'
    events.append(packet)

node.create_subscription(String,'/assistive/status',status,10)
node.create_subscription(String,'/assistive/mission/events',event,10)
start=time.monotonic()
try:
    while time.monotonic()-start<args.seconds:
        rclpy.spin_once(node,timeout_sec=.05)
        if arrived and frames>=10:break
    assert arrived,f'Destination not reached: {profile}, {phases}'
    if args.scenario=='signalized_crossing':
        assert {'red','green'}<=signals
        assert vehicle_speed>3
    else:
        assert {'contact','backtrack','scan','detour','arrive'}<=phases
    report={'passed':True,'scenario':profile,'phases':sorted(phases),'events':events,
            'signal_states':sorted(signals),'max_vehicle_speed_mps':round(vehicle_speed,2),
            'destination_reached':arrived,'status_samples':frames,'navigation_source':'scenario_script'}
    (runtime_dir()/f'validation_{args.scenario}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
finally:node.destroy_node();rclpy.shutdown()
