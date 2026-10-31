#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import re, urllib.request
u="https://waterpololeague.gr/championship/wpl-26-27/fixtures"
s=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=40).read().decode()
parts=re.split(r'<a href="(https://waterpololeague\.gr/fixture/[^"]+)" class="block">', s)
for link, body in zip(parts[1::2], parts[2::2]):
    if "ethnikos" in link and "paok" in link:
        print(link); print(re.sub(r"\s+"," ",body.split("</a>",1)[0])[:4000])
    elif "2026-10-31" in link or "2026-10-24" in link:
        b=re.sub(r"\s+"," ",body.split("</a>",1)[0]); i=b.find("sm:block"); print("OTHER", link, b[max(0,i-300):i+400])
PY
