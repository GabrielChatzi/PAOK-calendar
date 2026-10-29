#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 40 -A "$UA" "https://ehfel.eurohandball.com/women/2026-27/matches/" -o /tmp/p.html
grep -oE '<script[^>]*src="[^"]+"' /tmp/p.html | sed 's/.*src="//;s/"$//' | sort -u
for js in $(grep -oE '<script[^>]*src="[^"]+"' /tmp/p.html | sed 's/.*src="//;s/"$//' | grep -v '^//' | grep -v http); do
  curl -sSL -m 40 -A "$UA" "https://ehfel.eurohandball.com$js" -o /tmp/x.js
  if grep -q -i "competitionmatches" /tmp/x.js; then echo "== $js"; grep -oiE '.{0,150}competitionmatchesapi.{0,250}' /tmp/x.js | head -10; fi
done
grep -oiE '.{0,100}competitionmatches.{0,200}' /tmp/p.html | head -5
