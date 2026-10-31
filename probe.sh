#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
echo "=== basket.gr wbl1"
curl -sSL -m 40 -A "$UA" https://www.basket.gr/wbl1/schedule/ -o /tmp/b.html; grep -oiE '.{0,80}(fibalivestats|geniussports|livestats|widget\.wh|webcast).{0,120}' /tmp/b.html | head -8
python3 - <<'PY'
import re
s=open('/tmp/b.html',encoding='utf-8',errors='replace').read()
i=s.find('ΠΑΟΚ'); blk=s[max(0,i-3000):i+1500]
print(sorted(set(re.findall(r'href="([^"]+)"', blk)))[:20])
PY
echo "=== basket.gr game page sample"
G=$(python3 -c "
import re; s=open('/tmp/b.html',encoding='utf-8',errors='replace').read()
l=[u for u in re.findall(r'href=\"(https?://www.basket.gr/[^\"]*(?:game|match|agonas)[^\"]*)\"', s)]; print(l[0] if l else '')")
echo "game: $G"; [ -n "$G" ] && curl -sSL -m 40 -A "$UA" "$G" | grep -oiE '.{0,80}(fibalivestats|geniussports|livestats|webcast|live).{0,120}' | head -8
echo "=== CEV dataproject live"
for h in cev-web cev; do curl -sS -m 30 -A "$UA" -o /tmp/c.html -w "$h %{http_code}\n" "https://$h.dataproject.com/MainLiveScore.aspx"; grep -oE 'id="HF_MatchesList" value="[^"]*"' /tmp/c.html; done
curl -sSL -m 30 -A "$UA" "https://www-old.cev.eu/" | grep -oiE '.{0,60}(livescore|dataproject|signalr).{0,100}' | head -5
echo "=== EHF match fields"
python3 - <<'PY'
import json, urllib.request
UA="Mozilla/5.0"
base="https://ehfec.eurohandball.com"
for gender in ("men","women"):
    try:
        u=f"{base}/{gender}/2026-27/matches/"
        s=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA}),timeout=40).read().decode()
        import re
        cid=re.search(r'data-competition-id="([^"]+)"',s); cur=re.search(r'data-currentcontentid="([^"]+)"',s)
        print(gender, cid and cid.group(1), cur and cur.group(1))
        q=f"competitionId={cid.group(1)}&roundId=&currentContentId={cur.group(1)}" if cid and cur else ""
        d=json.loads(urllib.request.urlopen(urllib.request.Request(f"{base}/umbraco/api/competitionmatchesapi/GetInitMatches?{q}",headers={"User-Agent":UA}),timeout=40).read())
        m=d["matches"][0]
        print(json.dumps({k:(v if not isinstance(v,(dict,list)) else str(v)[:200]) for k,v in m.items()}, ensure_ascii=False)[:1500])
    except Exception as e: print(gender, "ERR", e)
PY
