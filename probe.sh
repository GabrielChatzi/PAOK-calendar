#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
curl -sS -m 40 -w "  [%{http_code} %{time_total}s]" "https://paokalendar.vercel.app/api/live?src=gs&key=RFJIN037I07QV520B7WEXKV1GYNA31&day=2026-10-31&side=a"; echo
curl -sS -m 20 "https://paokalendar.vercel.app/matches.json" | python3 -c "import json,sys; d=json.load(sys.stdin); print([m.get('live') for m in d['matches'] if m['uid']=='basketball-esake-29CD5AD8'])"
