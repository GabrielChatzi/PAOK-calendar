#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0"
for site in https://ea.microplustimingservices.com https://live.koe.org.gr; do
  echo "##### $site"
  curl -sSL -A "$UA" "$site/" -o /tmp/h.html; echo "html bytes $(wc -c < /tmp/h.html)"; head -c 1500 /tmp/h.html; echo
  for js in $(grep -oE '(src|href)="[^"]+\.js[^"]*"' /tmp/h.html | sed -E 's/^(src|href)="//; s/"$//'); do
    case "$js" in http*) u=$js;; /*) u=$site$js;; *) u=$site/$js;; esac
    echo "-- $u"; curl -sSL -A "$UA" "$u" | grep -oE '"/?get/[A-Za-z]+[^"]{0,60}"|`[^`]{0,40}/get/[A-Za-z]+[^`]{0,80}`|get/[A-Za-z]{4,}' | sort -u | head -40
  done
done
EA=https://ea.microplustimingservices.com/api/wp
T=$(curl -sS -A "$UA" "$EA/site/token" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")
for path in "EA27/get/resultsDBlikeJSON/ASF/2/001/3/URA/PAOK" "EACLUB27/get/resultsDBlikeJSON/ASF/2/001/3/URA/PAOK/" ; do
  echo "== $path"; curl -sS -A "$UA" -H "Authorization: Bearer $T" -w " [%{http_code}]" "$EA/$path" | head -c 600; echo
done
