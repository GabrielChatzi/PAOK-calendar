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

# ---- B: ESPN με season, σελίδες ESAKE και τίτλων
extra = []
for url in ["https://www.paokbc.gr/el/istoria/tropaia", "https://www.paokfc.gr/istoria/oi-titloi/"]:
    try:
        page = bc.fetch(url)
        sub = re.findall(r'href="(https://www.paokfc.gr/istoria/oi-titloi/[^"]+)"', page)
        extra.append(f"## {url}\n{bc.clean(page)[:12000]}\nsub: {sorted(set(sub))}")
        for u in sorted(set(sub))[:15]:
            try:
                extra.append(f"### {u}\n{bc.clean(bc.fetch(u))[:5000]}")
            except Exception as e:
                extra.append(f"### {u}: {e}")
    except Exception as e:
        extra.append(f"## {url}: {e}")
page = bc.fetch("https://www.esake.gr/el/action/EsaketeamView?idteam=0000000C&mode=3")
i = page.find("Επιλογή αγωνιστικής")
extra.append("## esake form\n" + page[max(0, i - 3000):i + 400])
for u in ["https://www.esake.gr/el/action/EsaketeamView?idteam=0000000C&mode=3&idchampionship=4820C134",
          "https://www.esake.gr/el/action/EsaketeamView?idteam=0000000C&mode=3&idchamp=4820C134"]:
    try:
        pg = bc.fetch(u); extra.append(f"## {u}: {len(pg)} chars, 2024 in titles: {pg.count('2024')}, 2026: {pg.count('2026')}")
    except Exception as e:
        extra.append(f"## {u}: {e}")
for url in []:
    try:
        page = bc.fetch(url)
        links = sorted(set(re.findall(r'href="([^"]*(?:season|seira|idseason|archive|arxeio|titl|troph|istori|palmar|history)[^"]*)"', page, re.I)))
        opts = re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)</option>', page)[:60]
        extra.append(f"## {url}\nlinks: {links[:80]}\noptions: {opts}")
    except Exception as e:
        extra.append(f"## {url}: {e}")
(OUT / "extra2.txt").write_text("\n".join(extra), encoding="utf-8")
