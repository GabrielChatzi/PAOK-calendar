#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
for u in "https://www.slgr.gr/el/schedule/" "https://www.slgr.gr/el/" "https://www.paokfc.gr/fixtures/" "https://www.paokfc.gr/" "https://www.superleaguegreece.net/"; do
  code=$(curl -sSL -A "$UA" -o /tmp/p.html -w "%{http_code}" "$u"); echo "== $u $code $(wc -c </tmp/p.html)"
  grep -oiE '.{0,120}(cosmote|nova|ert ?sports|ΕΡΤ|mega|ant1|skai|tv ?channel|broadcaster|μετάδοση).{0,120}' /tmp/p.html | head -6
done
