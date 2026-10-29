#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
B=https://ea.microplustimingservices.com/EAWPClubs2027
curl -sSL -m 60 "$B/main.js" -o /tmp/main.js
for k in Bearer "Authorization" "/token" "getToken" "apiKey" "api_key" "x-api-key" "TOKEN"; do
  echo "== $k"; grep -oE ".{0,200}$k.{0,250}" /tmp/main.js | head -6
done
