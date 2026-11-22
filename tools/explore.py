"""Προσωρινό: σελίδες σεζόν του ΠΑΟΚ στη Wikipedia."""
import json, re, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_calendars as bc
OUT = Path("/tmp/out"); OUT.mkdir(exist_ok=True)
lines = []
API = "https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=wikitext&redirects=1&page="
for y in range(1959, 2026):
    title = f"{y}–{(y + 1) % 100:02d} PAOK FC season"
    if y == 1999: title = "1999–2000 PAOK FC season"
    try:
        d = json.loads(bc.fetch(API + urllib.parse.quote(title)))
    except Exception as e:
        lines.append(f"{y}\tERR {e}"); continue
    if "error" in d:
        lines.append(f"{y}\tMISSING"); continue
    w = d["parse"]["wikitext"]["*"]
    boxes = re.findall(r"\{\{\s*(Football box[^|\n]*|footballbox[^|\n]*|Fb[^|\n]*)", w, re.I)
    res = re.search(r"\|\s*league result\s*=\s*([^\n|]*)", w)
    cup = re.search(r"\|\s*cup1? result\s*=\s*([^\n|]*)", w)
    lines.append(f"{y}\t{len(w)}\tboxes={len(boxes)} {sorted(set(b.strip() for b in boxes))[:4]}\tleague={res[1].strip() if res else '-'}\tcup={cup[1].strip() if cup else '-'}")
    if y in (1985, 2000, 2010, 2018, 2024):
        i = w.find("{{Football box")
        if i < 0: i = w.lower().find("{{footballbox")
        (OUT / f"sample-{y}.txt").write_text(w[i:i + 6000] if i >= 0 else w[:6000], encoding="utf-8")
(OUT / "wiki.tsv").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
