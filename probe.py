import urllib.request, os
os.makedirs("docs/probe", exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
for n in ("Header", "PlayByPlay", "Boxscore"):
    u = f"https://live.euroleague.net/api/{n}?gamecode=111&seasoncode=U2026"
    b = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA, "Cache-Control": "no-cache"}), timeout=30).read().decode("utf-8-sig")
    open(f"docs/probe/{n}.json", "w").write(b); print(n, len(b), b[:1500] if n == "Header" else "")
