#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 40 -A "$UA" "https://ehfel.eurohandball.com/women/2026-27/matches/" -o /tmp/p.html
grep -n 'competitionMatches' /tmp/p.html | head -3
L=$(grep -n 'ref="competitionMatches"' /tmp/p.html | head -1 | cut -d: -f1)
sed -n "$((L-15)),$((L+40))p" /tmp/p.html | cut -c1-300
grep -oE '"/frontend[^"]+\.js[^"]*"|/frontend[^" ]+\.js' /tmp/p.html | sort -u | head
