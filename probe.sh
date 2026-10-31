#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
curl -sS -m 30 -A "$UA" https://www.esake.gr/ -o /tmp/e.html
python3 - <<'PY'
import re
s=open('/tmp/e.html',encoding='utf-8',errors='replace').read()
for m in re.finditer(r'Genius Sports Widget', s):
    print(s[m.start()-200:m.start()+1500]); print("-----")
PY
curl -sS -m 30 -A "$UA" -e "https://www.esake.gr/" "https://widget.wh.geniussports.com/widget//?RFJIN037I07QV520B7WEXKV1GYNA31" -o /tmp/w.js
python3 - <<'PY'
import re
s=open('/tmp/w.js',encoding='utf-8',errors='replace').read()
print(len(s)); print(sorted(set(re.findall(r'https?://[A-Za-z0-9./_?=&-]+', s)))[:40])
print(s[:1500])
PY
