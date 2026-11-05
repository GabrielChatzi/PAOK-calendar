#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
for u in https://paokalendar.gr/ https://www.paokalendar.gr/ https://paokalendar.gr/api/health; do echo "$u -> $(curl -sS -o /dev/null -m 20 -w '%{http_code} -> %{redirect_url}' "$u")"; done
