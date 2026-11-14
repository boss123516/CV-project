#!/usr/bin/env bash
set -e
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
exec "$CV_PYTHON" -m cv_project start "$@"
