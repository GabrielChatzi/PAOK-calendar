"""Προσωρινό: τι δίνουν οι πηγές για παλιές σεζόν, και πού γράφουν οι σελίδες τα τρόπαια."""
import json, re, signal, sys, traceback, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_calendars as bc
import standings as st

OUT = Path("/tmp/out"); OUT.mkdir(exist_ok=True)

class TO(Exception): pass
def alarm(*_): raise TO("timeout")
signal.signal(signal.SIGALRM, alarm)

def run(fn, secs=90):
    signal.alarm(secs)
    try:
        return fn()
    finally:
        signal.alarm(0)

# ---- A: τρόπαια στις σελίδες
lines = []
for site in ["https://acpaok.gr", "https://www.paokbc.gr", "https://www.paokfc.gr"]:
    for page in range(1, 6):
        try:
            got = json.loads(bc.fetch(f"{site}/wp-json/wp/v2/pages?per_page=100&page={page}&_fields=id,title,link,content"))
        except Exception as e:
            lines.append(f"## {site} page {page}: {e}"); break
        if not got: break
        for p in got:
            text = bc.clean((p.get("content") or {}).get("rendered", ""))
            title = bc.clean(p["title"]["rendered"])
            hit = re.search(r"ΠΡΩΤΑΘΛ|ΚΥΠΕΛΛ|ΤΙΤΛ|ΤΡΟΠΑΙ|ΠΑΛΜΑΡ|ΚΑΤΑΚΤΗΣ", bc.plain(text + " " + title))
            lines.append(f"## {site} {p['id']} | {title} | {p['link']} | {len(text)} chars {'HIT' if hit else ''}")
            if hit:
                lines.append(text[:8000])
        if len(got) < 100: break
(OUT / "trophies.txt").write_text("\n".join(lines), encoding="utf-8")

# ---- B: παλιές σεζόν
orig = bc.season_start_year
rows = []
for year in [2025, 2024, 2023, 2022, 2021, 2019, 2016]:
    bc.season_start_year = lambda today=None, y=year: y
    st.season_start_year = bc.season_start_year
    bc._FETCHED.clear()
    for key, getters in bc.SOURCES.items():
        for name, get in getters:
            try:
                ms = run(get) or []
                ms = [m for m in ms if m]
                dates = sorted(m.start.date().isoformat() for m in ms if getattr(m, "start", None))
                scored = sum(1 for m in ms if getattr(m, "score", ""))
                ok = f"{len(ms)} αγώνες, {scored} με σκορ, {dates[0] if dates else '-'} … {dates[-1] if dates else '-'}"
            except Exception as e:
                ok = f"ΣΦΑΛΜΑ {type(e).__name__}: {str(e)[:120]}"
            rows.append(f"{year}\t{key}\t{name}\t{ok}")
            print(rows[-1], flush=True)
    for key, get in st.STANDINGS.items():
        try:
            t = run(get)
            ok = "; ".join(f"{x['title']} ({len(x['rows'])})" for x in t)[:200]
        except Exception as e:
            ok = f"ΣΦΑΛΜΑ {type(e).__name__}: {str(e)[:120]}"
        rows.append(f"{year}\t{key}\tΒΑΘΜΟΛΟΓΙΑ\t{ok}")
        print(rows[-1], flush=True)
(OUT / "seasons.tsv").write_text("\n".join(rows), encoding="utf-8")
