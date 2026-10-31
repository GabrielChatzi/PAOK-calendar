#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 -c "
import live, json
print(json.dumps(live.basketball_state({'src':'gs','key':'RFJIN037I07QV520B7WEXKV1GYNA31','day':'2026-10-31','side':'a'}), ensure_ascii=False))"
S=https://paokalendar.vercel.app
for t in s:basketball:live s:basketball:result m:0528a32db7:result m:0528a32db7:live; do echo -n "$t "; curl -sS "$S/api/health?topic=$t" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('matching'), d.get('byService'))"; done
