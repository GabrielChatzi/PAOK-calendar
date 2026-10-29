#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 40 -A "$UA" "https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?ID=1801" -o docs/cevold.html
curl -sSL -m 40 -A "$UA" "https://www-old.cev.eu/Competition-Area/CompetitionTeamDetails.aspx?TeamID=14088&ID=1801" -o docs/cevteam.html
python3 - <<'PY'
import re,html
for f in ["docs/cevold.html","docs/cevteam.html"]:
    t=open(f,encoding="utf-8",errors="replace").read()
    txt=html.unescape(re.sub(r"<[^>]+>"," ",re.sub(r"<script.*?</script>|<style.*?</style>","",t,flags=re.S)))
    txt=re.sub(r"\s+"," ",txt)
    print("####",f,len(t)); print(txt[:2500])
    i=txt.find("PAOK"); print("...PAOK:", txt[max(0,i-1500):i+1500] if i>=0 else "")
PY
