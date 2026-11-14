"""Destination/obstruction/detour choreography with bounded speed and turning.

This is a scenario driver, not a perception-driven navigation planner. A contact
is an explicitly staged cane tap; no rigid-body collision or measured depth is
fabricated. The detector/depth pipeline runs independently on the rendered view.
"""
from dataclasses import dataclass
import math
from cv_project.simulation.trajectory import WalkingTrajectory
from cv_project.simulation.traffic import CrossingTraffic


def wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


@dataclass
class MissionSample:
    x: float
    y: float
    heading: float
    speed: float
    signed_distance: float
    phase: str
    action_id: str
    caption: str
    arrived: bool
    lap: int
    contact_count: int


class MissionDriver:
    MOVEMENT = {'walk', 'detour', 'backtrack'}

    def __init__(self, config, cruise_speed=.72):
        self.config = config
        self.actions = config['actions']
        if not self.actions or self.actions[-1]['kind'] != 'arrive':
            raise ValueError('A destination mission must end with an arrive action')
        self.destination = tuple(config['destination']['position'])
        self.cruise_speed = cruise_speed
        self.max_yaw_rate = float(config.get('max_yaw_rate_rad_s', .85))
        self.traffic=CrossingTraffic(config['traffic_signal']) if 'traffic_signal' in config else None
        self.lap = -1
        self.reset()

    def reset(self):
        self.x, self.y = map(float, self.config['start'])
        self.heading = float(self.config.get('heading_rad', 0.))
        self.speed = 0.
        self.index = 0
        self.point_index = 0
        self.elapsed = 0.
        self.contact_count = 0
        self.events = []
        self.lap += 1
        self.enter_heading = self.heading
        self._entered = False
        self.trajectory=None
        self.trajectory_distance=0.
        self.green_announced_at=None
        if self.traffic:self.traffic.reset()

    @property
    def action(self):
        return self.actions[min(self.index, len(self.actions)-1)]

    @property
    def arrived(self):
        return self.action['kind'] == 'arrive'

    @property
    def distance_to_goal(self):
        return math.hypot(self.destination[0]-self.x, self.destination[1]-self.y)

    def _advance(self):
        self.index += 1
        self.point_index = 0
        self.elapsed = 0.
        self._entered = False
        self.speed = 0.
        self.trajectory=None

    def _enter(self):
        self._entered = True
        self.enter_heading = self.heading
        if self.action['kind']=='signal_wait':
            self.events.append({'type':'pedestrian_red_wait','action_id':self.action['id'],
                                'position':[self.x,self.y],'source':'scenario_script'})
        if self.action['kind'] in ['detour','arrive']:
            self.events.append({'type':'detour_started' if self.action['kind']=='detour' else 'destination_reached',
                                'action_id':self.action['id'],'position':[self.x,self.y],'source':'scenario_script'})
        if self.action['kind'] == 'contact':
            self.contact_count += 1
            self.events.append({'type': 'staged_cane_contact', 'action_id': self.action['id'],
                                'position': [self.x, self.y], 'source': 'scenario_script'})

    def step(self, dt, paused=False):
        if dt <= 0:
            raise ValueError('dt must be positive')
        if not self._entered:
            self._enter()
        if self.traffic and not paused:
            self.traffic.step(dt,occupied=self.action['id']=='cross_road')
        action = self.action
        kind = action['kind']
        moved = 0.
        if paused:
            self.speed = 0.
        elif kind=='signal_wait':
            self.speed=0.
            if self.traffic and self.traffic.pedestrian_signal=='green' and self.traffic.crosswalk_clear:
                if self.green_announced_at is None:
                    self.green_announced_at=self.traffic.time
                    self.events.append({'type':'pedestrian_green_clear','action_id':action['id'],'position':[self.x,self.y],'source':'scenario_script'})
                elif self.traffic.time-self.green_announced_at>=2.:self._advance()
        elif kind in {'walk','detour'}:
            if self.trajectory is None:
                end=self.index;goals=[]
                while end<len(self.actions) and self.actions[end]['kind'] in {'walk','detour'}:
                    goals.extend((point,end) for point in self.actions[end]['waypoints']);end+=1
                    if self.actions[end-1]['id']=='cross_road':break
                self.trajectory=WalkingTrajectory((self.x,self.y),self.heading,goals)
                self.trajectory_distance=0.;self.group_end=end
            remaining=self.trajectory.length-self.trajectory_distance
            curvature=max(self.trajectory.curvature(self.trajectory_distance),self.trajectory.curvature(self.trajectory_distance+.25))
            limit=min(self.cruise_speed,float(action.get('speed_mps',self.cruise_speed)))
            limit=min(limit,math.sqrt(.38/max(.01,curvature)),self.max_yaw_rate/max(.1,curvature))
            target=min(limit,math.sqrt(2*.8*max(0.,remaining)))
            self.speed+=max(-1.*dt,min(.65*dt,target-self.speed))
            amount=min(remaining,self.speed*dt)
            self.trajectory_distance+=amount
            self.x,self.y,owner=self.trajectory.at(self.trajectory_distance)
            wanted=self.trajectory.heading(self.trajectory_distance)
            error=wrap_angle(wanted-self.heading)
            self.heading=wrap_angle(self.heading+max(-self.max_yaw_rate*dt,min(self.max_yaw_rate*dt,error)))
            moved=amount
            if owner!=self.index:
                self.index=owner;self._entered=False;self._enter()
            if remaining<.018:
                self.x,self.y,_=self.trajectory.at(self.trajectory.length)
                self.index=self.group_end-1;self._advance()
        elif kind == 'backtrack':
            points = action['waypoints']
            gx, gy = points[self.point_index]
            dx, dy = gx-self.x, gy-self.y
            distance = math.hypot(dx, dy)
            if distance < .025:
                self.x, self.y = float(gx), float(gy)
                self.point_index += 1
                self.speed = 0.
                if self.point_index >= len(points):
                    self._advance()
            else:
                backward = kind == 'backtrack'
                wanted = self.enter_heading if backward else math.atan2(dy, dx)
                error = wrap_angle(wanted-self.heading)
                turn = max(-self.max_yaw_rate*dt, min(self.max_yaw_rate*dt, error))
                self.heading = wrap_angle(self.heading+turn)
                limit = min(self.cruise_speed, float(action.get('speed_mps', self.cruise_speed)))
                # Turn at corners before translating; brake as the waypoint approaches.
                target = min(limit, math.sqrt(2*.8*distance)) if abs(error) < .22 else 0.
                self.speed += max(-1.0*dt, min(.65*dt, target-self.speed))
                amount = min(distance, self.speed*dt)
                self.x += dx/distance*amount
                self.y += dy/distance*amount
                moved = -amount if backward else amount
        else:
            self.speed = 0.
            self.elapsed += dt
            if kind == 'scan':
                duration = float(action.get('duration_s', 3.))
                sweep=min(float(action.get('sweep_rad', .48)), .85*self.max_yaw_rate*duration/(2*math.pi))
                self.heading = wrap_angle(self.enter_heading + sweep*math.sin(2*math.pi*min(1.,self.elapsed/duration)))
            if kind == 'arrive':
                repeat = self.config.get('repeat_after_s')
                if repeat is not None and self.elapsed >= float(repeat):
                    self.reset()
            elif self.elapsed >= float(action.get('duration_s', 1.)):
                self.heading = self.enter_heading
                self._advance()
        current = self.action
        signed_speed = -self.speed if current['kind'] == 'backtrack' else self.speed
        return MissionSample(self.x,self.y,self.heading,signed_speed,moved,current['kind'],
                             current['id'],current.get('caption_ko',''),self.arrived,self.lap,self.contact_count)

    def status(self):
        action = self.action
        return {'navigation_source':'scenario_script','phase':action['kind'],'action_id':action['id'],
                'caption_ko':action.get('caption_ko',''),'destination':self.config['destination'],
                'distance_to_goal_m':round(self.distance_to_goal,2),'arrived':self.arrived,
                'contact_count':self.contact_count,'action_index':self.index,
                'action_count':len(self.actions),'recent_events':self.events[-3:],
                **({'traffic':self.traffic.snapshot()} if self.traffic else {})}

    def map_data(self):
        if hasattr(self,'_map_cache'):return self._map_cache
        legs=[];position=tuple(self.config['start']);heading=float(self.config.get('heading_rad',0.));index=0
        while index<len(self.actions):
            action=self.actions[index]
            if action['kind'] in {'walk','detour'}:
                goals=[];end=index
                while end<len(self.actions) and self.actions[end]['kind'] in {'walk','detour'}:
                    goals.extend((point,end) for point in self.actions[end]['waypoints']);end+=1
                    if self.actions[end-1]['id']=='cross_road':break
                trajectory=WalkingTrajectory(position,heading,goals)
                current_kind=None
                for point,owner in zip(trajectory.points,trajectory.owners):
                    kind=self.actions[owner]['kind']
                    if current_kind!=kind:legs.append({'kind':kind,'points':[]});current_kind=kind
                    legs[-1]['points'].append(point)
                position=trajectory.points[-1];heading=trajectory.heading(trajectory.length);index=end
            elif action['kind']=='backtrack':
                legs.append({'kind':'backtrack','points':action['waypoints']})
                position=tuple(action['waypoints'][-1]);index+=1
            else:index+=1
        self._map_cache={'start':self.config['start'],'destination':self.config['destination'],
                         'legs':legs,'obstacles':self.config.get('obstacles',[]),'road':self.config.get('road')}
        return self._map_cache
