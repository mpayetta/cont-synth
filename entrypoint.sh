#!/bin/bash
set -e

echo "Running database migrations..."
reflex db migrate

echo "Starting app (API_URL=${API_URL:-http://localhost:8000})..."
exec reflex run --env prod --loglevel warning
