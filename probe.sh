#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
sleep 30
for i in 1 2 3 4 5 6; do
  page=$(curl -sS "https://paokalendar.vercel.app/")
  data=$(curl -sS "https://paokalendar.vercel.app/matches.json")
  if echo "$page" | grep -q 'data-bell' && echo "$data" | grep -q '"nt"'; then echo "LIVE: new page and data"; exit 0; fi
  sleep 20
done
echo "NOT YET"
