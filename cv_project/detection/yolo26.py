"""Ultralytics YOLO26 adapter. Model import and weight loading are explicit."""
from cv_project.config import resolve_path
from cv_project.contracts import Detection


class YOLO26Detector:
    def __init__(self, weights, confidence=.35, image_size=640, device=None, class_map=None, model=None):
        self.confidence = float(confidence)
        self.image_size = int(image_size)
        self.device = device
        self.class_map = class_map or {}
        if model is None:
            weights = resolve_path(weights)
            if not weights.is_file():
                raise FileNotFoundError(f'Model weights not found: {weights}. Run scripts/download_models.py or supply custom weights.')
            try:
                from ultralytics import YOLO
            except ImportError as error:
                raise RuntimeError('Install the yolo extra: python -m pip install -e ".[yolo]"') from error
            model = YOLO(str(weights))
        self.model = model

    def detect(self, image_bgr):
        options = {'source': image_bgr, 'conf': self.confidence, 'imgsz': self.image_size, 'verbose': False}
        if self.device is not None:
            options['device'] = self.device
        result = self.model.predict(**options)[0]
        if result.boxes is None:
            return []
        xyxy = result.boxes.xyxy.cpu().tolist()
        scores = result.boxes.conf.cpu().tolist()
        classes = result.boxes.cls.cpu().tolist()
        detections = []
        for box, score, index in zip(xyxy, scores, classes):
            name = str(result.names[int(index)])
            name = self.class_map.get(name, name)
            # No tracking ID is invented; consumers can use the class as a speech key.
            detections.append(Detection(name, tuple(box), float(score), None))
        return detections
