#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
B=https://ea.microplustimingservices.com/EAWPClubs2027
echo "== api_config"; curl -sSL -m 40 "$B/api_config.json"; echo
echo "== runtime"; curl -sSL -m 40 "$B/assets/runtime-config.json"; echo
echo "== sports_config"; curl -sSL -m 40 "$B/sports_config.json" | head -c 1500; echo
