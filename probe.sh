#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 -c "
import standings
for t in standings.volley_women():
    print(t['title'])
    for r in t['rows']: print(r['pos'], r['team'], r['cells'], bool(r['logo']))"
