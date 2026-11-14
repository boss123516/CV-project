"""Mission map and status rendering. The map is scenario metadata, not SLAM."""
import math
import cv2
import numpy as np
from PIL import Image,ImageDraw

PHASES={'walk':'목적지로 이동','contact':'지팡이 접촉 연출','backtrack':'뒤로 물러남',
        'signal_wait':'빨간불 대기','scan':'좌우 공간 확인','detour':'대체 경로로 우회','wait':'보행자 대기','arrive':'목적지 도착'}


def render_panel(canvas,status,font,small_font):
    mission=status.get('mission')
    if not mission:return
    x0=1294;w=292
    canvas[:,1280:]=(34,32,28)
    image=Image.fromarray(cv2.cvtColor(canvas,cv2.COLOR_BGR2RGB));draw=ImageDraw.Draw(image)
    goal=mission['destination']
    draw.text((x0,26),'목적지',font=small_font,fill=(164,179,181),anchor='lt')
    draw.text((x0,54),goal['name_ko'],font=font,fill=(235,235,222),anchor='lt')
    draw.text((x0,100),PHASES.get(mission['phase'],mission['phase']),font=small_font,fill=(239,199,115),anchor='lt')
    draw.text((x0,135),f"남은 직선 거리 {mission['distance_to_goal_m']:.1f} m",font=small_font,fill=(212,220,218),anchor='lt')
    traffic=mission.get('traffic')
    if traffic:
        green=traffic['pedestrian_signal']=='green'
        draw.text((x0,192),'보행 신호: '+('초록불' if green else '빨간불'),font=small_font,fill=(120,220,143) if green else (250,105,90),anchor='lt')
    draw.text((x0,166),f"행동 {mission['action_index']+1} / {mission['action_count']}",font=small_font,fill=(164,179,181),anchor='lt')
    draw.text((x0,630),f"접촉 연출 {mission['contact_count']}회",font=small_font,fill=(196,204,201),anchor='lt')
    draw.text((x0,667),'동선: 시나리오 스크립트',font=small_font,fill=(147,161,159),anchor='lt')
    canvas[:]=cv2.cvtColor(np.asarray(image),cv2.COLOR_RGB2BGR)
    data=mission['map'];points=[data['start'],goal['position']]
    for leg in data['legs']:points+=leg['points']
    for obj in data['obstacles']:
        cx,cy=obj['center'];hx,hy=obj['half_extents']
        points.extend([[cx-hx,cy-hy],[cx+hx,cy+hy]])
    road=data.get('road')
    if road:
        x1,y1,x2,y2=road['bounds'];points.extend([[x1,y1],[x2,y2]])
    points=np.array(points,float)
    lo=points.min(axis=0)-1.3;hi=points.max(axis=0)+1.3
    span=np.maximum(hi-lo,1.)
    scale=min((w-22)/span[0],355/span[1])
    origin=np.array([x0+10+(w-22-span[0]*scale)/2,580-(355-span[1]*scale)/2])
    def pixel(point):
        point=(np.array(point)-lo)*scale
        return int(origin[0]+point[0]),int(origin[1]-point[1])
    cv2.rectangle(canvas,(x0,212),(x0+w,601),(48,49,44),-1)
    if road:
        x1,y1,x2,y2=road['bounds']
        cv2.rectangle(canvas,pixel([x1,y2]),pixel([x2,y1]),(61,62,57),-1)
    previous=data['start']
    for leg in data['legs']:
        color=(86,170,223) if leg['kind']=='detour' else (143,151,144)
        for point in leg['points']:
            cv2.line(canvas,pixel(previous),pixel(point),color,2,cv2.LINE_AA);previous=point
    for obstacle in data['obstacles']:
        center=np.array(obstacle['center']);half=np.array(obstacle['half_extents'])
        cv2.rectangle(canvas,pixel(center+[-half[0],half[1]]),pixel(center+[half[0],-half[1]]),(78,109,172),-1)
    if traffic:
        for car in traffic['vehicles']:
            center_car=pixel([car['x'],car['y']])
            cv2.rectangle(canvas,(center_car[0]-8,center_car[1]-3),(center_car[0]+8,center_car[1]+3),(112,163,196),-1)
    cv2.circle(canvas,pixel(goal['position']),7,(106,188,134),2,cv2.LINE_AA)
    center=pixel([status.get('x_m',0),status.get('y_m',0)])
    cv2.circle(canvas,center,5,(235,216,101),-1,cv2.LINE_AA)
    yaw=status.get('heading_rad',0)
    tip=(center[0]+int(15*math.cos(yaw)),center[1]-int(15*math.sin(yaw)))
    cv2.arrowedLine(canvas,center,tip,(235,216,101),2,cv2.LINE_AA,tipLength=.4)
