#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
curl -sS "https://site.api.espn.com/apis/site/v2/sports/soccer/gre.1/summary?event=401896734" | python3 -c "import json,sys; d=json.load(sys.stdin); c=d['header']['competitions'][0]; print(c['status']['type']['name'], c['status'].get('displayClock'), [(x['team']['displayName'], x.get('score')) for x in c['competitors']])"
curl -sS "https://paokalendar.vercel.app/api/health?topic=s:football:live" ; echo
curl -sS "https://paokalendar.vercel.app/api/health?topic=s:football:pre" ; echo
