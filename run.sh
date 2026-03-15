#!/bin/bash
if [ -f .env ]; then
  echo "Loading environment variables from .env"
  # Export all variables from .env
  set -a
  source .env
  set +a
else
  echo ".env file not found. Please create one with ADMIN_USERNAME, ADMIN_PASSWORD, and SECRET_KEY."
  exit 1
fi

echo "Running with username: $ADMIN_USERNAME"
echo "Running with password: $ADMIN_PASSWORD"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
