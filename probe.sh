#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
curl -sS -m 30 -A "$UA" "https://live.koe.org.gr/waterpolo/main.4211092d4684fb4c.js" -o /tmp/j.js
grep -oE '.{0,250}https://live\.koe\.org\.gr/.{0,250}' /tmp/j.js | head -5
echo "== wp"; grep -oE '.{0,100}"/?(wp|api)/.{0,150}' /tmp/j.js | head -10
echo "== http.get"; grep -oE '.{0,40}\.get\([^)]{0,160}' /tmp/j.js | head -40
