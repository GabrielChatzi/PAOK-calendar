#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
curl -sSL -m 40 -A "$UA" -e https://www.basket.gr/livescore/ "https://apps.basket.gr/iframe/livescores?date=31/10/2026" -o /tmp/a.html
python3 - <<'PY'
import re
s=open('/tmp/a.html',encoding='utf-8',errors='replace').read()
for m in re.finditer(r'\$\.ajax\(\{', s): print(s[m.start()-300:m.start()+700].replace("\n"," ")[:1000]); print("----")
i=s.find('WOMEN'); i = i if i>0 else s.find('ΓΥΝΑΙΚ')
t=re.sub(r"<script.*?</script>|<style.*?</style>","",s,flags=re.S); t=re.sub(r"<[^>]+>"," ",t); t=re.sub(r"\s+"," ",t)
j=t.find('ΠΑΟΚ'); print("PAOK ctx:", t[max(0,j-300):j+300])
print(sorted(set(re.findall(r'data-[a-z-]+="[^"]{0,40}"', s)))[:30])
PY
echo "=== EHF GetMatchDetails"
curl -sS -m 40 -A "$UA" "https://www.eurohandball.com/umbraco/api/matchdetailapi/GetMatchDetails?matchId=202712020703021" | python3 -c "
import json,sys; d=json.load(sys.stdin); print(type(d).__name__, list(d.keys())[:40] if isinstance(d,dict) else '')
def show(x,p=''):
  if isinstance(x,dict):
    for k,v in x.items():
      if isinstance(v,(dict,list)): 
        if p.count('.')<2: show(v,p+k+'.')
      else: print(p+k, '=', str(v)[:60])
show(d)" | head -60
