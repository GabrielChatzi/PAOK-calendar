#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
G=https://gabrielchatzi.github.io/PAOK-calendar
for u in "$G/matches.json" "https://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/data/matches.json"; do
  curl -sS "$u?t=$(date +%s)" | python3 -c "import json,sys; d=json.load(sys.stdin); print(max(d['updated'].values()), len(d['matches']))"
done
curl -sS -o /dev/null -w "ics %{http_code}\n" "$G/football-home.ics"; curl -sS -o /dev/null -w "index %{http_code}\n" "$G/"
