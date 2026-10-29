#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 60 -A "$UA" "https://www.volleyleague.gr/index.php/season/2026-27/regular-season-results-statistics" -o /tmp/v.html
grep -oE 'href="[^"]*season/2026-27/[^"]*"' /tmp/v.html | sort -u | head -30
grep -oE '<h3>[^<]*</h3>' /tmp/v.html | head -40
grep -oiE '.{0,300}(ΠΑΝΑΘΗΝΑΪΚΟΣ|Παναθηναϊκός).{0,100}' /tmp/v.html | grep -i "paok\|παοκ" | head -3
