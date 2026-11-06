#!/usr/bin/env bash
set -e
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
for component in voice viewer sim; do
  pid_file="$PROJECT_DIR/logs/$component.pid"
  if [[ -f "$pid_file" ]]; then
    demo_pid="$(cat "$pid_file")"
    if kill -0 "$demo_pid" 2>/dev/null && [[ "$(ps -p "$demo_pid" -o args=)" == *"$PROJECT_DIR"* ]]; then
      demo_group="$(ps -p "$demo_pid" -o pgid= | tr -d " ")"
      if [[ "$demo_group" == "$demo_pid" ]]; then
        kill -TERM -- "-$demo_pid"
      else
        kill -TERM "$demo_pid"
      fi
      echo "Stopped $component (PID $demo_pid)"
    fi
    rm -f "$pid_file"
  fi
done
