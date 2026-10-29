import re, html, urllib.request
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60) as r:
        return r.read().decode("utf-8", "replace")
t = get("https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?ID=1949")
open("docs/cev1949.html", "w").write(t)
for h in sorted(set(re.findall(r'href="([^"]*(?:PID|Phase|Match|Calendar)[^"]*)"', t))): print("LINK", html.unescape(h))
txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S))))
i = txt.find("Skip Navigation Links"); print(txt[i:i+1500])
j = txt.upper().find("PAOK"); print("PAOK:", txt[max(0, j-800):j+400])
k = t.upper().find("PAOK"); print("RAW:", t[max(0, k-3000):k+600])
