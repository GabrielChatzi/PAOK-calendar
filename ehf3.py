import json, urllib.request, re
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
def raw(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60) as r:
        return r.read().decode("utf-8")
base = "https://ehfec.eurohandball.com"
q = "contentId=138859&competitionId=0NO-qzR3XKKIL4ING3vbOA"
ms = json.loads(raw(f"{base}/umbraco/api/competitionmatchesapi/GetMatches?{q}&matchId=202711020703025&futureMatches=true"))["matches"]
for m in ms:
    for side in ("homeTeam", "guestTeam"):
        t = m[side]["team"]
        if "PAOK" in t["fullName"]:
            print(json.dumps({k: t[k] for k in ("id", "name", "fullName", "url", "logoSmall", "shortName")}, ensure_ascii=False))
            url = t["url"]
html = raw(url if url.startswith("http") else base + url)
print(len(html))
for a in re.findall(r'data-[a-z-]*(?:url|id)="[^"]*"', html)[:60]: print(a)
