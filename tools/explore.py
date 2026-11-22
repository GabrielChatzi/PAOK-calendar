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

# ---- B: ESPN με season, σελίδες ESAKE και τίτλων
extra = []
for y in (2024, 2020, 2015):
    for league in ("gre.1", "gre.cup", "uefa.europa", "uefa.europa.conf", "uefa.champions"):
        try:
            d = json.loads(bc.fetch(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{bc.ESPN_TEAM_ID}/schedule?season={y}"))
            ev = d.get("events", [])
            extra.append(f"ESPN {y} {league}: {len(ev)} {ev[0]['date'] if ev else ''} … {ev[-1]['date'] if ev else ''}")
        except Exception as e:
            extra.append(f"ESPN {y} {league}: {e}")
for url in ["https://www.esake.gr/el/action/EsaketeamView?idteam=0000000C&mode=3",
            "https://www.paokbc.gr/el/omada/titloi", "https://www.paokbc.gr/el/istoria", "https://www.paokfc.gr/",
            "https://www.paokbc.gr/el/"]:
    try:
        page = bc.fetch(url)
        links = sorted(set(re.findall(r'href="([^"]*(?:season|seira|idseason|archive|arxeio|titl|troph|istori|palmar|history)[^"]*)"', page, re.I)))
        opts = re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)</option>', page)[:60]
        extra.append(f"## {url}\nlinks: {links[:80]}\noptions: {opts}")
    except Exception as e:
        extra.append(f"## {url}: {e}")
(OUT / "extra.txt").write_text("\n".join(extra), encoding="utf-8")
