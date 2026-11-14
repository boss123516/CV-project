#!/usr/bin/env python3
"""Build a textured neighborhood sidewalk and physically placed hazards."""
from pathlib import Path
import math
from build_textures import generate
ROOT=Path(__file__).resolve().parents[1]


def material(color='1 1 1',texture=None,rough=.8,metal=0,repeat=(1,1)):
    tex=f'baseColorMap ImageTexture {{ url [ "../textures/{texture}" ] }} textureTransform TextureTransform {{ scale {repeat[0]} {repeat[1]} }}' if texture else ''
    return f'PBRAppearance {{ baseColor {color} roughness {rough} metalness {metal} {tex} }}'


def shape(geometry,color='1 1 1',texture=None,**kwargs):
    return f'Shape {{ appearance {material(color,texture,**kwargs)} geometry {geometry} }}'


def pose(x,y,z,child,rotation=None):
    rot=f'rotation {rotation}' if rotation else ''
    return f'Pose {{ translation {x} {y} {z} {rot} children [ {child} ] }}\n'


def box(x,y,z,sx,sy,sz,color='1 1 1',texture=None,rotation=None,**kwargs):
    return pose(x,y,z,shape(f'Box {{ size {sx} {sy} {sz} }}',color,texture,**kwargs),rotation)


def cylinder(x,y,z,r,h,color='1 1 1',rotation=None,**kwargs):
    return pose(x,y,z,shape(f'Cylinder {{ radius {r} height {h} subdivision 16 }}',color,**kwargs),rotation)


def solid(name,children,position=(0,0,0),model=None,bounds=None,rotation=None):
    xyz=' '.join(map(str,position));rot=f'rotation {rotation}' if rotation else ''
    recognition=f'model "{model}" recognitionColors [ 0.8 0.4 0.2 ]' if model else ''
    bound=f'boundingObject {bounds}' if bounds else ''
    return f'DEF {name} Solid {{ translation {xyz} {rot} name "{name.lower()}" {recognition} children [\n{children}] {bound} }}\n'


def bounds_box(x,y,z,sx,sy,sz):
    return f'Pose {{ translation {x} {y} {z} children [ Box {{ size {sx} {sy} {sz} }} ] }}'


def facade(x,y,width,height,index,opposite=False):
    side=-1 if not opposite else 1;front=y+side*.32
    color=['0.89 0.86 0.79','0.74 0.78 0.75','0.75 0.70 0.63'][index%3]
    children=box(0,0,height/2,width,.75,height,color,'brick.png' if index%3==0 else 'concrete.png',repeat=(4,3))
    for wx in [-width*.32,0,width*.32]:
        children+=box(wx,side*.43,3.90,1.45,.075,1.32,'0.17 0.25 0.29',rough=.18,metal=.2)
        for dx in [-.73,.73]:children+=box(wx+dx,side*.49,3.90,.055,.06,1.42,'0.76 0.76 0.70')
        children+=box(wx,side*.49,3.90,.035,.06,1.3,'0.76 0.76 0.70')
        children+=box(wx,side*.49,3.22,1.57,.16,.1,'0.75 0.73 0.66')
    if not opposite:
        for wx in [-width*.29,width*.29]:
            children+=box(wx,side*.46,1.35,2.4,.08,2.2,'0.11 0.21 0.23',rough=.15,metal=.25)
            children+=box(wx-.90,side*.515,1.35,.045,.04,2.2,'0.66 0.67 0.63')
            children+=box(wx+.90,side*.515,1.35,.045,.04,2.2,'0.66 0.67 0.63')
            children+=box(wx,side*.52,.65,2.4,.04,.045,'0.66 0.67 0.63')
            # Warm interior shelves and simple posters add realistic background edges.
            children+=box(wx,side*.51,1.6,.63,.025,.81,'0.83 0.76 0.57')
            children+=box(wx+.75,side*.51,.43,.7,.025,.28,'0.53 0.38 0.22')
        children+=box(0,side*.48,1.24,1.10,.1,2.4,'0.06 0.13 0.15',rough=.2)
        children+=box(.38,side*.57,1.1,.045,.06,.45,'0.80 0.79 0.72',metal=.65)
        children+=box(0,side*.48,2.77,width-.7,.08,.35,'0.65 0.65 0.60',texture='concrete.png')
        awning='0.34 0.36 0.34'
        children+=box(0,side*.92,2.42,width-.6,.70,.08,awning,rotation=f'1 0 0 {side*.10}')
        children+=box(0,side*1.20,2.31,width-.6,.055,.23,awning)
    return solid(f'BUILDING_{"FAR" if opposite else "SHOP"}_{index}',children,(x,y,0))


