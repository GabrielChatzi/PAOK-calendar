#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
curl -sSL -m 40 -A "$UA" -e https://www.basket.gr/livescore/ "https://apps.basket.gr/iframe/livescores?date=31/10/2026" -o /tmp/a.html
python3 - <<'PY'
import re, json, urllib.request
s=open('/tmp/a.html',encoding='utf-8',errors='replace').read()
cards=re.split(r'(?=<div[^>]+id="match-card-)', s)
for c in cards:
    if 'ΠΑΟΚ' in c:
        print(re.sub(r"\s+"," ",c)[:2500]); mid=re.search(r'id="match-card-(\d+)"',c).group(1); break
# headers with competition
print("HEADERS", re.findall(r'<div[^>]*class="[^"]*(?:tournament|competition|league)[^"]*"[^>]*>(.*?)</div>', s, re.S)[:8])
u=f"https://apps.basket.gr/iframe/livescores/get-matches-info?match_ids={mid}"
print(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","X-Requested-With":"XMLHttpRequest","Referer":"https://apps.basket.gr/iframe/livescores"}),timeout=30).read().decode()[:1500])
PY
