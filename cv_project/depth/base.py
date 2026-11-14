"""A depth backend works on stereo pixels and detector ROIs, not object sizes."""
from typing import Protocol


class DepthEstimator(Protocol):
    baseline: float
    fx: float
    num_disparities: int
    person_from_optical: object
    def compute(self, left_image, right_image): ...
    def localize(self, frame, detection): ...
