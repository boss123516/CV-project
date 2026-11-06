#!/usr/bin/env python3
"""Generate a small, dependency-free assistive walking scene."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def appearance(color, metal=0):
    return f'PBRAppearance {{ baseColor {color} roughness 0.8 metalness {metal} }}'

def box(x,y,z,sx,sy,sz,color):
    return f'Pose {{ translation {x} {y} {z} children [ Shape {{ appearance {appearance(color)} geometry Box {{ size {sx} {sy} {sz} }} }} ] }}'

world = '''#VRML_SIM R2025a utf8
EXTERNPROTO "../protos/vendor/Pedestrian.proto"
WorldInfo {
  title "Assistive Vision | Stereo Walking Lab"
  info [ "Sparse sidewalk: bench, cone and person" "Stereo RGB: 640x480, 12 cm baseline, 65 degree horizontal FOV" ]
  basicTimeStep 32
}
DEF OVERVIEW Viewpoint {
  orientation -0.14424710640725608 0.3899370592013912 0.9094733982665486 0.7726155506271932
  position -4 -6 4
  near 0.1
  follow "assistive_walker"
  followType "Tracking Shot"
}
Background { skyColor [ 0.71 0.82 0.91 ] }
DirectionalLight { direction -0.4 0.3 -1 intensity 2.2 ambientIntensity 0.5 castShadows TRUE }
'''
world += 'Solid { name "ground" children [\n' + box(13,0,-.13,38,22,.2,'0.32 0.43 0.32') + '] boundingObject Pose { translation 13 0 -0.13 children [ Box { size 38 22 0.2 } ] } }\n'
world += 'Solid { name "sidewalk" children [\n'
for x in range(-3,31):
    c=.58 + .018*(x%3)
    world += box(x+.5,0,-.025,.99,4,.05,f'{c} {c+.025} {c+.035}')+'\n'
for side in [-1,1]:
    world += box(13,side*2.12,.06,34,.22,.18,'0.80 0.81 0.79')+'\n'
    wall_height=2.2 if side==1 else .35
    world += box(13,side*3.15,wall_height/2,36,.16,wall_height,'0.77 0.81 0.82')+'\n'
world += '] boundingObject Pose { translation 13 0 -0.025 children [ Box { size 34 4 0.05 } ] } }\n'
# The controller shows one station at a time, spaced 8 m apart.
world += 'DEF BENCH Solid { translation 6 1.02 0 rotation 0 0 1 -1.570796 name "wooden_bench" model "bench" recognitionColors [ 0.55 0.28 0.12 ] children [\n'
for y in [-.16,0,.16]:
    world += box(0,y,.47,1.5,.13,.07,'0.50 0.27 0.12')+'\n'
for z in [.68,.85]:
    world += box(0,.24,z,1.5,.07,.13,'0.55 0.31 0.15')+'\n'
for x in [-.58,.58]:
    for y in [-.16,.19]:
        world += box(x,y,.24,.055,.055,.46,'0.10 0.14 0.17')+'\n'
    world += box(x,.25,.62,.055,.055,.65,'0.10 0.14 0.17')+'\n'
world += '] boundingObject Pose { translation 0 0.04 0.47 children [ Box { size 1.5 0.55 0.94 } ] } }\n'
world += '''DEF CONE Solid {
  translation 14 -0.78 0 name "traffic_cone" model "traffic_cone"
  recognitionColors [ 1 0.35 0.04 ]
  children [
'''+box(0,0,.035,.5,.5,.07,'0.13 0.15 0.16')+'''
    Pose { translation 0 0 0.39 children [ Shape { appearance PBRAppearance { baseColor 1 0.25 0.025 roughness 0.8 metalness 0 } geometry Cone { bottomRadius 0.23 height 0.70 subdivision 32 } } ] }
    Pose { translation 0 0 0.41 children [ Shape { appearance PBRAppearance { baseColor 0.95 0.96 0.94 roughness 0.6 metalness 0 } geometry Cylinder { radius 0.131 height 0.09 subdivision 32 } } ] }
  ]
  boundingObject Pose { translation 0 0 0.38 children [ Cylinder { radius 0.25 height 0.76 } ] }
}
DEF TARGET_PERSON Pedestrian {
  translation 22 0.85 1.27 rotation 0 0 1 3.14159
  name "oncoming_person" shirtColor 0.75 0.23 0.18 pantsColor 0.12 0.19 0.29
  enableBoundingObject TRUE
}
DEF WALKER Pedestrian {
  translation 0 0 1.27 name "assistive_walker"
  controller "assistive_walker" controllerArgs [ "--assistive" ]
  shirtColor 0.08 0.35 0.60 pantsColor 0.12 0.15 0.2
  bodySlot [
    Pose { translation 0.20 0 0.40 children [ Shape { appearance PBRAppearance { baseColor 0.035 0.05 0.07 roughness 0.5 metalness 0.2 } geometry Box { size 0.04 0.21 0.045 } } ] }
    DEF LEFT_CAMERA Camera {
      translation 0.235 0.06 0.40 rotation 0 1 0 0.12
      name "left_camera" width 640 height 480 fieldOfView 1.1344640138
      near 0.05 far 10 antiAliasing TRUE
      recognition Recognition { maxRange 9.5 maxObjects 4 occlusion 1 }
    }
    DEF RIGHT_CAMERA Camera {
      translation 0.235 -0.06 0.40 rotation 0 1 0 0.12
      name "right_camera" width 640 height 480 fieldOfView 1.1344640138
      near 0.05 far 10 antiAliasing TRUE
    }
    DEF CANE_SWEEP Pose {
      translation 0.12 -0.28 -0.45
      children [
        Pose { translation 0.40 0 -0.35 rotation 0 1 0 -0.85 children [
          Shape { appearance PBRAppearance { baseColor 0.95 0.96 0.94 roughness 0.5 metalness 0 } geometry Cylinder { radius 0.012 height 1.10 } }
          Pose { translation 0 0 -0.45 children [ Shape { appearance PBRAppearance { baseColor 0.9 0.10 0.07 roughness 0.7 metalness 0 } geometry Cylinder { radius 0.014 height 0.20 } } ] }
          Pose { translation 0 0 0.48 children [ Shape { appearance PBRAppearance { baseColor 0.06 0.07 0.08 roughness 0.7 metalness 0 } geometry Cylinder { radius 0.021 height 0.18 } } ] }
        ] }
      ]
    }
  ]
}
'''
(ROOT/'worlds/assistive_sidewalk.wbt').write_text(world)
print(ROOT/'worlds/assistive_sidewalk.wbt')
