"""A detector consumes a rectified BGR image and returns image-space detections."""
from typing import Protocol, Sequence
import numpy as np
from cv_project.contracts import Detection


class Detector(Protocol):
    def detect(self, image_bgr: np.ndarray) -> Sequence[Detection]: ...
