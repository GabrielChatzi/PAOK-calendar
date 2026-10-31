#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
curl -sS -m 30 -A "$UA" "https://live.koe.org.gr/waterpolo/main.4211092d4684fb4c.js" -o /tmp/j.js
echo "== json files"; grep -oE '"[^"]{0,60}\.json[^"]{0,20}"' /tmp/j.js | sort -u | head
echo "== x-wp-token ctx"; grep -oE '.{0,700}nomeHeader\(\)\{return"x-wp-token"\}.{0,900}' /tmp/j.js | head -3
echo "== competitionCode"; grep -oE '.{0,200}competitionCode=.{0,200}' /tmp/j.js | head -4
for f in assets/config.json assets/apiconfig.json config.json apiconfig.json assets/config/config.json; do echo "-- $f"; curl -sS -m 20 -A "$UA" "https://live.koe.org.gr/waterpolo/$f" | head -c 400; echo; done
