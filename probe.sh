#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
curl -sS -m 30 -A "$UA" "https://live.koe.org.gr/waterpolo/main.4211092d4684fb4c.js" -o /tmp/j.js
python3 - <<'PY'
import re
s=open('/tmp/j.js',encoding='utf-8',errors='replace').read()
def ctx(pat, n=2, a=200, b=900):
    print("=====", pat)
    for m in list(re.finditer(pat, s))[:n]:
        print(s[max(0,m.start()-a):m.end()+b]); print("--")
ctx(r'convertStatus\(\w+\)\{', 1, 50, 1200)
ctx(r'getIconStatus\(\w+\)\{', 1, 50, 600)
ctx(r'jsonSta=', 3, 300, 500)
ctx(r'RESULTDB', 3, 300, 600)
PY
