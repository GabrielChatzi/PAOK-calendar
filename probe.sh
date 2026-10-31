#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import json, urllib.request
def get(u,h={}):
    with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0",**h}),timeout=30) as r: return json.loads(r.read())
K="https://live.koe.org.gr/api-waterpolo/wp"
t=get(K+"/token")["token"]; H={"x-wp-token":t}
print(json.dumps(get(K+"/KOE/get/resultsDBlikeJSON/ASM/65/A01/1/9175200/9175106",H),ensure_ascii=False))
d=get(K+"/KOE/get/schedulereferee/ASM/65/*/*/*",H)
sch=d.get("Schedule", d) if isinstance(d,dict) else d
print(type(d).__name__, list(d.keys())[:5] if isinstance(d,dict) else len(d))
for x in (sch if isinstance(sch,list) else []):
    if x.get("OraMatchDate")=="31/10/2026": print(json.dumps(x,ensure_ascii=False)[:600])
PY
