#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
sleep 40
for i in 1 2 3 4 5 6 7 8; do
  if curl -sS "https://paokalendar.vercel.app/" | grep -q 'function matchHtml'; then echo "LIVE: match page deployed"; exit 0; fi
  sleep 20
done
echo "NOT YET"
