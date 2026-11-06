#!/usr/bin/env bash
set -e
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-71}"
export QT_QPA_FONTDIR=/usr/share/fonts/truetype/dejavu
exec /usr/bin/python3 "$PROJECT_DIR/scripts/stereo_viewer.py"
