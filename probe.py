"""Κατεβάζει υποψήφιες πηγές για το αρχείο σε probe_out/ (για ανάλυση εκτός GitHub)."""
import json, os, re, sys, time, urllib.parse, urllib.request
OUT = "probe_out"; os.makedirs(OUT, exist_ok=True)
UA = "PAOKalendar/1.0 (https://paokalendar.gr; info@paokalendar.gr)"
log = open(f"{OUT}/_log.txt", "w")
def get(name, url, data=None):
    try:
        req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept-Language": "el,en"})
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
        open(f"{OUT}/{name}", "wb").write(b)
        log.write(f"OK {len(b):8d} {name} {url}\n"); log.flush()
        return b.decode("utf-8", "replace")
    except Exception as e:
        log.write(f"ERR {name} {url} {e}\n"); log.flush()
        return ""
def wiki(lang, title, name):
    u = f"https://{lang}.wikipedia.org/w/api.php?format=json&action=parse&prop=wikitext&redirects=1&page=" + urllib.parse.quote(title)
    t = get(name, u); time.sleep(1)
    return t
def search(lang, q, name):
    u = f"https://{lang}.wikipedia.org/w/api.php?format=json&action=query&list=search&srlimit=50&srsearch=" + urllib.parse.quote(q)
    get(name, u); time.sleep(1)


# 2ος γύρος
for g in ("male","female"):
    get(f"wpl_champs_{g}.html", f"https://waterpololeague.gr/championships?gender={g}")
import glob
slugs=set()
for f in glob.glob(f"{OUT}/wpl_champs_*.html"):
    slugs |= set(re.findall(r'waterpololeague\.gr/championship/([a-z0-9-]+)', open(f, errors="ignore").read()))
log.write("WPL slugs: " + " ".join(sorted(slugs)) + "\n")
for sl in sorted(slugs)[:3]:
    get(f"wplold_{sl[:40]}.html", f"https://waterpololeague.gr/championship/{sl}/fixtures")
    get(f"wplold_st_{sl[:40]}.html", f"https://waterpololeague.gr/championship/{sl}/standings")
for i in range(3, 19):
    get(f"dp_comp_{i}.html", f"https://eope-web.dataproject.com/CompetitionHome.aspx?ID={i}")
get("dp_matches_8.html", "https://eope-web.dataproject.com/CompetitionMatches.aspx?ID=8")
get("bgr_champs_2018.html", "https://www.basket.gr/champs-2018-2019/")
get("bgr_periodoy_2023.html", "https://www.basket.gr/protathlimata-agon-periodoy-2023-2024/")
for d in ("26", "30", "1"):
    get(f"esake_rank_03_day{d}.html", f"https://www.esake.gr/el/action/EsakeRanking?idchampionship=00000003&day={d}")
for t in ("Πρωτάθλημα καλαθοσφαίρισης Α1 εθνικής κατηγορίας ανδρών 1993-1994",
          "Πρωτάθλημα καλαθοσφαίρισης ανδρών Basket League 2013-2014",
          "Πρωτάθλημα καλαθοσφαίρισης Α1 εθνικής κατηγορίας γυναικών 2018-2019",
          "Α1 Κατηγορία υδατοσφαίρισης ανδρών 2009-2010", "Α1 Εθνική υδατοσφαίρισης ανδρών 2013–14",
          "Α΄ Κατηγορία υδατοσφαίρισης γυναικών 2020-21", "Πρωτάθλημα Ελλάδας υδατοσφαίρισης ανδρών",
          "Πρωτάθλημα Ελλάδας υδατοσφαίρισης γυναικών", "Πρωτάθλημα Ελλάδας καλαθοσφαίρισης γυναικών"):
    wiki("el", t, "wk2_el_" + re.sub(r"\W+", "_", t)[-40:] + ".json")
for t in ("2022–23 Greek A Division (women's football)", "2015–16 A1 Ethniki (men's water polo)", "A1 Ethniki Water Polo",
          "A1 Ethniki Women's Water Polo", "P.A.O.K. Women's Volleyball", "2024–25 Greek Women's Basketball League"):
    wiki("en", t, "wk2_en_" + re.sub(r"\W+", "_", t)[:40] + ".json")
def allsearch(lang, q, name):
    res=[]; off=0
    while off < 1500:
        u=f"https://{lang}.wikipedia.org/w/api.php?format=json&action=query&list=search&srlimit=500&sroffset={off}&srsearch="+urllib.parse.quote(q)
        try:
            d=json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60).read())
        except Exception as e:
            log.write(f"ERR search {q} {e}\n"); break
        res += [x["title"] for x in d["query"]["search"]]
        if "continue" not in d: break
        off = d["continue"]["sroffset"]; time.sleep(1)
    open(f"{OUT}/{name}", "w").write(json.dumps(res, ensure_ascii=False, indent=0))
    log.write(f"SEARCH {name}: {len(res)}\n")
allsearch("el", 'intitle:"καλαθοσφαίρισης" intitle:"ανδρών"', "ttl_el_bk_men.json")
allsearch("el", 'intitle:"καλαθοσφαίρισης" intitle:"γυναικών"', "ttl_el_bk_women.json")
allsearch("el", 'intitle:"υδατοσφαίρισης" intitle:"ανδρών"', "ttl_el_wp_men.json")
allsearch("el", 'intitle:"υδατοσφαίρισης" intitle:"γυναικών"', "ttl_el_wp_women.json")
allsearch("el", 'intitle:"πετοσφαίρισης" intitle:"γυναικών"', "ttl_el_vb_women.json")
allsearch("el", 'intitle:"χειροσφαίρισης"', "ttl_el_hb.json")
allsearch("el", 'intitle:"ποδοσφαίρου γυναικών"', "ttl_el_fbw.json")
allsearch("en", 'intitle:"water polo" intitle:"A1 Ethniki"', "ttl_en_wp.json")
allsearch("en", "intitle:\"Greek A Division (women's football)\"", "ttl_en_fbw.json")
allsearch("el", 'ΠΑΟΚ υδατοσφαίριση ανδρών', "ttl_el_paok_wp.json")
log.close()
