#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
for u in https://paokalendar.gr/ https://paokalendar.gr/api/health https://paokalendar.gr/matches.json https://www.paokalendar.gr/ https://paokalendar.gr/football-home.ics; do
  echo "$u -> $(curl -sS -o /dev/null -m 20 -w '%{http_code} %{content_type} %{redirect_url}' "$u")"; done
echo "MX: $(dig +short MX paokalendar.gr @8.8.8.8)"
