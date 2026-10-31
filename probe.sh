#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 -c "
import live, json
print(json.dumps(live.basketball_state({'src':'gs','key':'RFJIN037I07QV520B7WEXKV1GYNA31','day':'2026-10-31','side':'a'}), ensure_ascii=False))"
