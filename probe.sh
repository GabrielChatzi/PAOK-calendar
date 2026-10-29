#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 build_calendars.py > build.log 2>&1; echo "exit $?"
grep -E "^futsal|! |Νέος|futsal" build.log | cut -c1-200 | head -30
python3 -c "
import json; d=json.load(open('docs/matches.json'))
for m in d['matches']:
  if m['section']=='futsal': print(m['start'], m['timeKnown'], m['home'], '–', m['away'], m['score'], m['round'], bool(m['homeLogo']))
s=json.load(open('docs/standings.json'))['futsal'][0]
for r in s['rows']: print(r['pos'], r['team'], r['cells'])"
echo "---- checks"; cat checks.md
rm -rf docs; mkdir -p docs; touch docs/.keep
