#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
A=https://ea.microplustimingservices.com/EAWPClubs2027/assets
echo "== api_config"; curl -sSL -m 40 "$A/api_config.json"; echo
echo "== sports_config"; curl -sSL -m 40 "$A/sports_config.json" | head -c 2500; echo
