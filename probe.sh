#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0"
B=https://ea.microplustimingservices.com/EAWPClubs2027
curl -sSL -A "$UA" "$B/main.js" -o /tmp/x.js
grep -oE '.{0,120}api/wp.{0,200}' /tmp/x.js | head -10
echo ----
grep -oE '.{0,100}(/get/|"get"|\+"/"\+).{0,160}' /tmp/x.js | head -40
echo ----
grep -oE '.{0,150}"mpbp".{0,150}' /tmp/x.js | head -5
echo ----
grep -oE '.{0,150}"results".{0,150}' /tmp/x.js | head -5
echo ----
grep -oE '.{0,150}"live".{0,150}' /tmp/x.js | head -5
