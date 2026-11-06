#!/usr/bin/env bash
set -e
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-71}"
export PYTHONPATH="$PROJECT_DIR/..${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 "$PROJECT_DIR/../perception/ros_node.py"
