#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import json,urllib.request
U="https://site.api.espn.com/apis/site/v2/sports/soccer/gre.1/summary?event=401896734"
d=json.load(urllib.request.urlopen(urllib.request.Request(U,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}),timeout=20))
c=d['header']['competitions'][0]; print(c['status']['type']['name'], c['status'].get('displayClock'), [(x['team']['displayName'], x.get('score')) for x in c['competitors']])
for e in d.get('keyEvents',[]): print(e.get('type',{}).get('text'), e.get('clock',{}).get('displayValue'), e.get('scoringPlay'))
PY
