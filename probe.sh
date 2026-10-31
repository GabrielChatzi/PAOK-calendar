#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
for site in https://live.koe.org.gr/waterpolo/ https://ea.microplustimingservices.com/; do
  echo "=== $site"
  curl -sS -m 30 -A "$UA" "$site" -o /tmp/s.html; head -c 1500 /tmp/s.html; echo
  for js in $(grep -oE '(src|href)=["'"'"']?[^"'"'"' >]+\.js' /tmp/s.html | sed -E 's/^(src|href)=["'"'"']?//' | head -10); do
    case "$js" in http*) u=$js;; /*) u=$(echo $site | grep -oE 'https://[^/]+')$js;; *) u=$site$js;; esac
    echo "--- $u"
    curl -sS -m 30 -A "$UA" "$u" -o /tmp/j.js; wc -c < /tmp/j.js
    grep -oE '"[^"]{0,40}(api|/get/)[^"]{0,80}"' /tmp/j.js | sort -u | head -40
    grep -oE '/get/[A-Za-z_]+' /tmp/j.js | sort -u | head -40
  done
done
