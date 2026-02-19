#!/usr/bin/env bash
set -euo pipefail

HEALTH_ROOT="/Users/jimmylu/.openclaw/workspace-health"
SAFE_ROOT="/Users/jimmylu/.openclaw/workspace/shared/health-reports"
SRC_DIR="$HEALTH_ROOT/memory/health-daily"

mkdir -p "$SAFE_ROOT"

src="${1:-}"
if [[ -z "$src" ]]; then
  src="$(ls -t "$SRC_DIR"/*.md 2>/dev/null | head -n 1 || true)"
fi

if [[ -z "$src" || ! -f "$src" ]]; then
  echo "No report found. Provide a file path or ensure $SRC_DIR has markdown reports." >&2
  exit 1
fi

base="$(basename "$src")"
dst="$SAFE_ROOT/$base"
cp "$src" "$dst"

# Keep a stable pointer for easy send
ln -sfn "$dst" "$SAFE_ROOT/latest.md"

echo "Published: $dst"
echo "Latest link: $SAFE_ROOT/latest.md"
