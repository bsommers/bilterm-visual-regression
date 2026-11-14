#!/usr/bin/env bash
# Render real bilterm frames headlessly and refresh fixtures/real/.
# Does not modify bilterm: cargo builds into a temp target dir.
#
#   BILTERM_DIR=/path/to/bilterm scripts/capture_frames.sh
set -euo pipefail
cd "$(dirname "$0")/.."

BILTERM_DIR="${BILTERM_DIR:-$HOME/src/tools/bilterm}"
[ -f "$BILTERM_DIR/examples/design_preview.rs" ] || {
  echo "bilterm checkout not found at $BILTERM_DIR (set BILTERM_DIR)" >&2; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

COMMIT="$(git -C "$BILTERM_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "Rendering frames from bilterm @ $COMMIT ..."
( cd "$BILTERM_DIR" && CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$WORK/target}" \
    cargo run -q --example design_preview -- "$WORK/ppm" )

PYTHONPATH=src python3 -m bilterm_vr.capture --ppm-dir "$WORK/ppm" --out fixtures/real --bilterm-commit "$COMMIT"
