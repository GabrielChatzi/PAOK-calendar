#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
S=https://api.sofascore.com/api/v1
curl -sS -m 30 -A "$UA" -D /tmp/h -o docs/search.json "$S/search/all?q=PAOK&page=0"; head -20 /tmp/h | grep -iE "^HTTP|access-control|cf-|content-type"
python3 - <<'PY'
import json
try:
    d = json.load(open("docs/search.json"))
    for r in d.get("results", [])[:25]:
        e = r.get("entity", {}); 
        print(r.get("type"), e.get("id"), e.get("name"), (e.get("sport") or {}).get("slug"), e.get("gender"), (e.get("country") or {}).get("name"))
except Exception as ex: print("ERR", ex, open("docs/search.json").read()[:300])
PY
curl -sS -m 30 -A "$UA" -H "Origin: https://paokalendar.vercel.app" -D /tmp/h2 -o /dev/null "$S/sport/football/events/live"; grep -iE "^HTTP|access-control" /tmp/h2
