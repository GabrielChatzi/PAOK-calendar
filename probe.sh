#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import json, urllib.request
UA="Mozilla/5.0"
def get(u,h={}):
    with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA,**h}),timeout=30) as r: return json.loads(r.read())
K="https://live.koe.org.gr/api-waterpolo/wp"
t=get(K+"/token")["token"]
print(json.dumps(get(K+"/KOE/get/resultsDBlikeJSON/ASM/65/A01/1/9175200/9175106",{"x-wp-token":t}),ensure_ascii=False)[:2500])
print(json.dumps(get("https://paokalendar.vercel.app/api/live?src=koe&cat=ASM&gara=65&tur=A01&gru=1&a=9175200&b=9175106")))
PY
