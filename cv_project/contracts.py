"""Detector/depth boundaries use capture timestamps and rectified-left pixels."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Detection:
    class_name: str
    bbox_xyxy: tuple
    confidence: float = 1.0
    object_id: object = None

    def as_dict(self):
        values = tuple(float(v) for v in self.bbox_xyxy)
        if len(values) != 4 or not all(math.isfinite(v) for v in values):
            raise ValueError('bbox must have four finite xyxy coordinates')
        if values[2] <= values[0] or values[3] <= values[1]:
            raise ValueError('bbox must have positive area')
        if not self.class_name or not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError('Invalid class name or confidence')
        return {'id': self.object_id, 'class': self.class_name, 'bbox_xyxy': list(values),
                'confidence': float(self.confidence)}


def detection_packet(stamp_ns, detections, source):
    if isinstance(stamp_ns, bool) or not isinstance(stamp_ns, int) or stamp_ns < 0:
        raise ValueError('stamp_ns must be the nonnegative image capture timestamp')
    return {'stamp_ns': stamp_ns, 'source': source, 'coordinate_space': 'rectified_left',
            'detections': [item.as_dict() for item in detections]}


def validate_detection_packet(packet):
    if packet.get('coordinate_space') != 'rectified_left':
        raise ValueError('Detections must use rectified-left image coordinates')
    if not isinstance(packet.get('stamp_ns'), int) or isinstance(packet['stamp_ns'], bool) or packet['stamp_ns'] < 0:
        raise ValueError('Invalid capture timestamp')
    clean = []
    for item in packet['detections']:
        # Drop every field beyond the detector contract, including simulator positions.
        clean.append(Detection(item['class'], tuple(item['bbox_xyxy']),
                               float(item.get('confidence', 1.0)), item.get('id')).as_dict())
    return dict(packet, detections=clean)
