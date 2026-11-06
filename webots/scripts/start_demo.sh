#!/usr/bin/env bash
set -e
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$PROJECT_DIR/logs"
for component in sim detector perception viewer voice; do
  pid_file="$PROJECT_DIR/logs/$component.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null && [[ "$(ps -p "$(cat "$pid_file")" -o stat=)" != Z* ]] && [[ "$(ps -p "$(cat "$pid_file")" -o args=)" == *"$PROJECT_DIR"* ]]; then
    echo "$component already running"
    continue
  fi
  nohup setsid "$PROJECT_DIR/scripts/run_$component.sh" > "$PROJECT_DIR/logs/$component.log" 2>&1 < /dev/null &
  echo "$!" > "$pid_file"
  echo "Started $component (PID $!)"
done
