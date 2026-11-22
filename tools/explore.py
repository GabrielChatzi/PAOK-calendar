"""Προσωρινό: πίνακες «ανά σεζόν» στα άρθρα των τμημάτων."""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path
OUT = Path("/tmp/out"); OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "PAOKalendar/1.0 (https://paokalendar.gr; info@paokalendar.gr)"}
pages = [("el", "Π.Α.Ο.Κ. (καλαθοσφαίριση ανδρών)"), ("el", "Π.Α.Ο.Κ. (καλαθοσφαίριση γυναικών)"), ("el", "Π.Α.Ο.Κ. (πετοσφαίριση ανδρών)"),
         ("el", "Π.Α.Ο.Κ. (υδατοσφαίριση)"), ("el", "Π.Α.Ο.Κ. (χειροσφαίριση γυναικών)"), ("el", "Π.Α.Ο.Κ. (ποδόσφαιρο γυναικών)"),
         ("en", "PAOK BC"), ("en", "PAOK FC (women)"), ("el", "Π.Α.Ο.Κ. (χειροσφαίριση ανδρών)"), ("el", "Π.Α.Ο.Κ. (πετοσφαίριση γυναικών)")]
for lang, title in pages:
    url = f"https://{lang}.wikipedia.org/w/api.php?format=json&action=parse&prop=wikitext&redirects=1&page=" + urllib.parse.quote(title)
    for a in range(5):
        try:
            d = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()); break
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            time.sleep(10 * (a + 1))
    w = d.get("parse", {}).get("wikitext", {}).get("*", "") if "error" not in d else ""
    safe = re.sub(r"\W+", "_", title)[:40]
    (OUT / f"{lang}-{safe}.txt").write_text(w, encoding="utf-8")
    time.sleep(1.5)
