import json, re, os, urllib.request, urllib.parse
OUT = "docs/probe"; os.makedirs(OUT, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def get(url, headers=None, data=None):
    h = {"User-Agent": UA}; h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h, data=data), timeout=30) as r: return r.status, r.read().decode("utf-8-sig", "replace")
    except urllib.error.HTTPError as e: return e.code, e.read().decode("utf-8", "replace")[:500]
    except Exception as e: return 0, str(e)
for u in ("https://eope-web.dataproject.com/MatchStatistics.aspx?mID=762", "https://eope-web.dataproject.com/MatchStatistics.aspx?mID=762&ID=0"):
    st, b = get(u); print(u, st, len(b), b.count('id="PlayerName"'))
DP = "https://dataprojectservicesignalr.azurewebsites.net/signalr"; HUB = "signalrlivehubfederations"
for fed, lst in (("eope", "762"), ("eope", "762;756")):
    h = {"Origin": f"https://{fed}-web.dataproject.com", "Referer": f"https://{fed}-web.dataproject.com/"}
    cd = urllib.parse.quote(json.dumps([{"name": HUB}]))
    st, neg = get(f"{DP}/negotiate?clientProtocol=2.1&connectionData={cd}", h); neg = json.loads(neg)
    q = f"transport=longPolling&clientProtocol=2.1&connectionToken={urllib.parse.quote(neg['ConnectionToken'])}&connectionData={cd}"
    get(f"{DP}/connect?{q}", h); get(f"{DP}/start?{q}", h)
    body = "data=" + urllib.parse.quote(json.dumps({"H": HUB, "M": "getLiveScoreListData_From_ES", "A": [lst, fed], "I": 0}))
    st, out = get(f"{DP}/send?{q}", {**h, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, body.encode())
    print(fed, lst, st, out[:3000])
# Πού βρίσκεται το ID διοργάνωσης στη σελίδα LIVE SCORE
st, b = get("https://hvl-web.dataproject.com/MainLiveScore.aspx"); print("hvl live", st, re.findall(r'MatchStatistics\.aspx\?[^"\']+', b)[:5], re.findall(r'id="HF_\w+" value="[^"]*"', b)[:10])
