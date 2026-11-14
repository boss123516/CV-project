#!/usr/bin/env bash
set -e
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_DIR/../scripts/env.sh"
for component in voice viewer perception detector sim; do
  pid_file="$CV_RUN_DIR/$component.pid"
  if [[ -f "$pid_file" ]]; then
    demo_pid="$(cat "$pid_file")"
    if kill -0 "$demo_pid" 2>/dev/null && [[ "$(ps -p "$demo_pid" -o args=)" == *"$CV_PROJECT_ROOT"* ]]; then
      demo_group="$(ps -p "$demo_pid" -o pgid= | tr -d " ")"
      if [[ "$demo_group" == "$demo_pid" ]]; then
        kill -TERM -- "-$demo_pid"
        for attempt in {1..40}; do
          kill -0 -- "-$demo_pid" 2>/dev/null || break
          sleep 0.05
        done
        # Webots may leave its GUI process alive after the launcher exits.
        # This group belongs to the verified project process above.
        if kill -0 -- "-$demo_pid" 2>/dev/null; then
          kill -KILL -- "-$demo_pid" 2>/dev/null || true
        fi
      else
        kill -TERM "$demo_pid"
      fi
      echo "Stopped $component (PID $demo_pid)"
    fi
    rm -f "$pid_file"
  fi
done
