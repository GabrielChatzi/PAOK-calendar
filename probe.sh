#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
node sr.mjs
echo "=== volleyleague.gr"
curl -sS -m 30 -A "Mozilla/5.0" https://www.volleyleague.gr/ | grep -oiE '.{0,60}(dataproject|livescore|live score|signalr).{0,100}' | head -10
