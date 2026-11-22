"""Προσωρινό: ολόκληρες σελίδες σεζόν από τη Wikipedia για δοκιμές."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import wiki
OUT = Path("/tmp/out"); OUT.mkdir(exist_ok=True)
for y in (1972, 1985, 1996, 2003, 2009, 2018, 2024):
    (OUT / f"full-{y}.txt").write_text(wiki.fetch_wikitext(y) or "", encoding="utf-8")
