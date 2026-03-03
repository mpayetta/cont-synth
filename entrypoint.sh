#!/bin/bash
set -e

export PYTHONWARNINGS="ignore::DeprecationWarning"

echo "Running database migrations..."
reflex db migrate

# Patch react-router.config.ts to disable SSR prerendering.
# Reflex generates this file with prerender:true, which causes vaul to crash
# with "document is not defined" during the static build step.
# This watcher patches it before the npm build starts.
(
  CONFIG_FILE="/app/.web/react-router.config.ts"
  until [ -f "$CONFIG_FILE" ]; do sleep 0.2; done
  sed -i -E 's/prerender:[[:space:]]*true/prerender: false/g' "$CONFIG_FILE"
  echo "[patch] Disabled SSR prerendering in react-router.config.ts"
) &

echo "Starting app (API_URL=${API_URL:-http://localhost:8000})..."
exec reflex run --env prod --loglevel warning
