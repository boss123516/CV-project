#!/usr/bin/env bash
set -e
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-71}"
export PYTHON_COMMAND=/usr/bin/python3
export WEBOTS_PYTHON_COMMAND=/usr/bin/python3
WEBOTS_BIN="${WEBOTS_BIN:-/home/boss/.ros/webotsR2025a/webots/webots}"
exec "$WEBOTS_BIN" --port=1241 --mode=realtime --stdout --stderr "$@" "$PROJECT_DIR/worlds/assistive_sidewalk.wbt"
