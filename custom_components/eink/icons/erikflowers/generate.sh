#!/bin/bash
# Regenerate weather condition PNGs from the upstream weather-icons repo.
# Requires: librsvg2-bin (apt install librsvg2-bin)
# Source:   https://github.com/erikflowers/weather-icons (SIL OFL 1.1)
#           Copyright (c) Erik Flowers
set -e

REPO=$(mktemp -d)
git clone --depth 1 https://github.com/erikflowers/weather-icons "$REPO"
SRC="$REPO/svg"
DST="$(dirname "$0")"
declare -A ICONS=(
  [clear-night]="wi-night-clear"
  [cloudy]="wi-cloudy"
  [exceptional]="wi-meteor"
  [fog]="wi-fog"
  [hail]="wi-hail"
  [lightning]="wi-lightning"
  [lightning-rainy]="wi-thunderstorm"
  [partlycloudy]="wi-day-cloudy"
  [pouring]="wi-rain"
  [rainy]="wi-day-rain"
  [snowy]="wi-snow"
  [snowy-rainy]="wi-rain-mix"
  [sunny]="wi-day-sunny"
  [windy]="wi-day-windy"
  [windy-variant]="wi-cloudy-windy"
)

declare -A COLORS=(
  [clear-night]="yellow"
  [cloudy]="black"
  [exceptional]="red"
  [fog]="black"
  [hail]="blue"
  [lightning]="red"
  [lightning-rainy]="red"
  [partlycloudy]="yellow"
  [pouring]="blue"
  [rainy]="blue"
  [snowy]="blue"
  [snowy-rainy]="blue"
  [sunny]="yellow"
  [windy]="black"
  [windy-variant]="black"
)

TMPSVG=$(mktemp --suffix=.svg)

for condition in "${!ICONS[@]}"; do
  color="${COLORS[$condition]}"
  sed "s/<svg /<svg fill=\"$color\" /" "$SRC/${ICONS[$condition]}.svg" > "$TMPSVG"
  rsvg-convert -w 128 -h 128 "$TMPSVG" -o "$DST/${condition}.png"
  echo "✓ $condition ($color)"
done

rm -rf "$REPO" "$TMPSVG"
