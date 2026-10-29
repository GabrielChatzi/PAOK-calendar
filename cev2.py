import re, html, urllib.request, concurrent.futures as cf
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
def get(i):
    u = f"https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?ID={i}"
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60) as r:
            t = r.read().decode("utf-8", "replace")
    except Exception as e:
        return i, "ERR " + str(e)[:60], False
    txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S))))
    m = re.search(r"Calendar Search Login (.{0,80}?) Men Women Home", txt)
    return i, (m.group(1) if m else txt[3000:3080]), "PAOK" in txt.upper()
with cf.ThreadPoolExecutor(8) as ex:
    for i, title, paok in ex.map(get, range(1905, 2150)):
        if "2027" in title or paok: print(i, title, "PAOK" if paok else "")
