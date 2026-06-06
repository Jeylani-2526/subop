#!/usr/bin/env bash
# =============================================================================
# SUBOP — First-Time Development Environment Setup
# Run once after cloning the repository.
# =============================================================================

set -euo pipefail

echo "=== SUBOP Dev Environment Setup ==="

# 1. Check prerequisites
echo "[1/4] Checking prerequisites..."
command -v docker  >/dev/null 2>&1 || { echo "ERROR: Docker is not installed."; exit 1; }
command -v git     >/dev/null 2>&1 || { echo "ERROR: Git is not installed.";    exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: Python 3 is not installed."; exit 1; }
echo "      Prerequisites OK."

# 2. Copy .env if it doesn't exist
echo "[2/4] Setting up .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "      .env created from .env.example."
  echo "      Edit .env if you need custom passwords or ports."
else
  echo "      .env already exists — skipping."
fi

# 3. Start core services (M1-M2 set)
echo "[3/4] Starting core services (postgres, pgadmin, zookeeper, kafka, kafka-ui)..."
docker compose up -d postgres pgadmin zookeeper kafka kafka-ui
echo "      Waiting 15 seconds for services to be healthy..."
sleep 15

# 4. Verify services
echo "[4/4] Verifying services..."
docker compose ps

echo ""
echo "=== Setup Complete ==="
echo ""
echo "  PostgreSQL  : localhost:5432"
echo "  pgAdmin     : http://localhost:5050  (login: admin@subop.local / admin_dev)"
echo "  Kafka UI    : http://localhost:8080"
echo ""
echo "  Run 'docker compose logs -f' to follow service logs."
echo "  Run 'docker compose down' to stop all services."
