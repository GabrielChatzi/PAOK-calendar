import json, re, urllib.request, sys
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60) as r:
        return r.read().decode("utf-8")
first = True
for sub in ("ehfcl", "ehfel", "ehfec"):
    for g in ("men", "women"):
        base = f"https://{sub}.eurohandball.com"
        try:
            html = get(f"{base}/{g}/2026-27/matches/")
        except Exception as e:
            print(sub, g, "ERR", e); continue
        comp = re.search(r'data-competition-id="([^"]+)"', html); cont = re.search(r'data-currentcontentid="(\d+)"', html)
        if not comp: print(sub, g, "no comp"); continue
        q = f"contentId={cont.group(1)}&competitionId={comp.group(1)}"
        init = json.loads(get(f"{base}/umbraco/api/competitionmatchesapi/GetInitMatches?{q}"))
        allm = list(init["matches"])
        for fut in (False, True):
            ms = init["matches"]
            for _ in range(30):
                if not ms: break
                anchor = (ms[-1] if fut else ms[0])["matchID"]
                ms = json.loads(get(f"{base}/umbraco/api/competitionmatchesapi/GetMatches?{q}&matchId={anchor}&futureMatches={'true' if fut else 'false'}"))["matches"]
                allm += ms
        print(f"## {sub} {g} {comp.group(1)} {cont.group(1)} total {len(allm)}")
        if first and allm:
            m = allm[0]; first = False
            print(json.dumps({k: (v if k not in ("comp",) else {kk: v[kk] for kk in ("round","phase","group","name")}) for k, v in m.items()}, ensure_ascii=False)[:3500])
        for m in allm:
            s = json.dumps(m, ensure_ascii=False)
            if "PAOK" in s.upper():
                h, a = m["homeTeam"], m.get("guestTeam") or m.get("awayTeam")
                print("  PAOK:", m["venue"]["date"].get("utc"), m["venue"]["date"].get("hasTime"), h["team"].get("fullName"), "-", a["team"].get("fullName") if a else None,
                      h.get("score"), (a or {}).get("score"), m["comp"]["round"]["name"], m["comp"]["phase"]["name"], m["comp"]["group"]["name"], m.get("url"), m.get("status"), m.get("isLive"))
