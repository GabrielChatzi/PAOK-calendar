#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
for sub in ehfcl ehfel ehfec; do for g in men women; do
  c=$(curl -sSL -m 40 -A "$UA" "https://$sub.eurohandball.com/$g/2026-27/clubs/" | grep -oi "a\.c\. paok\|paok" | head -1)
  echo "$sub $g clubs PAOK: [$c]"
done; done
curl -sSL -m 40 -A "$UA" "https://www.cev.eu/club/cev-volleyball-cup/2027/men/" -o /tmp/c.html
grep -oE 'href="[^"]*2027[^"]*"' /tmp/c.html | sort -u | head -30
grep -oiE '.{0,200}(round of 32|main-round|16th|matches).{0,200}' /tmp/c.html | head -10 | cut -c1-400
