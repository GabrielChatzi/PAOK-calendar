#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
U="https://www.handball.org.gr/media/yootheme/cache/2a/PAOK-01-2a789158.jpg"
echo "== no referer"; curl -sS -o /dev/null -D - -A "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)" "$U" | grep -iE "^HTTP|content-type|cross-origin|content-length|location|x-frame|cf-"
echo "== with referer"; curl -sS -o /dev/null -D - -e "https://paokalendar.vercel.app/" -A "Mozilla/5.0" "$U" | grep -iE "^HTTP|content-type|cross-origin|content-length"
