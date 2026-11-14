#!/usr/bin/env python3
"""Three unbranded architectural settings with destinations and detour lanes."""
from pathlib import Path
import json
import math
from build_world import box,cylinder,solid,shape,pose,bounds_box,tree,parked_car
from build_textures import generate
ROOT=Path(__file__).resolve().parents[1]


def header(title):
    return '''#VRML_SIM R2025a utf8
EXTERNPROTO "../protos/vendor/Pedestrian.proto"
WorldInfo { title "'''+title+'''" basicTimeStep 32 info [ "Destination mission with explicitly scripted cane contact and detour" ] }
DEF OVERVIEW Viewpoint {
  orientation -0.167958 0.365177 0.915661 0.930969
  position -4 -7 4.5 fieldOfView 1.0 near .1 far 75 followType "None"
}
Background { skyColor [ .66 .74 .80 ] }
DirectionalLight { direction -.55 -.45 -.8 intensity 2.1 ambientIntensity .44 castShadows TRUE }
'''


def ground(size=48,level=-.025):
    z=level-.175
    return solid('GROUND',box(3,1,z,size,size,.35,'.35 .39 .33'),bounds=bounds_box(3,1,z,size,size,.35))


def paving(x,y,sx,sy,texture='pavers.png'):
    return solid(f'PAVING_{str(x).replace("-","N").replace(".","_")}_{str(y).replace("-","N").replace(".","_")}',
                 box(0,0,-.045,sx,sy,.09,texture=texture,repeat=(max(1,sx/2),max(1,sy/2))),
                 (x,y,0),bounds=bounds_box(0,0,-.045,sx,sy,.09))


def residential_block(name,x,y,width,depth,height,rotation=0):
    children=box(0,0,height/2,width,depth,height,'.86 .84 .78',texture='concrete.png',repeat=(4,4))
    children+=box(0,-depth/2-.025,.30,width,.08,.6,'.37 .38 .36')
    count=max(2,int(width/1.7))
    for floor in range(1,max(2,int(height/2.6))+1):
        z=1.35+(floor-1)*2.45
        if z+.6>height:continue
        for index in range(count):
            wx=-width/2+(index+.5)*width/count
            children+=box(wx,-depth/2-.045,z,.92,.08,1.12,'.20 .28 .30',rough=.22,metal=.15)
            children+=box(wx,-depth/2-.095,z,.038,.035,1.12,'.67 .68 .63')
            children+=box(wx,-depth/2-.12,z-.58,1.02,.24,.06,'.64 .64 .58')
            children+=box(wx,-depth/2-.12,z+.59,1.02,.10,.04,'.69 .69 .63')
    # A plain entrance, door frame and canopy; no invented store names.
    children+=box(0,-depth/2-.05,1.13,1.32,.10,2.26,'.12 .19 .20',rough=.2)
    for dx in [-.72,.72]:children+=box(dx,-depth/2-.10,1.15,.09,.14,2.40,'.57 .59 .56')
    children+=box(0,-depth/2-.10,2.36,1.52,.14,.10,'.57 .59 .56')
    children+=box(.40,-depth/2-.15,1.1,.04,.07,.38,'.76 .76 .72',metal=.7)
    children+=box(0,-depth/2-.46,2.5,2.0,.92,.10,'.40 .42 .40')
    children+=box(0,0,height+.045,width+.16,depth+.16,.09,'.47 .49 .46')
    return solid(name,children,(x,y,0),bounds=bounds_box(0,0,height/2,width,depth,height),rotation=f'0 0 1 {rotation}')


