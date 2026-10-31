#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
echo "=== apps.basket.gr iframe"
curl -sSL -m 40 -A "$UA" -e https://www.basket.gr/livescore/ https://apps.basket.gr/iframe/livescores -o /tmp/a.html; wc -c < /tmp/a.html
grep -oE '(src|href)="[^"]+"' /tmp/a.html | sort -u | head -15
grep -oiE '.{0,60}(fetch\(|axios|\$\.(get|ajax)|api/|\.json|websocket|socket|pusher|fibalivestats|genius).{0,120}' /tmp/a.html | sort -u | head -15
python3 - <<'PY'
import re
s=open('/tmp/a.html',encoding='utf-8',errors='replace').read()
t=re.sub(r"<script.*?</script>|<style.*?</style>","",s,flags=re.S); t=re.sub(r"<[^>]+>"," ",t); t=re.sub(r"\s+"," ",t)
print(t[:900])
PY
echo "=== EHF match page"
curl -sSL -m 40 -A "$UA" "https://www.eurohandball.com/en/matches/202712020703021/OFNIonias-ClubeJovemAlmeidaGarrett/" -o /tmp/e.html -w "%{http_code} %{url_effective}\n"
grep -oE '/umbraco/api/[A-Za-z]+/[A-Za-z]+' /tmp/e.html | sort -u | head; grep -oE 'data-[a-z-]+="[^"]{0,60}"' /tmp/e.html | sort -u | grep -iE "match|api|live" | head -10
python3 - <<'PY'
import json, urllib.request
UA="Mozilla/5.0"; base="https://ehfec.eurohandball.com"
q="competitionId=HUvNPxVw-FYaDNYG5p1ZLw&roundId=&currentContentId=138879"
d=json.loads(urllib.request.urlopen(urllib.request.Request(f"{base}/umbraco/api/competitionmatchesapi/GetInitMatches?{q}",headers={"User-Agent":UA}),timeout=40).read())["matches"]
for m in d:
    if m.get("isFinished"):
        h=m["homeTeam"]; print({k:v for k,v in h.items() if k!="team"}); break
PY
