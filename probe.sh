#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0"
curl -sSL -A "$UA" https://live.koe.org.gr/main.8a93d7754480c5a57ba3.js -o /tmp/k.js; wc -c /tmp/k.js
grep -oE '.{0,60}resultsDBlikeJSON.{0,120}' /tmp/k.js | head -5
echo ---; grep -oE '"/get/[^"]{0,80}"|/get/"|"get/[^"]{0,60}"|\+"/get/[a-zA-Z]+' /tmp/k.js | sort -u | head -60
echo ---; grep -oE '[a-zA-Z]+DBlikeJSON|get/[A-Za-z]+' /tmp/k.js | sort -u | head -80
echo --- ea refs; grep -oE '.{0,40}microplustimingservices.{0,80}' /tmp/k.js | head
curl -sSL -A "$UA" "https://europeanaquatics.org/sports/water-polo/club-competitions/schedule/" -o /tmp/e.html; wc -c /tmp/e.html
grep -oiE '.{0,80}(microplus|livescore|live-results|results\.).{0,120}' /tmp/e.html | head -20
