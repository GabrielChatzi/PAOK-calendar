#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import re, urllib.request, html, json
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0"}
get=lambda u: urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=40).read().decode("utf-8","replace")
EPO="https://www.epo.gr"
p=get(EPO+"/el/competition/5/matches")
sel=re.findall(r'<select[^>]*id="([^"]*)"[^>]*>(.*?)</select>', p, re.S)
for sid,body in sel: print(sid, [(html.unescape(v),l.strip()) for v,l in re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)',body)][:12])
print("ranking-table in main page:", 'ranking-table' in p)
urls=[html.unescape(v) for sid,body in sel for v,l in re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)',body) if '/stage/' in v]
for u in urls[:4]:
    q=get(EPO+u); m=re.search(r'<table class="ranking-table">(.*?)</table>', q, re.S)
    print("==", u, "ranking:", bool(m))
    if m:
        for tr in re.findall(r"<tr>(.*?)</tr>", m.group(1), re.S)[:5]:
            print("  ", [re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>","",c))).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)][:10])
# EA
EA="https://ea.microplustimingservices.com/api/wp"
t=json.loads(get(EA+"/site/token"))["data"]["token"]
h={**UA,"Authorization":"Bearer "+t}
for path in ["groupstandings","brackets","rounds","events/*"]:
    try:
        d=urllib.request.urlopen(urllib.request.Request(f"{EA}/EACLUB27/get/{path}",headers=h),timeout=40).read().decode()
        print("== EA", path, d[:900])
    except Exception as e: print("EA",path,e)
PY
