# Ανίχνευση: τι στατιστικά παικτών δίνουν οι πηγές live (ΚΟΕ, European Aquatics, Data Project, EHF, ΕΟΚ).
import json, re, os, urllib.request, urllib.parse
OUT = "docs/probe"; os.makedirs(OUT, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def get(url, headers=None, data=None):
    h = {"User-Agent": UA, "Accept": "*/*"}; h.update(headers or {})
    req = urllib.request.Request(url, headers=h, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, r.read().decode("utf-8-sig", "replace")
    except urllib.error.HTTPError as e: return e.code, e.read().decode("utf-8", "replace")[:500]
    except Exception as e: return 0, str(e)
def save(name, body):
    open(f"{OUT}/{name}", "w", encoding="utf-8").write(body)
def log(*a): print(*a, flush=True)
def scripts(base, html):
    out = []
    for s in re.findall(r'<script[^>]+src="([^"]+)"', html):
        u = urllib.parse.urljoin(base, s); st, js = get(u); out.append((u, js)); log("  js", st, u, len(js))
    return out
def grep_api(name, texts):
    hits = set()
    for t in texts:
        for m in re.finditer(r'["\'`]([^"\'`\s]{0,80}(?:/get/|api/|\.aspx|/stat|player|Player|boxscore|scorer)[^"\'`\s]{0,120})["\'`]', t):
            hits.add(m.group(1))
    save(name, "\n".join(sorted(hits))); log(" ", name, len(hits), "strings")

# ---- ΚΟΕ
KOE = "https://live.koe.org.gr/api-waterpolo/wp"
st, t = get(f"{KOE}/token"); log("koe token", st)
try:
    H = {"x-wp-token": json.loads(t)["token"]}
    for cat, gara in (("ASM", "65"), ("ASF", "66")):
        st, s = get(f"{KOE}/KOE/get/schedulereferee/{cat}/{gara}/*/*/*", H)
        sch = json.loads(s).get("Schedule", [])
        done = [x for x in sch if str(x.get("OraStatus")) == "2" and ("9175200" in (str(x.get("OraTeamCodeA")), str(x.get("OraTeamCodeB"))) or "9176200" in (str(x.get("OraTeamCodeA")), str(x.get("OraTeamCodeB"))) or "PAOK" in json.dumps(x, ensure_ascii=False).upper() or "ΠΑΟΚ" in json.dumps(x, ensure_ascii=False))]
        log("koe", cat, "schedule", len(sch), "paok done", len(done))
        save(f"koe-{cat}-schedule-sample.json", json.dumps(sch[:2], ensure_ascii=False, indent=1))
        if not done: continue
        x = done[-1]
        path = f"{cat}/{gara}/{x['OraTurCode']}/{x.get('OraGruCode', 1)}/{x['OraTeamCodeA']}/{x['OraTeamCodeB']}"
        log("koe match", path)
        for ep in ("resultsDBlikeJSON", "results", "startlist", "startlistDBlikeJSON", "pbp", "pbpDBlikeJSON", "stats", "statistics",
                   "players", "scorers", "teamstats", "playerstats", "boxscore", "matchstats", "lineup", "summary"):
            st, b = get(f"{KOE}/KOE/get/{ep}/{path}", H); log("  koe", ep, st, len(b))
            if st == 200 and len(b) > 20: save(f"koe-{cat}-{ep}.json", b)
except Exception as e: log("koe fail", e)
st, h = get("https://live.koe.org.gr/waterpolo/"); log("koe site", st, len(h)); save("koe-site.html", h)
grep_api("koe-api-strings.txt", [h] + [j for _, j in scripts("https://live.koe.org.gr/waterpolo/", h)])

# ---- European Aquatics
EA = "https://ea.microplustimingservices.com/api/wp"
st, t = get(f"{EA}/site/token"); log("ea token", st)
try:
    H = {"Authorization": "Bearer " + json.loads(t)["data"]["token"]}
    path = "ASF/2/001/3/URA/PAOK"
    for ep in ("results", "startlist", "pbp", "stats", "statistics", "players", "scorers", "teamstats", "playerstats", "boxscore", "summary", "resultsDBlikeJSON"):
        st, b = get(f"{EA}/EACLUB27/get/{ep}/{path}", H); log("  ea", ep, st, len(b))
        if st == 200 and len(b) > 20: save(f"ea-{ep}.json", b)
except Exception as e: log("ea fail", e)
st, h = get("https://ea.microplustimingservices.com/"); log("ea site", st, len(h))
grep_api("ea-api-strings.txt", [h] + [j for _, j in scripts("https://ea.microplustimingservices.com/", h)])

# ---- Data Project (βόλεϊ γυναικών, ίδιο σύστημα με τη Volley League ανδρών)
for name, url in (("dp-eope-762.html", "https://eope-web.dataproject.com/MatchStatistics.aspx?mID=762&ID=19"),
                  ("dp-eope-756.html", "https://eope-web.dataproject.com/MatchStatistics.aspx?mID=756&ID=19"),
                  ("dp-hvl-home.html", "https://hvl-web.dataproject.com/MainHome.aspx"),
                  ("dp-hvl-comps.html", "https://hvl-web.dataproject.com/CompetitionHome.aspx")):
    st, b = get(url); log("dp", name, st, len(b)); save(name, b)
st, b = get("https://hvl-web.dataproject.com/MainHome.aspx")
ids = sorted(set(re.findall(r"CompetitionHome\.aspx\?ID=(\d+)", b))); log("hvl comps", ids)
for cid in ids[:6]:
    st, c = get(f"https://hvl-web.dataproject.com/CompetitionMatches.aspx?ID={cid}")
    ms = re.findall(r"MatchStatistics\.aspx\?mID=(\d+)&(?:amp;)?ID=(\d+)", c)
    log("hvl comp", cid, st, len(c), "matches", len(ms))
    if ms: save(f"dp-hvl-matches-{cid}.html", c)

# ---- EHF
st, b = get("https://www.eurohandball.com/umbraco/api/matchdetailapi/GetMatchDetails?matchId=202711020702028"); log("ehf", st, len(b))
save("ehf-details.json", b)
for ep in ("GetMatchStatistics", "GetPlayerStatistics", "GetMatchPlayerStatistics", "GetLineups", "GetMatchLineups", "GetMatchReport", "GetPlayByPlay"):
    st, b = get(f"https://www.eurohandball.com/umbraco/api/matchdetailapi/{ep}?matchId=202711020702028"); log("  ehf", ep, st, len(b))
    if st == 200 and len(b) > 20: save(f"ehf-{ep}.json", b)
st, h = get("https://www.eurohandball.com/en/matches/202711020702028/RKBoracmtel-ACPAOK/"); log("ehf page", st, len(h)); save("ehf-page.html", h)
grep_api("ehf-api-strings.txt", [h] + [j for u, j in scripts("https://www.eurohandball.com/", h) if "eurohandball" in u])

# ---- ΕΟΚ (μπάσκετ γυναικών)
EOK = "https://apps.basket.gr/iframe/livescores"
st, h = get(f"{EOK}?date=07/11/2026", {"Referer": "https://www.basket.gr/livescore/"}); log("eok", st, len(h)); save("eok-page.html", h)
ids = re.findall(r'match-card-(\d+)', h); log("eok ids", ids[:20])
grep_api("eok-api-strings.txt", [h] + [j for _, j in scripts(EOK, h)])
for i in ids[:30]:
    if "ΠΑΟΚ" in h.split(f'match-card-{i}')[1][:3000]:
        st, b = get(f"{EOK}/get-matches-info?match_ids={i}", {"X-Requested-With": "XMLHttpRequest", "Referer": EOK}); log("eok info", i, st); save(f"eok-info-{i}.json", b)
        for u in (f"https://apps.basket.gr/iframe/livescores/{i}", f"https://apps.basket.gr/matches/{i}", f"https://apps.basket.gr/iframe/match/{i}",
                  f"https://apps.basket.gr/iframe/boxscore/{i}", f"https://www.basket.gr/match/{i}/"):
            st, b = get(u, {"Referer": "https://www.basket.gr/"}); log("  eok", u, st, len(b))
            if st == 200: save("eok-" + re.sub(r"\W+", "_", u[8:])[:60] + ".html", b)
        break
