#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0"
B=https://ea.microplustimingservices.com/EAWPClubs2027
for p in assets/api_config.json assets/config/api_config.json api_config.json; do echo "== $p"; curl -sSL -A "$UA" -w " [%{http_code}]" "$B/$p" | head -c 4000; echo; done
