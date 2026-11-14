#!/usr/bin/env bash
# Source this file from any directory. No developer-specific paths are required.
CV_PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export CV_PROJECT_ROOT
ROS_SETUP="${ROS_SETUP:-/opt/ros/${ROS_DISTRO:-humble}/setup.bash}"
if [[ -f "$ROS_SETUP" ]]; then source "$ROS_SETUP"; fi
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-71}"
export PYTHONPATH="$CV_PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
if [[ -z "${CV_PYTHON:-}" ]]; then
  if [[ -x "$CV_PROJECT_ROOT/.venv/bin/python" ]]; then CV_PYTHON="$CV_PROJECT_ROOT/.venv/bin/python"; else CV_PYTHON=/usr/bin/python3; fi
fi
export CV_PYTHON
export CV_SCENARIO="${CV_SCENARIO:-urban_baseline}"
export CV_PROJECT_CONFIG="${CV_PROJECT_CONFIG:-$CV_PROJECT_ROOT/config/pipelines/baseline.json}"
export CV_RUN_DIR="${CV_RUN_DIR:-$CV_PROJECT_ROOT/webots/logs}"
[[ "$CV_RUN_DIR" == /* ]] || CV_RUN_DIR="$CV_PROJECT_ROOT/$CV_RUN_DIR"
export CV_RUN_DIR
mkdir -p "$CV_RUN_DIR"
