#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import json, urllib.request
UA="Mozilla/5.0"; base="https://ehfec.eurohandball.com"
q="competitionId=HUvNPxVw-FYaDNYG5p1ZLw&roundId=&currentContentId=138879"
get=lambda u: json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA}),timeout=40).read())
d=get(f"{base}/umbraco/api/competitionmatchesapi/GetInitMatches?{q}")["matches"]
fin=[m for m in d if m.get("isFinished")]
mid=fin[0]["matchID"] if fin else d[0]["matchID"]
x=get(f"https://www.eurohandball.com/umbraco/api/matchdetailapi/GetMatchDetails?matchId={mid}")
def walk(o,p=""):
    if isinstance(o,dict):
        for k,v in o.items(): walk(v,p+"."+k)
    elif isinstance(o,list):
        if o: walk(o[0],p+"[0]")
    else:
        if any(w in p.lower() for w in ("score","goal","time","live","finish","state","period","half","team.fullname","minute")): print(p,"=",str(o)[:70])
walk(x["matchDetails"])
PY
