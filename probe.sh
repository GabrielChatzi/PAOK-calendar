#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0"
for u in http://statistics.handball.org.gr/gr/sportevents.asp http://statistics.handball.org.gr/ https://www.handball.org.gr/; do
  echo "== $u"; curl -sSL -m 30 -A "$UA" "$u" | grep -oiE '.{0,80}(live|ζωντ|genius|livestats|dataproject|swiss|hbstats|scoreboard).{0,120}' | head -8
done
