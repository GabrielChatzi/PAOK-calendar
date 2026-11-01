#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import urllib.request
U="https://site.api.espn.com/apis/site/v2/sports/soccer/gre.1/summary?event=401896734"
for name,h in [("live.py", {"User-Agent":"Mozilla/5.0 (PAOKalendar live; +https://paokalendar.vercel.app)","Cache-Control":"no-cache"}),
               ("no cache-control", {"User-Agent":"Mozilla/5.0 (PAOKalendar live; +https://paokalendar.vercel.app)"}),
               ("cache-control, plain UA", {"User-Agent":"Mozilla/5.0","Cache-Control":"no-cache"}),
               ("plain UA", {"User-Agent":"Mozilla/5.0"}),
               ("browser UA", {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36","Accept":"application/json"})]:
    try:
        with urllib.request.urlopen(urllib.request.Request(U,headers=h),timeout=20) as r: print(name, r.status)
    except Exception as e: print(name, e)
PY