def bench():
    children=''
    for y in [-.18,-.06,.06,.18]:children+=box(0,y,.47,1.75,.10,.065,texture='wood.png')
    for z in [.70,.88]:children+=box(0,.25,z,1.75,.065,.13,texture='wood.png')
    for x in [-.68,.68]:
        for y in [-.18,.19]:children+=box(x,y,.24,.05,.05,.46,'0.12 0.15 0.16',metal=.45)
        children+=box(x,.25,.64,.05,.05,.7,'0.12 0.15 0.16',metal=.45)
    return solid('BENCH',children,(5.5,1.03,0),'bench',bounds_box(0,.04,.48,1.8,.58,.96))


def signboard():
    children=''
    for side in [-1,1]:
        children+=box(side*.12,0,.65,.055,.68,1.05,texture='menu.png',rotation=f'0 1 0 {side*.18}')
        for y in [-.37,.37]:children+=box(side*.12,y,.61,.05,.055,1.22,'0.39 0.28 0.15',rotation=f'0 1 0 {side*.18}')
    children+=cylinder(0,0,1.19,.025,.78,'0.42 0.35 0.24',rotation='1 0 0 1.570796')
    return solid('SIGNBOARD',children,(11.0,.35,0),'signboard',bounds_box(0,0,.61,.55,.80,1.22))


def bollard():
    children=cylinder(0,0,.27,.105,.54,'0.28 0.30 0.29',texture='concrete.png')
    children+=cylinder(0,0,.43,.108,.07,'0.83 0.79 0.56')
    children+=cylinder(0,0,.04,.15,.08,'0.29 0.30 0.29')
    return solid('BOLLARD',children,(12.2,.43,0),'bollard',bounds_box(0,0,.28,.3,.3,.56))


def lamp():
    children=cylinder(0,0,2.2,.075,4.4,'0.47 0.49 0.46',texture='concrete.png')
    children+=cylinder(0,0,.14,.14,.28,'0.32 0.35 0.34')
    children+=cylinder(0,0,.85,.077,.16,'0.83 0.76 0.36')
    pole=solid('POLE',children,(18.4,-.45,0),'pole',bounds_box(0,0,2.2,.28,.28,4.4))
    pole+=box(18.4,-.94,4.35,.10,1.1,.12,'0.37 0.40 0.39')
    pole+=box(18.4,-1.4,4.24,.42,.65,.14,'0.25 0.29 0.29')
    pole+=box(18.4,-1.4,4.155,.34,.53,.025,'0.92 0.90 0.73')
    return pole


def cone():
    children=box(0,0,.035,.48,.48,.07,'0.16 0.17 0.17')
    children+=pose(0,0,.39,shape('Cone { bottomRadius .23 height .70 subdivision 32 }','0.95 0.25 0.035'))
    children+=cylinder(0,0,.41,.131,.09,'0.94 0.94 0.88')
    return solid('CONE',children,(24.2,.45,0),'traffic_cone',bounds_box(0,0,.38,.48,.48,.76))


