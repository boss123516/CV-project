"""Timed crossing choreography with moving cars and an explicit pedestrian gate.

Signal state is simulator scenario data, never a claimed vision classification.
"""
import math


class CrossingTraffic:
    def __init__(self,config):
        self.config=config
        self.reset()

    def reset(self):
        self.time=0.
        self.cars=[{'id':'TRAFFIC_CAR_A','x':-13.,'y':-1.7,'direction':1,'speed_mps':5.8},
                   {'id':'TRAFFIC_CAR_B','x':11.,'y':1.7,'direction':-1,'speed_mps':5.4}]

    @property
    def pedestrian_signal(self):
        return 'green' if 22.<=self.time<42. else 'red'

    @property
    def crosswalk_clear(self):
        return all(abs(car['x'])>3.15 for car in self.cars)

    def step(self,dt,occupied=False):
        # Hold the protective green while the scripted pedestrian is still crossing.
        if not (occupied and 41.8<=self.time<42.):self.time+=dt
        if self.time>=46.:self.time=0.
        vehicle_go=self.time<18.
        for car in self.cars:
            direction=car['direction'];stop=-3.8*direction
            before=(stop-car['x'])*direction
            if vehicle_go:
                target=5.8 if direction==1 else 5.4
            elif before>=-.05:
                target=min(5.8,math.sqrt(2*3.0*max(0.,before)))
            else:
                target=5.8 if abs(car['x'])<17 else 0.
            car['speed_mps']+=max(-3.0*dt,min(2.0*dt,target-car['speed_mps']))
            car['x']+=direction*car['speed_mps']*dt
            if vehicle_go and car['x']*direction>17:
                car['x']=-17.*direction
            if not vehicle_go and before>=0 and (stop-car['x'])*direction<0:
                car['x']=stop;car['speed_mps']=0.

    def snapshot(self):
        return {'source':'scenario_script','pedestrian_signal':self.pedestrian_signal,
                'crosswalk_clear':self.crosswalk_clear,'cycle_time_s':round(self.time,2),
                'vehicles':[dict(car) for car in self.cars]}
