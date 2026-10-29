#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
B=https://ea.microplustimingservices.com/EAWPClubs2027
cat docs/crs.js 2>/dev/null; curl -sSL -m 40 "$B/crs-results.js"; echo
curl -sSL -m 40 "$B/" -o /tmp/idx.html
grep -oE 'src="[^"]+\.js"' /tmp/idx.html
for js in $(grep -oE 'src="[^"]+\.js"' /tmp/idx.html | sed 's/src="//;s/"//'); do
  curl -sSL -m 60 "$B/$js" -o /tmp/main.js; echo "== $js $(wc -c </tmp/main.js)"
  grep -oE '"[^"]{0,80}(\.json|export/|/data/|\.php|api/)[^"]{0,60}"' /tmp/main.js | sort -u | head -40
  grep -oE '`[^`]{0,120}(\.json|export/|\.php)[^`]{0,60}`' /tmp/main.js | sort -u | head -40
done
