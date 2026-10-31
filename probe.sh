#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
curl -sS -m 30 -A "$UA" "https://live.koe.org.gr/waterpolo/main.4211092d4684fb4c.js" -o /tmp/j.js
python3 - <<'PY'
import re
s=open('/tmp/j.js',encoding='utf-8',errors='replace').read()
def ctx(pat, n=3, w=500):
    print("=====", pat)
    for m in list(re.finditer(pat, s))[:n]:
        print(s[max(0,m.start()-w):m.end()+w]); print("--")
print(sorted(set(re.findall(r'"([^"]{0,60}\.json[^"]{0,20})"', s))))
ctx(r'nomeHeader\(\)', 1, 1200)
ctx(r'competitionCode\s*=', 3, 300)
ctx(r'"/wp/', 3, 300)
PY
for f in assets/config.json config.json assets/api_config.json; do echo "-- $f"; curl -sS -m 20 -A "$UA" "https://live.koe.org.gr/waterpolo/$f" | head -c 300; echo; done
