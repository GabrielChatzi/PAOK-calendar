import re, html, urllib.request
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60) as r:
        return r.geturl(), r.read().decode("utf-8", "replace")
_, t = get("https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?ID=1801")
links = {}
for m in re.finditer(r'href="(https://www-old\.cev\.eu/Competition-Area/competition\.aspx\?ID=\d+)"[^>]*>\s*<span[^>]*><b>([^<]+)</b>', t):
    links[html.unescape(m.group(2))] = m.group(1)
print(links)
for name, u in links.items():
    if not re.search(r"Champions League|CEV Cup|Challenge Cup", name): continue
    final, page = get(u)
    title = re.search(r"(CEV[^<|]{0,60}\d{4}\s*\|\s*(?:Men|Women)|\d{4} CEV[^<]{0,60})", page)
    has = "PAOK" in page.upper()
    print("##", name, final, title.group(1) if title else None, "PAOK" if has else "")
    for h in sorted(set(re.findall(r'href="([^"]*(?:Match|Calendar|Results|Phase)[^"]*)"', page)))[:15]: print("   ", html.unescape(h))
