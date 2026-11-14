#!/usr/bin/env bash
set -e
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_DIR/../scripts/env.sh"
if [[ -z "${WEBOTS_BIN:-}" ]]; then
  if command -v webots >/dev/null; then WEBOTS_BIN="$(command -v webots)"
  elif [[ -n "${WEBOTS_HOME:-}" && -x "$WEBOTS_HOME/webots" ]]; then WEBOTS_BIN="$WEBOTS_HOME/webots"
  else WEBOTS_BIN="$HOME/.ros/webotsR2025a/webots/webots"; fi
fi
if [[ ! -x "$WEBOTS_BIN" ]]; then echo 'Webots not found. Set WEBOTS_BIN or WEBOTS_HOME.' >&2; exit 1; fi
export PYTHON_COMMAND="$CV_PYTHON"
export WEBOTS_PYTHON_COMMAND="$CV_PYTHON"
WORLD_PATH="$("$CV_PYTHON" -m cv_project world --scenario "$CV_SCENARIO")"
exec "$WEBOTS_BIN" --port="${WEBOTS_PORT:-1241}" --mode="${CV_WEBOTS_MODE:-realtime}" --stdout --stderr "$@" "$WORLD_PATH"