def barrier():
    children=box(0,0,.82,.09,1.24,.47,texture='roadworks.png')
    for y in [-.56,.56]:
        children+=box(0,y,.54,.055,.055,1.08,'0.67 0.69 0.65',metal=.7)
        children+=box(0,y,.04,.60,.12,.08,'0.39 0.42 0.39')
        children+=pose(0,y,1.1,shape('Sphere { radius .055 subdivision 1 }','0.94 0.37 0.04'))
    return solid('BARRIER',children,(25.7,.85,0),'barrier',bounds_box(0,0,.58,.65,1.4,1.16))


def parked_car():
    children=box(0,0,.45,3.85,1.65,.43,'0.16 0.28 0.36',rough=.27,metal=.45)
    children+=box(-.22,0,.99,1.92,1.42,.64,'0.10 0.18 0.22',rough=.13,metal=.3)
    children+=box(-.22,0,1.34,1.95,1.45,.075,'0.16 0.28 0.36',rough=.3,metal=.4)
    children+=box(.79,0,1.0,.035,1.36,.62,'0.22 0.34 0.38',rotation='0 1 0 .30',rough=.12,metal=.3)
    children+=box(-1.22,0,1.0,.035,1.36,.62,'0.20 0.31 0.35',rotation='0 1 0 -.30',rough=.12,metal=.3)
    for side in [-1,1]:
        for x in [-1.22,1.22]:
            children+=cylinder(x,side*.82,.28,.28,.16,'0.055 0.06 0.06',rotation='1 0 0 1.570796')
            children+=cylinder(x,side*.915,.28,.15,.025,'0.64 0.66 0.63',rotation='1 0 0 1.570796',metal=.75)
        children+=box(-.24,side*.725,1.0,.055,.035,.64,'0.16 0.28 0.36')
        for x in [-.70,.31]:children+=box(x,side*.845,.65,.21,.035,.035,'0.74 0.75 0.69',metal=.6)
        children+=box(.70,side*.94,.91,.24,.22,.13,'0.16 0.28 0.36')
        children+=box(1.935,side*.55,.50,.035,.40,.17,'0.91 0.91 0.74',rough=.16)
        children+=box(-1.935,side*.55,.50,.035,.37,.15,'0.69 0.07 0.045',rough=.18)
    children+=box(1.96,0,.36,.025,.54,.17,'0.87 0.86 0.77')
    return solid('PARKED_CAR',children,(30.8,-2.8,-.16),'car',bounds_box(0,0,.70,4.,1.90,1.4))


def tree(x,y,index):
    children=cylinder(0,0,1.5,.12,3.,'0.30 0.22 0.14')
    children+=box(0,0,.17,.9,.9,.34,'0.39 0.40 0.35',texture='concrete.png')
    for dx,dy,dz,r in [(0,0,3.45,.9),(.5,0,3.6,.70),(-.4,.2,3.3,.75),(0,-.4,3.8,.70)]:
        children+=pose(dx,dy,dz,shape(f'Sphere {{ radius {r} subdivision 2 }}','0.22 0.34 0.19'))
    return solid(f'TREE_{index}',children,(x,y,0))


