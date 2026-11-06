"""Clock direction and Korean guidance, independent of the detector backend."""
import math

NAMES={'bench':('벤치','가'),'traffic_cone':('교통 콘','이'),'pedestrian':('사람','이')}


def describe_sim_object(obj, pitch_rad=.12):
    """Webots FLU camera coordinates -> level horizontal bearing/range.

    The camera is pitched down; undo that pitch before reporting horizontal
    distance. This is the distance to the object's bounding-box center in the
    ground plane, not clearance to the nearest surface.
    """
    x,y,z=obj['camera_position_m']
    forward=math.cos(pitch_rad)*x-math.sin(pitch_rad)*z
    if forward<=0: return None
    bearing=math.degrees(math.atan2(-y,forward))
    hour=int(math.floor(bearing/30+.5))%12 or 12
    distance=math.hypot(forward,y)
    rounded=max(.5,math.floor(distance*2+.5)/2)
    number=str(int(rounded)) if rounded.is_integer() else str(rounded)
    name,particle=NAMES.get(obj['class'],(obj['class'],'이'))
    text=f'{hour}시 방향, {number}미터 앞에 {name}{particle} 있습니다.'
    return {'source':'webots_recognition_ground_truth','object_id':obj['id'],'class':obj['class'],'clock_hour':hour,'bearing_deg':round(bearing,2),'distance_m':round(distance,3),'forward_m':round(forward,3),'spoken_distance_m':rounded,'text':text}
