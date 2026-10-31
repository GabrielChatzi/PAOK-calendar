#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
curl -sS -m 30 -A "$UA" -e "https://www.esake.gr/" "https://widget.wh.geniussports.com/widget//?RFJIN037I07QV520B7WEXKV1GYNA31" -o /tmp/w.js
python3 - <<'PY'
import re, json, urllib.request
s=open('/tmp/w.js',encoding='utf-8',errors='replace').read()
h=json.loads('"'+re.search(r'var html = "(.*?)";\n', s, re.S).group(1)+'"')
lis=re.findall(r'<li class="spls_lsmatch[^"]*">(.*?)</li>', h, re.S)
print(len(lis))
txt=lambda x: re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' | ',x))
for li in lis:
    if 'PAOK' in li.upper() or 'ΠΑΟΚ' in li: print(txt(li)); print(re.findall(r'webcast/(\w+)/(\d+)', li))
print("comps", re.findall(r'<ul id = "sp_comp_\d+"', h)[:10])
print(txt(lis[0])[:500]); print(lis[0][:1500])
m=[re.findall(r'webcast/\w+/(\d+)', li)[0] for li in lis if 'PAOK' in li.upper()]
for mid in m[:2]:
    try:
        d=json.loads(urllib.request.urlopen(urllib.request.Request(f"https://fibalivestats.dcd.shared.geniussports.com/data/{mid}/data.json",headers={"User-Agent":UA}),timeout=30).read())
        print(mid, {k:(v if not isinstance(v,(dict,list)) else type(v).__name__) for k,v in d.items()})
        for t in ("1","2"): tm=d["tm"][t]; print(t, tm.get("name"), tm.get("score"), {k:v for k,v in tm.items() if k.startswith(("p","full","score"))})
    except Exception as e: print(mid, "ERR", e)
PY
