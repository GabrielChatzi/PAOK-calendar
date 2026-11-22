"""Προσωρινό: υπάρχουν σελίδες σεζόν στη Wikipedia για άλλα τμήματα;"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path
OUT = Path("/tmp/out"); OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "PAOKalendar/1.0 (https://paokalendar.gr; info@paokalendar.gr)"}
def q(params):
    url = "https://en.wikipedia.org/w/api.php?format=json&" + urllib.parse.urlencode(params)
    for a in range(5):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            time.sleep(10 * (a + 1))
lines = []
for prefix in ["PAOK B.C.", "PAOK BC", "P.A.O.K. BC", "PAOK V.C.", "PAOK H.C.", "PAOK FC (women)", "PAOK W.B.C."]:
    d = q({"action": "query", "list": "search", "srsearch": f'intitle:"{prefix}" season', "srlimit": 50})
    for r in d["query"]["search"]:
        lines.append(f"{prefix}\t{r['title']}")
    time.sleep(1.5)
for lang, term in [("el", "ΠΑΟΚ μπάσκετ περίοδος"), ("el", "ΚΑΕ ΠΑΟΚ σεζόν")]:
    url = f"https://{lang}.wikipedia.org/w/api.php?format=json&action=query&list=search&srlimit=30&srsearch=" + urllib.parse.quote(term)
    d = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
    for r in d["query"]["search"]:
        lines.append(f"{lang}:{term}\t{r['title']}")
(OUT / "other.tsv").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
