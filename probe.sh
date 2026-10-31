#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
python3 - <<'PY'
import re, urllib.request
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0"
for mode in (3,2):
    s=urllib.request.urlopen(urllib.request.Request(f"https://www.esake.gr/el/action/EsakegameView?idgame=29CD5AD8&mode={mode}",headers={"User-Agent":UA}),timeout=30).read().decode("utf-8","replace")
    t=re.sub(r"<script.*?</script>|<style.*?</style>","",s,flags=re.S); t=re.sub(r"<[^>]+>"," ",t); t=re.sub(r"\s+"," ",t)
    i=t.find("ΗΡΑΚΛ"); print("MODE",mode, t[max(0,i-200):i+700]); print()
    print(sorted(set(re.findall(r'(?:src|href)="([^"]+\.(?:js|json|aspx)[^"]*)"', s)))[:15])
    print(re.findall(r'(?:ajax|url)\s*[:=]\s*["\']([^"\']+)', s)[:10])
PY
