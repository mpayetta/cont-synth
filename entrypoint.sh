#!/bin/bash
set -e

export PYTHONWARNINGS="ignore::DeprecationWarning"

echo "Running database migrations..."
alembic upgrade head

# Fix: vaul 1.1.2 calls document.body.style.backgroundColor inside a useMemo
# which runs during React Router SSR prerendering → "document is not defined".
# Patch: wrap with typeof guard to make it SSR-safe.
VAUL_FILE="/app/.web/node_modules/vaul/dist/index.mjs"
VAUL_BUG='useMemo(()=>document\.body\.style\.backgroundColor, \[\])'
VAUL_FIX='useMemo(()=>typeof document!=="undefined"?document.body.style.backgroundColor:"", [])'

patch_vaul() {
  if [ -f "$VAUL_FILE" ] && grep -q 'useMemo(()=>document\.body' "$VAUL_FILE" 2>/dev/null; then
    sed -i "s|$VAUL_BUG|$VAUL_FIX|g" "$VAUL_FILE"
    echo "[patch] Applied SSR guard to vaul"
  fi
}

# Patch immediately (handles cached .web volume from previous runs)
patch_vaul

# Also re-apply after npm/bun reinstalls vaul (handles wiped volumes)
(
  until [ -f "$VAUL_FILE" ]; do sleep 1; done
  sleep 2  # buffer for npm to finish writing the file
  patch_vaul
) &

echo "Starting app (API_URL=${API_URL:-http://localhost:8000})..."
exec reflex run --env prod --loglevel warning
