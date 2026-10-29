import re, html, urllib.request
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60) as r:
        return r.read().decode("utf-8", "replace")
def text(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S))))
for pid in (3545, 3546, 3547, 3548, 3549):
    t = get(f"https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?ID=1949&PID={pid}")
    tabs = re.findall(r'rtsTxt">([^<]+)<', t)
    sel = re.findall(r'rtsLink[^"]*rtsSelected"[^>]*>(?:<[^>]+>)*([^<]+)', t)
    x = text(t); j = x.find("PAOK THESSALONIKI")
    print(pid, "tabs", tabs, "sel", sel, "matchlinks", len(re.findall(r"MatchPage\.aspx", t)))
    k = x.find("Home Matches"); print("   ", x[k:k+700])
