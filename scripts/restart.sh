#!/bin/bash
# Restart Home Assistant.
# Requires .env with HA_TOKEN set.
set -e
source "$(dirname "$0")/../.env"

curl -s -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  http://localhost:8123/api/services/homeassistant/restart > /dev/null

echo "Restarting Home Assistant..."
