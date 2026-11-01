#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0"
B=https://ea.microplustimingservices.com/EAWPClubs2027
curl -sSL -A "$UA" $B/crs-results.js; echo
for f in $(curl -sSL -A "$UA" $B/crs-results.js | grep -oE '[a-zA-Z0-9._-]+\.js' | sort -u) main.js; do
  echo "-- $f"; curl -sSL -A "$UA" "$B/$f" -o /tmp/x.js; wc -c < /tmp/x.js
  grep -oE '.{0,60}/get/.{0,140}' /tmp/x.js | head -40
  grep -oE '[A-Za-z]{3,}DBlikeJSON|"[a-zA-Z]*(results|Results|live|pbp|summary)[a-zA-Z]*"' /tmp/x.js | sort -u | head -40
done
