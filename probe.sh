#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
echo "== api_config"; curl -sS -m 30 -A "$UA" "https://live.koe.org.gr/waterpolo/api_config.json"; echo
curl -sS -m 30 -A "$UA" "https://live.koe.org.gr/waterpolo/main.4211092d4684fb4c.js" -o /tmp/j.js
echo "== get/ strings"; grep -oE '.{0,60}/get/.{0,120}' /tmp/j.js | head -60
echo "== token"; grep -oE '.{0,100}token.{0,100}' /tmp/j.js | grep -i "site\|bearer" | head -10
echo "== match-details"; grep -oE '.{0,200}match-details.{0,200}' /tmp/j.js | head -5
