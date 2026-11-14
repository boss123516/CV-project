"""Repository-relative configuration; independent of a developer's home directory."""
from copy import deepcopy
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get('CV_PROJECT_ROOT', Path(__file__).resolve().parents[1])).resolve()


def resolve_path(value):
    path = Path(os.path.expandvars(str(value))).expanduser()
    return path if path.is_absolute() else ROOT / path


def read_json(value):
    with resolve_path(value).open(encoding='utf-8') as stream:
        return json.load(stream)


def pipeline_config(path=None):
    config = read_json(path or os.environ.get('CV_PROJECT_CONFIG', 'config/pipelines/baseline.json'))
    if config.get('detector', {}).get('backend') not in {'simulator', 'yolo26'}:
        raise ValueError('detector.backend must be simulator or yolo26')
    from cv_project.depth.factory import BACKENDS
    if config.get('depth', {}).get('backend') not in BACKENDS:
        raise ValueError('Unknown depth backend; register it in cv_project.depth.factory')
    return config


def scenario_config(identifier=None):
    identifier = identifier or os.environ.get('CV_SCENARIO', 'urban_baseline')
    if not identifier or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in identifier):
        raise ValueError('Scenario ID must contain lowercase letters, digits, _ or -')
    manifest = read_json(f'scenarios/{identifier}/scenario.json')
    if manifest['id'] != identifier:
        raise ValueError('Scenario directory and manifest ID differ')
    scene = deepcopy(read_json(manifest['scene']))
    scene['route_start_m'] = manifest['route']['start_m']
    scene['route_end_m'] = manifest['route']['end_m']
    scene['cruise_speed_mps'] = manifest['route']['cruise_speed_mps']
    if not 0 <= scene['route_start_m'] < scene['route_end_m'] <= scene['path_xy'][-1][0]:
        raise ValueError('Scenario route lies outside the shared world')
    scene['manifest'] = manifest
    return scene


def runtime_dir():
    path = resolve_path(os.environ.get('CV_RUN_DIR', 'webots/logs'))
    path.mkdir(parents=True, exist_ok=True)
    return path
