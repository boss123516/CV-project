#!/usr/bin/env bash
set -e
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_DIR/../scripts/env.sh"
export QT_QPA_FONTDIR="${QT_QPA_FONTDIR:-/usr/share/fonts/truetype/dejavu}"
exec "$CV_PYTHON" "$PROJECT_DIR/scripts/stereo_viewer.py"
