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

# Wikipedia: ποδόσφαιρο (σελίδες σεζόν ΠΑΟΚ + πρωταθλήματος), δείγμα
for y in (1975, 1985, 1998, 2010, 2020):
    end = f"{y+1}" if y == 1999 else f"{(y+1)%100:02d}"
    wiki("en", f"{y}–{end} PAOK FC season", f"wk_fb_paok_{y}.json")
for t in ("1985–86 Alpha Ethniki", "1975–76 Alpha Ethniki", "1998–99 Alpha Ethniki", "2010–11 Super League Greece", "1968–69 Alpha Ethniki"):
    wiki("en", t, "wk_fb_league_" + t[:7] + ".json")
# Μπάσκετ
search("en", "A1 Ethniki basketball season", "wk_s_basket_en.json")
for t in ("1998–99 A1 Ethniki", "1998–99 Greek A1 Basketball League", "2010–11 Greek Basket League", "1992–93 A1 Ethniki"):
    wiki("en", t, "wk_bk_" + t.replace(" ", "_")[:30] + ".json")
search("el", "Α1 Εθνική καλαθοσφαίρισης περίοδος", "wk_s_basket_el.json")
# Αθλήματα χωρίς περιλήψεις: ελληνικά άρθρα τμημάτων
for t in ("Π.Α.Ο.Κ. (υδατοσφαίριση ανδρών)", "Π.Α.Ο.Κ. (υδατοσφαίριση γυναικών)", "Π.Α.Ο.Κ. (καλαθοσφαίριση γυναικών)",
          "Π.Α.Ο.Κ. (χειροσφαίριση γυναικών)", "Π.Α.Ο.Κ. (ποδόσφαιρο γυναικών)", "Π.Α.Ο.Κ. (ποδόσφαιρο σάλας)",
          "Π.Α.Ο.Κ. (πετοσφαίριση γυναικών)"):
    wiki("el", t, "wk_el_" + re.sub(r"\W+", "_", t)[-28:] + ".json")
for t in ("PAOK (water polo)", "PAOK women's water polo", "PAOK BC (women)", "PAOK women's basketball", "PAOK (women's handball)"):
    wiki("en", t, "wk_en_" + re.sub(r"\W+", "_", t)[:28] + ".json")
search("el", "Πρωτάθλημα υδατοσφαίρισης ανδρών Ελλάδας περίοδος", "wk_s_wp_el.json")
search("en", "Greek Water Polo League season", "wk_s_wp_en.json")
search("en", "A1 Ethniki Women water polo", "wk_s_wpw_en.json")
search("en", "Greek Women's Basketball League season", "wk_s_bkw_en.json")
search("en", "Greek A Division women football season", "wk_s_fbw_en.json")
search("en", "Greek Volley League Women season", "wk_s_vw_en.json")

# Πόλο: waterpololeague.gr
p = get("wpl_cur_fixtures.html", "https://waterpololeague.gr/championship/wpl-26-27/fixtures")
get("wpl_home.html", "https://waterpololeague.gr/")
links = sorted(set(re.findall(r'https://waterpololeague\.gr/championship/[a-z0-9-]+', p + open(f"{OUT}/wpl_home.html", errors="ignore").read() if os.path.exists(f"{OUT}/wpl_home.html") else p)))
log.write("WPL links: " + " ".join(links) + "\n")
for s in ("wpl-25-26", "wpl-women-25-26", "wpl-2025-26", "wpl-24-25", "wpl-21-22", "wpl-19-20"):
    get(f"wpl_{s}.html", f"https://waterpololeague.gr/championship/{s}/fixtures")
get("wpl_championships.html", "https://waterpololeague.gr/championships")
# ΚΟΕ
get("koe_wp.html", "https://koe.org.gr/sports/water-polo")
get("koe_home.html", "https://koe.org.gr/")
# ΕΠΟ γυναικών
get("epo_6.html", "https://www.epo.gr/el/competition/6/matches")
# basket.gr WBL1
get("wbl1_schedule.html", "https://www.basket.gr/wbl1/schedule/")
get("wbl1_home.html", "https://www.basket.gr/wbl1/")
# Data Project ΕΟΠΕ
h = get("dp_home.html", "https://eope-web.dataproject.com/MainHome.aspx")
get("dp_archive.html", "https://eope-web.dataproject.com/MainArchive.aspx")
get("dp_compsearch.html", "https://eope-web.dataproject.com/CompetitionsList.aspx")
# ESAKE
get("esake_ranking.html", "https://www.esake.gr/el/action/EsakeRanking")
tp = get("esake_team.html", "https://www.esake.gr/el/action/EsaketeamView?idteam=0000000C&mode=3")
opts = re.findall(r'<option value="([0-9A-F]{8})"[^>]*>([^<]*)</option>', tp)
log.write("ESAKE opts: " + repr(opts[:80]) + "\n")
for v, label in opts:
    if re.search(r"2010|1999|1996|1997|1998", label):
        get(f"esake_rank_{v}.html", f"https://www.esake.gr/el/action/EsakeRanking?idchampionship={v}")
        get(f"esake_team_{v}.html", f"https://www.esake.gr/el/action/EsaketeamView?idteam=0000000C&mode=3&idchampionship={v}")
# ESPN standings με σεζόν
get("espn_st_2015.json", "https://site.api.espn.com/apis/v2/sports/soccer/gre.1/standings?season=2015")
get("espn_st_2005.json", "https://site.api.espn.com/apis/v2/sports/soccer/gre.1/standings?season=2005")
# ΟΧΕ χάντμπολ 2014-15
get("oxe_home.html", "http://statistics.handball.org.gr/gr/")
log.close()
