#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
for id in $(seq 1 60); do
  t=$(curl -sSL -m 20 -A "$UA" "https://www.epo.gr/el/competition/$id/matches" | grep -oE '<title>[^<]*' | head -1)
  case "$t" in *[Ff]utsal*|*[Σσ]άλας*|*ΣΑΛΑΣ*|*αλας*) echo "$id $t";; esac
done
curl -sSL -m 30 -A "$UA" "https://www.epo.gr/el/competitions" | grep -oiE 'href="[^"]*competition/[0-9]+[^"]*"[^>]*>[^<]*' | grep -i "σάλας\|futsal\|ΣΑΛΑΣ" | head
