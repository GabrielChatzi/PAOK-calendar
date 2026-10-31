#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
S=https://paokalendar.vercel.app
curl -sS "$S/matches.json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('generated') or d.get('updated')); print([(s['key'], s.get('live')) for s in d['sections']])"
for t in s:volley:pre s:volley:time m:d3d69c179b:result m:d3d69c179b:pre; do echo -n "$t "; curl -sS "$S/api/health?topic=$t" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('matching'))"; done
