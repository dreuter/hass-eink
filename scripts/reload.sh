#!/bin/bash
# Reload the eink integration without restarting Home Assistant.
# Requires .env with HA_TOKEN set.
set -e
source "$(dirname "$0")/../.env"

ENTRY_ID=$(curl -s -H "Authorization: Bearer $HA_TOKEN" \
  http://localhost:8123/api/config/config_entries/entry \
  | python3 -c "import sys,json; entries=json.load(sys.stdin); print(next(e['entry_id'] for e in entries if e['domain']=='eink'))")

curl -s -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8123/api/services/homeassistant/reload_config_entry \
  -d "{\"entry_id\": \"$ENTRY_ID\"}" > /dev/null

echo "Reloaded eink (entry $ENTRY_ID)"
