#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
curl -sSL -m 30 -A "$UA" "https://www.handball.org.gr/competitions/protathlimata/handball-premier" -o /tmp/p.html; echo "premier $(wc -c </tmp/p.html)"
grep -oE 'href="/competitions/[^"]*"' /tmp/p.html | sort -u | head -30
python3 - <<'PY'
import re, html
p=open('/tmp/p.html',encoding='utf-8',errors='replace').read()
imgs=re.findall(r'<img[^>]+>', p)
print(len(imgs),'imgs')
for i in imgs:
    if 'favicon' in i or 'logo.png' in i or 'logo-mobile' in i: continue
    src=re.search(r'src="([^"]+)"',i); alt=re.search(r'alt="([^"]*)"',i)
    print(html.unescape(alt.group(1) if alt else ''), '|', src.group(1)[:120] if src else '')
PY
