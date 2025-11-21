#!/bin/bash
# Docker Stop Script (Linux/macOS)
# This script ensures all containers and networks are properly stopped and removed

set -e

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "[WARN] Docker is not available."
    echo "This is OK if you just want to clean up stopped containers."
fi

# Check if .env exists to determine if frontend is enabled
ENABLE_FRONTEND=false
if [ -f .env ]; then
    if grep -q "FRONTEND_PROFILE=frontend" .env 2>/dev/null; then
        ENABLE_FRONTEND=true
    elif ! grep -q 'FRONTEND_PROFILE=""' .env 2>/dev/null; then
        if grep -q "FRONTEND_PROFILE=" .env 2>/dev/null; then
            ENABLE_FRONTEND=true
        fi
    fi
fi

echo "[INFO] Stopping WaveEnv services..."
echo

# Stop all containers (with profile if frontend was enabled)
if [ "$ENABLE_FRONTEND" = "true" ]; then
    echo "[INFO] Stopping services with frontend profile..."
    docker-compose --profile frontend stop 2>/dev/null || true
    docker-compose --profile frontend rm -f 2>/dev/null || true
else
    echo "[INFO] Stopping backend service only..."
    docker-compose stop 2>/dev/null || true
    docker-compose rm -f 2>/dev/null || true
fi

# Force remove any remaining containers by name
echo "[INFO] Cleaning up any remaining containers..."
docker stop waveenv-backend waveenv-frontend 2>/dev/null || true
docker rm -f waveenv-backend waveenv-frontend 2>/dev/null || true

# Remove network if it exists
echo "[INFO] Removing network..."
if [ "$ENABLE_FRONTEND" = "true" ]; then
    docker-compose --profile frontend down 2>/dev/null || true
else
    docker-compose down 2>/dev/null || true
fi

# Force remove network if it still exists
docker network rm waveenv_waveenv-network 2>/dev/null || true

# Verify cleanup
echo "[INFO] Verifying cleanup..."
REMAINING_CONTAINERS=$(docker ps -a --filter name=waveenv --format "{{.Names}}" 2>/dev/null || echo "")
if [ -z "$REMAINING_CONTAINERS" ]; then
    echo "[INFO] All containers removed successfully."
else
    echo "[WARN] Some containers may still exist. Trying to remove..."
    echo "$REMAINING_CONTAINERS" | while read -r container; do
        [ -n "$container" ] && docker rm -f "$container" 2>/dev/null || true
    done
fi

REMAINING_NETWORKS=$(docker network ls --filter name=waveenv --format "{{.Name}}" 2>/dev/null || echo "")
if [ -z "$REMAINING_NETWORKS" ]; then
    echo "[INFO] Network removed successfully."
else
    echo "[WARN] Network may still exist."
fi

echo
echo "[INFO] Cleanup complete!"
echo

