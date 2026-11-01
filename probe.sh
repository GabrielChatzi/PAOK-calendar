#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
S=https://paokalendar.vercel.app
echo "GET: $(curl -sS $S/api/admin)"
echo "POST: $(curl -sS -X POST -H 'Content-Type: application/json' -d '{"password":"x","action":"check"}' $S/api/admin)"
