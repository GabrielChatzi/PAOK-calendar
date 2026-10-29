#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
B=https://ea.microplustimingservices.com/EAWPClubs2027
curl -sSL -m 40 -A "Mozilla/5.0" "$B/crs-results.js" -o docs/crs.js; wc -c docs/crs.js
grep -oE '"[^"]*(\.json|export|NU_|/api/|\.php)[^"]*"' docs/crs.js | sort -u | head -60
grep -oE "'[^']*(\.json|export|\.php)[^']*'" docs/crs.js | sort -u | head -40
curl -sS -m 30 -o /dev/null -w "index %{http_code}\n" "$B/"
curl -sSL -m 30 "$B/" | head -c 1500