def fence_barrier(x,y,width=2.8):
    children=box(0,0,.82,.08,width,.44,texture='roadworks.png')
    children+=box(0,0,.09,.06,width,.07,'.48 .52 .49',metal=.55)
    for index in range(max(1,int(width/.22))):
        yy=-width/2+.11+index*.22
        children+=box(0,yy,.37,.025,.023,.56,'.48 .52 .49',metal=.55)
    for side in [-1,1]:
        children+=box(0,side*(width/2-.1),.6,.055,.055,1.2,'.56 .59 .56',metal=.5)
        children+=box(0,side*(width/2-.1),.04,.62,.14,.08,'.39 .42 .40')
        children+=pose(0,side*(width/2-.1),1.22,shape('Sphere { radius .055 subdivision 1 }','.9 .38 .04'))
    return solid('MISSION_BARRIER',children,(x,y,0),'barrier',bounds_box(0,0,.63,.60,width,1.26))


def planter(name,x,y,sx,sy):
    children=box(0,0,.24,sx,sy,.48,'.45 .45 .39',texture='concrete.png')
    children+=box(0,0,.49,sx-.08,sy-.08,.05,'.24 .22 .16')
    for index in range(max(1,int(sx/.5))):
        xx=-sx/2+.3+index*.5
        children+=pose(xx,0,.74,shape('Sphere { radius .35 subdivision 2 }','.26 .35 .21'))
    return solid(name,children,(x,y,0),'planter' if name=='MISSION_PLANTER' else None,
                 bounds_box(0,0,.5,sx,sy,1.0))


def bench_at(name,x,y,rotation=0):
    children=''
    for yy in [-.18,-.06,.06,.18]:children+=box(0,yy,.46,1.7,.10,.065,texture='wood.png')
    for z in [.66,.83]:children+=box(0,.24,z,1.7,.06,.12,texture='wood.png')
    for xx in [-.63,.63]:
        children+=box(xx,0,.23,.06,.42,.46,'.19 .22 .21')
        children+=box(xx,.24,.62,.06,.06,.7,'.19 .22 .21')
    return solid(name,children,(x,y,0),'bench',bounds_box(0,.02,.45,1.75,.55,.90),f'0 0 1 {rotation}')


def drain(x,y,angle=0):
    parts=box(0,0,.006,.64,.36,.012,'.27 .30 .28',metal=.5)
    for offset in [-.24,-.16,-.08,0,.08,.16,.24]:parts+=box(offset,0,.014,.028,.29,.012,'.13 .16 .14')
    return pose(x,y,0,parts,f'0 0 1 {angle}')


def rail(x,y,length,angle=0):
    parts=''
    for xx in [-length/2,length/2]:parts+=cylinder(xx,0,.48,.025,.96,'.59 .63 .61',metal=.7)
    parts+=cylinder(0,0,.95,.027,length,'.59 .63 .61',rotation='0 1 0 1.570796',metal=.7)
    return pose(x,y,0,parts,f'0 0 1 {angle}')


def finish(world,identifier):
    scene=json.loads((ROOT.parent/'scenarios'/identifier/'scene.json').read_text())
    actor=scene.get('actor',{'start':[100,100]});sx,sy=actor['start']
    world+=f'''DEF TARGET_PERSON Pedestrian {{
      translation {sx} {sy} 1.215 name "crossing_person"
      shirtColor .44 .23 .17 pantsColor .16 .19 .21 enableBoundingObject TRUE
      controller "<none>" controllerArgs [ "animated_by_supervisor" ]
    }}\n'''
    world+=(ROOT/'config/walker_rig.wbt.inc').read_text()
    target=ROOT/'worlds'/f'{identifier}.wbt';target.write_text(world)
    print(target)


