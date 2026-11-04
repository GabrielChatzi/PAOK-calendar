#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
S=https://paokalendar.vercel.app
curl -sS -D /tmp/h "$S/matches.json" -o /tmp/m.json; grep -iE "cache-control|age:|x-vercel-cache" /tmp/h
python3 -c "
import json; d=json.load(open('/tmp/m.json'))
hb=[m for m in d['matches'] if m['section'].startswith('handball') and 'oxe' in m['uid']]
print('served handball with logos:', sum(1 for m in hb if m['homeLogo'] and m['awayLogo']), '/', len(hb), '| updated', d['updated'].get('handball'))"
curl -sS "$S/standings.json" | python3 -c "
import json,sys; s=json.load(sys.stdin); print('standings handball logos', sum(1 for t in s['handball'] for r in t['rows'] if r['logo']))"
curl -sS "$S/sw.js" | head -15 | grep -n "VERSION\|matches"
