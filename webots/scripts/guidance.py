"""Korean phrasing for measured stereo results; no simulator geometry input."""
from pathlib import Path
import json
import math

CATALOG=json.loads((Path(__file__).resolve().parents[1]/'config/object_classes.json').read_text())


def describe_estimate(obj):
    if not obj.get('valid'):return None
    rounded=max(.5,math.floor(obj['distance_m']*2+.5)/2)
    number=str(int(rounded)) if rounded.is_integer() else str(rounded)
    definition=CATALOG.get(obj['class'],{'name_ko':obj['class'],'particle':'이'})
    text=f"{obj['clock_hour']}시 방향, {number}미터 앞에 {definition['name_ko']}{definition['particle']} 있습니다."
    return dict(obj,object_id=obj.get('id'),spoken_distance_m=rounded,text=text)