def residential():
    world=header('Assistive Vision | Residential Detour')+ground()
    world+=paving(8,0,23,3.4)+paving(6.8,-2.8,7.2,2.4,'concrete.png')
    world+=paving(4.25,-1.8,2.0,3.6)+paving(9.4,-1.8,2.0,3.6)
    world+=paving(12,4,3.2,9)+paving(15,7,8,3.0)
    world+=residential_block('BLOCK_A',.3,4.8,6,3.5,6.0)
    world+=residential_block('BLOCK_B',7.2,4.8,5.8,3.5,8.0)
    world+=residential_block('DESTINATION_BUILDING',20.5,7,6,3.2,5.8,-math.pi/2)
    world+=residential_block('SOUTH_BLOCK',14,-5.4,8,3.0,5.5,math.pi)
    world+=fence_barrier(6,0)
    world+=bench_at('BENCH_RESIDENTIAL',14.5,8.0)
    world+=tree(-1.8,2.7,40)+tree(16.8,4.5,41)
    world+=planter('SIDE_PLANTER',2.0,1.8,1.0,.75)
    for x,y in [(3,-1.2),(10.5,-1.2),(12.8,5.6)]:world+=drain(x,y)
    # Low edge walls frame the service alley without closing the bypass.
    world+=box(6.8,-4.15,.25,7.6,.16,.5,'.61 .61 .55',texture='concrete.png')
    finish(world,'residential_detour')


def courtyard():
    world=header('Assistive Vision | Courtyard Detour')+ground()
    world+=paving(2,0,25,19)+box(2,0,.003,6,8,.006,texture='concrete.png',repeat=(3,4))
    world+=residential_block('NORTH_BLOCK',5,9,16,3.6,8.0)
    world+=residential_block('WEST_BLOCK',-10,-.5,14,3.5,6.0,math.pi/2)
    world+=residential_block('EAST_BLOCK',15,0,12,3.5,6.0,-math.pi/2)
    world+=planter('MISSION_PLANTER',-1,1.2,3.3,.9)
    world+=planter('PLANTER_NORTH',-.5,5.7,3.5,1.1)
    world+=planter('PLANTER_EAST',7.6,-1.8,4.2,1.2)
    world+=bench_at('BENCH_WEST',-5,3.8,math.pi/2)
    world+=bench_at('BENCH_EAST',10.3,3.8,-math.pi/2)
    world+=tree(-5.8,-1.2,50)+tree(10.8,-4.5,51)
    for x in [-6,-2,2,6,10]:world+=box(x,-7,.008,.035,3.5,.016,'.43 .44 .40')
    for x,y in [(-3,-3),(4,-3),(8,4.5)]:world+=drain(x,y)
    finish(world,'courtyard_detour')


def station():
    world=header('Assistive Vision | Station Access Detour')+ground(55)
    world+=paving(1,-.8,27,9)+paving(7,5.1,10,9,'concrete.png')
    # Actual station entrance canopy and glazed side walls, without a brand banner.
    world+=box(8,8.7,3.05,8,4.6,.20,'.40 .43 .42',metal=.15)
    for x in [4.25,11.75]:
        world+=box(x,8.5,1.5,.20,.20,3.0,'.52 .56 .55',metal=.4)
        world+=box(x,9.3,1.4,.05,2.5,2.5,'.24 .34 .37',rough=.17,metal=.2)
    world+=box(8,10.8,1.35,7.5,.18,2.7,'.24 .29 .30')
    world+=box(8,10.65,1.15,3.6,.04,2.3,'.085 .12 .13')
    world+=box(8,8.8,.008,3.2,3.6,.016,'.30 .34 .33',texture='concrete.png')
    world+=rail(6.3,8.4,3.5,math.pi/2)+rail(9.7,8.4,3.5,math.pi/2)
    world+=fence_barrier(3,-2)
    for y in [-4.6,.5]:
        world+=solid('BOLLARD_'+('N' if y<0 else 'P'),cylinder(0,0,.34,.09,.68,'.38 .42 .41'),
                     (3,y,0),'bollard',bounds_box(0,0,.34,.18,.18,.68))
    world+=paving(1,-7.5,31,4,'asphalt.png')
    for x in range(-12,17,4):world+=box(x,-7.5,.005,2.0,.08,.01,'.80 .77 .58')
    for y in [-8.6,-7.9,-7.2,-6.5]:world+=box(-4,y,.008,2.3,.42,.016,'.83 .83 .76')
    world+=residential_block('BACKGROUND_BUILDING',-9,7,10,3.4,8.0)
    world+=bench_at('STATION_BENCH',-5,3.0)
    world+=tree(-10,2,60)+tree(13,3,61)
    for x,y in [(-4,-4.2),(1,-4.2),(5,3.5)]:world+=drain(x,y)
    # Tactile approach strip is a surface cue, not a glowing goal marker.
    world+=box(6.8,4.3,.008,.28,6.0,.016,texture='tactile.png',repeat=(1,6))
    finish(world,'station_access_detour')