def build():
    generate()
    world='''#VRML_SIM R2025a utf8
EXTERNPROTO "../protos/vendor/Pedestrian.proto"
WorldInfo {
  title "Assistive Vision | Neighborhood Street"
  info [ "Textured urban sidewalk, partial occlusion, slender obstacles, roadworks and crossing pedestrian" "Depth and bearing are estimated from stereo images, not simulator object positions" ]
  basicTimeStep 32
}
DEF OVERVIEW Viewpoint {
  orientation -0.16795769054754286 0.3651770768903671 0.9156614640246379 0.9309686379817355
  position -4 -7 4.5
  fieldOfView 1.0
  near 0.1
  far 95
  follow ""
  followType "None"
}
Background { skyColor [ 0.64 0.75 0.85 ] }
DirectionalLight { direction -0.5 -0.35 -0.8 intensity 2.4 ambientIntensity 0.42 castShadows TRUE }
'''
    world+=solid('GROUND',box(20,-2,-.40,68,36,.45,'0.40 0.43 0.35'),bounds=bounds_box(20,-2,-.40,68,36,.45))
    world+=solid('ROAD',box(20,-4.6,-.21,64,6,.1,texture='asphalt.png',repeat=(22,3)),bounds=bounds_box(20,-4.6,-.21,64,6,.1))
    for x in range(-6,50,4):world+=box(x,-4.45,-.154,2.,.09,.012,'0.84 0.76 0.44')
    for y in [-1.84,-7.25]:world+=box(20,y,-.15,64,.07,.012,'0.88 0.87 0.80')
    pavement=''
    for x in range(-7,49):
        texture='asphalt.png' if 35<=x<38 else 'pavers.png'
        pavement+=box(x+.5,0,-.065,.994,3.,.13,texture=texture,repeat=(1,2))
        pavement+=box(x+.5,1.86,-.065,.994,.70,.13,texture='concrete.png')
        if not 35<=x<38:
            pavement+=box(x+.5,-1.56,-.08,.99,.16,.16,texture='concrete.png')
        pavement+=box(x+.5,-8.0,-.07,.994,1.1,.18,texture='concrete.png')
    world+=solid('SIDEWALK',pavement,bounds=bounds_box(20,0,-.065,64,3,.13))
    # A tactile guidance strip and a blister warning patch at the driveway.
    for x in range(-5,44):
        world+=box(x+.5,-.98,.006,.995,.28,.012,texture='tactile.png')
    for x in [34.6,38.1]:world+=box(x,-.98,.009,.45,.88,.012,texture='blister.png')
    # Crosswalk across the road, alongside a curb ramp and drainage grate.
    for y in np_range(-7.0,-1.9,.65):world+=box(32.8,y,-.149,2.0,.38,.015,'0.87 0.86 0.80')
    for i in range(8):world+=box(35.5+i*.10,-1.4,-.004,.055,.46,.015,'0.22 0.26 0.25',metal=.5)
    for index,x in enumerate([0.,9.,18.,27.,36.,45.]):world+=facade(x,2.95,8.85,5.5+(index%2)*.6,index)
    for index,x in enumerate([1.,12.,23.,34.,45.]):world+=facade(x,-9.45,10.8,6.0+(index%3),index,opposite=True)
    world+=tree(1.7,1.8,0)+tree(16.0,1.8,1)+tree(36.0,1.8,2)
    # Drain covers, utility cabinet and two small planters are background street details.
    for x in [7.5,21.,34.]:
        world+=cylinder(x,-1.0,.007,.23,.014,'0.28 0.30 0.28',texture='concrete.png')
    world+=box(20.3,1.85,.56,.48,.45,1.12,'0.42 0.45 0.42',texture='concrete.png')
    for x in [8.,28.]:
        world+=box(x,1.8,.22,.65,.62,.44,'0.38 0.26 0.19')
        world+=pose(x,1.8,.65,shape('Sphere { radius .37 subdivision 2 }','0.26 0.38 0.20'))
    # A worn asphalt patch and shiny wet patch create changing texture/reflectance.
    world+=box(26.,1.1,.006,2.,.68,.012,texture='asphalt.png')
    world+=box(28.6,-1.1,.008,1.8,.45,.016,'0.23 0.27 0.26',rough=.16)
    world+=bench()+signboard()+bollard()+lamp()+cone()+barrier()+parked_car()
    world+='''DEF TARGET_PERSON Pedestrian {
  translation 32 1.30 1.27 rotation 0 0 1 -1.570796
  name "crossing_person" shirtColor 0.66 0.22 0.15 pantsColor 0.15 0.20 0.24
  enableBoundingObject TRUE
  controller "<none>" controllerArgs [ "animated_by_walker_supervisor" ]
}
'''
    world+=(ROOT/'config/walker_rig.wbt.inc').read_text()
    (ROOT/'worlds/assistive_sidewalk.wbt').write_text(world)
    print(ROOT/'worlds/assistive_sidewalk.wbt')


def np_range(start,stop,step):
    while start<stop:
        yield round(start,3);start+=step


if __name__=='__main__':build()
