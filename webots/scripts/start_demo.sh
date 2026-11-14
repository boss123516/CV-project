#!/usr/bin/env bash
set -e
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_DIR/../scripts/env.sh"
for component in ${CV_COMPONENTS:-sim detector perception viewer voice}; do
  pid_file="$CV_RUN_DIR/$component.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null && [[ "$(ps -p "$(cat "$pid_file")" -o stat=)" != Z* ]] && [[ "$(ps -p "$(cat "$pid_file")" -o args=)" == *"$CV_PROJECT_ROOT"* ]]; then
    echo "$component already running"
    continue
  fi
  nohup setsid "$PROJECT_DIR/scripts/run_$component.sh" > "$CV_RUN_DIR/$component.log" 2>&1 < /dev/null &
  echo "$!" > "$pid_file"
  echo "Started $component (PID $!)"
done
