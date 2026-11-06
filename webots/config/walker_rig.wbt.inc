DEF WALKER Pedestrian {
  translation 0 0 1.27 name "assistive_walker"
  controller "assistive_walker" controllerArgs [ "--assistive" ]
  shirtColor 0.08 0.35 0.60 pantsColor 0.12 0.15 0.2
  bodySlot [
    Pose { translation 0.20 0 0.40 children [ Shape { appearance PBRAppearance { baseColor 0.035 0.05 0.07 roughness 0.5 metalness 0.2 } geometry Box { size 0.04 0.21 0.045 } } ] }
    DEF LEFT_CAMERA Camera {
      translation 0.235 0.06 0.40 rotation 0 1 0 0.12
      name "left_camera" width 640 height 480 fieldOfView 1.1344640138
      near 0.05 far 55 antiAliasing TRUE noise 0.002
      recognition Recognition { maxRange 7.5 maxObjects 8 occlusion 1 }
    }
    DEF RIGHT_CAMERA Camera {
      translation 0.235 -0.06 0.40 rotation 0 1 0 0.12
      name "right_camera" width 640 height 480 fieldOfView 1.1344640138
      near 0.05 far 55 antiAliasing TRUE noise 0.002
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
