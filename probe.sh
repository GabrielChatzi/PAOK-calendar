#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0"
curl -sSL -A "$UA" https://ea.microplustimingservices.com/EAWPClubs2027/crs-results.js -o /tmp/c.js; wc -c /tmp/c.js
grep -oE '.{0,40}/get/.{0,120}' /tmp/c.js | head -60
echo ----; grep -oE '"get/[^"]*"|get/\$\{[^`]{0,100}|/get/"\s*\+[^;]{0,120}' /tmp/c.js | sort -u | head -60
echo ----; grep -oE '[A-Za-z]*(DBlike|results|Results|live|Live|pbp|PlayBy|summary|Summary)[A-Za-z]*JSON' /tmp/c.js | sort | uniq -c | head -40
echo ----; grep -oE 'https?://[^"`'"'"' ]+' /tmp/c.js | sort -u | head -30
