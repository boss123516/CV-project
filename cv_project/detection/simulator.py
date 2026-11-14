"""Reproducible demo detector: simulator labels/boxes only, never geometry."""
from cv_project.contracts import Detection, detection_packet


def convert_simulator_packet(packet):
    detections = []
    for obj in packet['objects']:
        x, y = obj['center_px']; width, height = obj['size_px']
        if width <= 0 or height <= 0:
            continue
        detections.append(Detection(obj['class'], (x-width/2, y-height/2, x+width/2, y+height/2),
                                    1.0, obj['id']))
    return detection_packet(round(packet['simulation_time'] * 1e9), detections,
                            'webots_box_adapter_NOT_yolo')
