#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
S=https://paokalendar.vercel.app
curl -sS "$S/api/live?src=dp&fed=hvl&day=2026-10-31&side=h"; echo
for t in s:volley:live m:d3d69c179b:live s:volley:result; do echo -n "$t "; curl -sS "$S/api/health?topic=$t" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('matching'), d.get('byService'))"; done
curl -sS "$S/matches.json" | python3 -c "import json,sys; d=json.load(sys.stdin); print([m.get('live') for m in d['matches'] if m['uid']=='volley-2026-27-740b2b9638ba'])"
