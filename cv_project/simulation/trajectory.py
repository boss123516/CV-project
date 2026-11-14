"""Arc-length sampled C1 Hermite paths for continuous, rounded walking turns."""
import bisect
import math


def unit(vector):
    length=math.hypot(*vector)
    return (vector[0]/length,vector[1]/length) if length>1e-9 else (1.,0.)


class WalkingTrajectory:
    def __init__(self,start,heading,tagged_goals):
        points=[tuple(start)];owners=[]
        for point,owner in tagged_goals:
            if math.dist(points[-1],point)>.001:
                points.append(tuple(point));owners.append(owner)
        if len(points)<2:raise ValueError('Walking trajectory requires distinct points')
        lengths=[math.dist(a,b) for a,b in zip(points,points[1:])]
        tangents=[]
        for i,point in enumerate(points):
            if i==0:
                direction=(math.cos(heading),math.sin(heading));magnitude=min(1.4,.65*lengths[0])
            elif i==len(points)-1:
                direction=unit((point[0]-points[i-1][0],point[1]-points[i-1][1]));magnitude=min(1.4,.65*lengths[-1])
            else:
                before=unit((point[0]-points[i-1][0],point[1]-points[i-1][1]))
                after=unit((points[i+1][0]-point[0],points[i+1][1]-point[1]))
                direction=unit((before[0]+after[0],before[1]+after[1]));magnitude=min(1.8,.8*min(lengths[i-1],lengths[i]))
            tangents.append((direction[0]*magnitude,direction[1]*magnitude))
        self.points=[points[0]];self.owners=[owners[0]];self.arc=[0.]
        for index,(a,b) in enumerate(zip(points,points[1:])):
            ma,mb=tangents[index:index+2]
            count=max(24,int(lengths[index]/.045))
            for step in range(1,count+1):
                t=step/count
                h00=2*t**3-3*t*t+1;h10=t**3-2*t*t+t
                h01=-2*t**3+3*t*t;h11=t**3-t*t
                xy=(h00*a[0]+h10*ma[0]+h01*b[0]+h11*mb[0],h00*a[1]+h10*ma[1]+h01*b[1]+h11*mb[1])
                distance=math.dist(self.points[-1],xy)
                self.points.append(xy);self.owners.append(owners[index]);self.arc.append(self.arc[-1]+distance)
        self.length=self.arc[-1]

    def at(self,distance):
        distance=max(0.,min(self.length,distance))
        index=max(0,min(len(self.arc)-2,bisect.bisect_right(self.arc,distance)-1))
        a,b=self.points[index:index+2];segment=max(1e-9,self.arc[index+1]-self.arc[index])
        ratio=(distance-self.arc[index])/segment
        return (a[0]+(b[0]-a[0])*ratio,a[1]+(b[1]-a[1])*ratio,self.owners[index+1])

    def heading(self,distance):
        a=self.at(distance-.04);b=self.at(distance+.04)
        return math.atan2(b[1]-a[1],b[0]-a[0])

    def curvature(self,distance):
        a=max(0.,distance-.16);b=min(self.length,distance+.16)
        angle=self.heading(b)-self.heading(a)
        return abs(math.atan2(math.sin(angle),math.cos(angle)))/max(.01,b-a)
