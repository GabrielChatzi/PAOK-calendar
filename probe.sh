#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0"
curl -sSL -A "$UA" "https://europeanaquatics.org/sports/water-polo/club-competitions/schedule/" -o /tmp/e.html
grep -oiE '.{0,100}(api/wp|EACLUB|ea\.microplus|iframe).{0,200}' /tmp/e.html | grep -v menu-item | head -20
for js in $(grep -oE 'src="[^"]+\.js[^"]*"' /tmp/e.html | sed -E 's/^src="//; s/"$//' | grep -iE 'wp-content/(plugins|themes)/[^/]*(ea|aqua|micro|schedule|live|wp)' ); do
  echo "-- $js"; curl -sSL -A "$UA" "$js" | grep -oE '.{0,80}(api/wp|/get/|token).{0,160}' | head -30
done
echo; grep -oE 'src="[^"]+\.js[^"]*"' /tmp/e.html | head -60
