#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test "$(uname -s)" = Darwin || { echo "Build this package on macOS."; exit 1; }
python3 -m venv .build-venv
.build-venv/bin/python -m pip install -e '.[dev]'
.build-venv/bin/python scripts/build_sidecar.py
target="$(rustc -vV | sed -n 's/^host: //p')"
.build-venv/bin/python scripts/smoke_sidecar.py "desktop/src-tauri/binaries/tripod-backend-$target"
if test -f frontend/package-lock.json; then npm --prefix frontend ci; else npm --prefix frontend install; fi
npm --prefix frontend test
npm --prefix frontend run build
cd desktop/src-tauri
npx --yes @tauri-apps/cli@2.12.4 build --locked
