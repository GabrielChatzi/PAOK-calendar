#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
curl -sS -m 30 -A "$UA" "https://live.koe.org.gr/waterpolo/main.4211092d4684fb4c.js" -o /tmp/j.js
echo "== urls"; grep -oE 'https?://[A-Za-z0-9./_-]+' /tmp/j.js | sort -u | grep -v gdm2022 | head -40
echo "== schedule"; grep -oE '.{0,120}schedule/.{0,120}' /tmp/j.js | head -12
echo "== apiurl"; grep -oiE '.{0,80}(apiurl|baseurl|urlapi|api_url).{0,120}' /tmp/j.js | head -12
