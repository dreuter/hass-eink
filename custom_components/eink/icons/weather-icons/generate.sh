#!/bin/bash
# Regenerate weather condition PNGs from the upstream weather-icons repo.
# Requires: librsvg2-bin (apt install librsvg2-bin)
# Source:   https://github.com/Makin-Things/weather-icons (MIT License)
#           Copyright (c) 2019 Custom cards for Home Assistant
set -e

REPO=$(mktemp -d)
git clone --depth 1 https://github.com/Makin-Things/weather-icons "$REPO"
SRC="$REPO/static"
DST="$(dirname "$0")"

declare -A ICONS=(
  [clear-night]="clear-night"
  [cloudy]="cloudy"
  [exceptional]="severe-thunderstorm"
  [fog]="fog"
  [hail]="hail"
  [lightning]="thunderstorms"
  [lightning-rainy]="scattered-thunderstorms"
  [partlycloudy]="cloudy-1-day"
  [pouring]="rainy-3"
  [rainy]="rainy-1"
  [snowy]="snowy-1"
  [snowy-rainy]="rain-and-snow-mix"
  [sunny]="clear-day"
  [windy]="wind"
  [windy-variant]="wind"
)

for condition in "${!ICONS[@]}"; do
  rsvg-convert -w 128 -h 128 "$SRC/${ICONS[$condition]}.svg" -o "$DST/${condition}.png"
  echo "✓ $condition"
done

rm -rf "$REPO"
