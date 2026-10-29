#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
curl -sSL -m 40 "https://ea.microplustimingservices.com/EAWPClubs2027/assets/api_config.json" | head -c 1500; echo
curl -sSL -m 60 "https://ea.microplustimingservices.com/EAWPClubs2027/main.js" -o /tmp/main.js
echo "== wsLogin"; grep -oE "wsLogin\(e=!1\).{0,1500}" /tmp/main.js | head -2
grep -oE ".{0,300}getWSSiteTokenUrl\(\).{0,600}" /tmp/main.js | head -3
