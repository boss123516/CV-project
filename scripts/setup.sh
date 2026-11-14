#!/usr/bin/env bash
set -e
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
/usr/bin/python3 -m venv --system-site-packages "$PROJECT_ROOT/.venv"
"$PROJECT_ROOT/.venv/bin/python" -m pip install -e "$PROJECT_ROOT"
if [[ "${1:-}" == '--yolo' ]]; then "$PROJECT_ROOT/.venv/bin/python" -m pip install -e "$PROJECT_ROOT[yolo]"; fi
printf '%s\n' 'Setup complete. ROS 2 and Webots are system dependencies; see docs/SETUP.md.'
