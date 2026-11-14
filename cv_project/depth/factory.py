"""Register future per-object stereo algorithms at this one boundary."""
from cv_project.depth.stereo import StereoEstimator

BACKENDS = {'sgbm': StereoEstimator}


def create_depth_estimator(backend, left, right, transform, **options):
    try:
        factory = BACKENDS[backend]
    except KeyError as error:
        raise ValueError(f'Unknown depth backend: {backend}') from error
    return factory(left, right, transform, **options)