def signal_lamp(x,y):
    world=cylinder(x,y,1.22,.055,2.44,'.39 .43 .40')
    world+=box(x,y,2.35,.36,.20,.86,'.075 .085 .075')
    for label,z,color in [('RED',2.55,'1 .05 .025'),('GREEN',2.17,'.02 .12 .045')]:
        app=f'DEF PED_{label}_APP PBRAppearance {{ baseColor {color} emissiveColor {color if label=="RED" else "0 0 0"} roughness .45 metalness 0 }}'
        lamp=f'Shape {{ appearance {app} geometry Cylinder {{ radius .12 height .018 subdivision 24 }} }}'
        world+=pose(x,y-.115,z,lamp,'1 0 0 1.570796')
        world+=box(x,y-.17,z+.15,.30,.30,.035,'.08 .09 .08')
    return world


def crossing_world():
    world=header('Assistive Vision | Signalized Crossing')+ground(58,level=-.20)
    world+=solid('TRAFFIC_ROAD',box(0,0,-.165,38,7.2,.09,texture='asphalt.png',repeat=(18,3)),bounds=bounds_box(0,0,-.165,38,7.2,.09))
    world+=paving(0,-7.1,36,5.6)+paving(0,7.1,36,5.6)
    for x in range(-16,18,4):
        if abs(x)>2:world+=box(x,0,-.108,2,.07,.014,'.85 .78 .47')
    for y in [-2.9,-2.2,-1.5,-.8,-.1,.6,1.3,2.0,2.7]:
        world+=box(0,y,-.107,2.6,.40,.016,'.88 .87 .80')
    for side in [-1,1]:
        for x in [-9.4,9.4]:world+=box(x,side*3.72,-.06,15.2,.20,.12,texture='concrete.png',repeat=(8,1))
        y0=side*3.6;y1=side*4.3
        points=f'-1.7 {y0} -.12, 1.7 {y0} -.12, 1.7 {y1} 0, -1.7 {y1} 0'
        indices='0 1 2 3 -1' if side>0 else '3 2 1 0 -1'
        ramp=f'IndexedFaceSet {{ coord Coordinate {{ point [ {points} ] }} coordIndex [ {indices} ] }}'
        world+=shape(ramp,'.72 .71 .65',texture='concrete.png')
        world+=box(0,side*4.65,.006,2.8,.36,.012,texture='blister.png',repeat=(5,1))
    world+=signal_lamp(1.35,4.6)
    world+=residential_block('NORTH_BUILDING',5,11.2,13,3.6,7)
    world+=residential_block('SOUTH_BUILDING',-8,-11.5,9,3.4,6,math.pi)
    world+=tree(-6,6.4,70)+tree(8,-6.5,71)
    world+=bench_at('CROSSING_BENCH',5,5.6)
    for name,x,y in [('A',-13,-1.7),('B',11,1.7)]:
        car=parked_car()
        original='translation 30.8 -2.8 -0.16'
        assert original in car
        car=car.replace('DEF PARKED_CAR',f'DEF TRAFFIC_CAR_{name}',1).replace(original,f'translation {x} {y} -.12',1)
        car=car.replace('name "parked_car"',f'name "traffic_car_{name.lower()}"',1)
        world+=car
    finish(world,'signalized_crossing')


if __name__=='__main__':
    generate();residential();courtyard();station();crossing_world()
