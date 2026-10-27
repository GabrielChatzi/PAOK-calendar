#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
sleep 60
for i in 1 2 3 4 5 6; do
  if curl -sS "https://paokalendar.vercel.app/" | grep -q 'href="#/app"'; then echo "LIVE: new version"; exit 0; fi
  sleep 20
done
echo "NOT YET: old version"
