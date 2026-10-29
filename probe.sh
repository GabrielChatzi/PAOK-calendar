#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
for n in matches.min.js matches.js; do
curl -sSL -m 40 -A "$UA" "https://ehfel.eurohandball.com/frontend.kw/dist/assets/js/$n" -o /tmp/m.js; echo "== $n $(wc -c </tmp/m.js)"
grep -oE '.{0,300}(filterMatchesUrl|filter-matches-url|GetMatches|isPast|past|Past).{0,300}' /tmp/m.js | head -12
done
