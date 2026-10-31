#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
echo "=== basket.gr livescore"
curl -sSL -m 40 -A "$UA" https://www.basket.gr/livescore/ -o /tmp/l.html; wc -c < /tmp/l.html
grep -oiE '(src|data-[a-z-]+)="[^"]*(live|score|genius|api|json)[^"]*"' /tmp/l.html | sort -u | head -15
grep -oiE '.{0,80}(fibalivestats|geniussports|widget\.wh|ajax|wp-json|admin-ajax).{0,120}' /tmp/l.html | sort -u | head -10
echo "=== CEV live page"
curl -sSL -m 30 -A "$UA" "https://www-old.cev.eu/MainLiveScore.aspx" -o /tmp/c.html -w "%{http_code}\n"; grep -oE 'id="HF_MatchesList" value="[^"]*"' /tmp/c.html; grep -oE 'src="[^"]*(signalr|LiveScore)[^"]*"' /tmp/c.html | head
curl -sS -m 30 -A "$UA" "https://www-old.cev.eu/Scripts/LiveScoreListSignalR.js" | grep -n "cev" | head -5
echo "=== EHF anchor + score fields"
python3 - <<'PY'
import json, urllib.request, re
UA="Mozilla/5.0"; base="https://ehfec.eurohandball.com"
q="competitionId=HUvNPxVw-FYaDNYG5p1ZLw&roundId=&currentContentId=138879"
get=lambda u: json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA}),timeout=40).read())
d=get(f"{base}/umbraco/api/competitionmatchesapi/GetInitMatches?{q}")["matches"]
ids=[m["matchID"] for m in d]; print("init", ids[:6])
fin=[m for m in d if m.get("isFinished")]
m=fin[0] if fin else d[-1]
print(json.dumps(m["homeTeam"], ensure_ascii=False)[:600])
for fut in ("true","false"):
    x=get(f"{base}/umbraco/api/competitionmatchesapi/GetMatches?{q}&matchId={ids[2]}&futureMatches={fut}")["matches"]
    print(fut, [y["matchID"] for y in x][:6], ids[2] in [y["matchID"] for y in x])
PY
