"""Βαθμολογίες για κάθε τμήμα του ΠΑΟΚ.

Κάθε συνάρτηση επιστρέφει λίστα πινάκων με τη μορφή
    {"title", "url", "columns": [...], "rows": [{"pos", "team", "logo", "paok", "cells": [...]}]}
Όπου υπάρχει επίσημη βαθμολογία τη διαβάζουμε από την πηγή· για το βόλεϊ ανδρών και το
EuroCup την υπολογίζουμε από τα αποτελέσματα, γιατί δεν δημοσιεύεται σε αναγνώσιμη μορφή.
Για το βόλεϊ γυναικών η πηγή δείχνει ακόμα βαθμούς με το παλιό σύστημα (3-2-1-0), οπότε
οι βαθμοί και η σειρά υπολογίζονται με τον νέο κανονισμό (βλ. volley_women_order).
"""
from __future__ import annotations

import json
import re

from build_calendars import (
    DATAPROJECT, EPO, FOOTBALL_NAMES, HANDBALL, _parse_dataproject, absolute, basket_name, clean, fetch,
    fetch_until,
    is_paok, latin_title, plain, season_start_year, tidy_name, volley_rows,
)


def table(title: str, url: str, columns: list[str], rows: list[tuple]) -> dict:
    """rows: (θέση, ομάδα, σήμα, [κελιά])"""
    return {
        "title": title, "url": url, "columns": columns,
        "rows": [{"pos": pos, "team": PAOK_NAME if is_paok(team) else team, "logo": logo,
                  "paok": is_paok(team), "cells": [str(c) for c in cells]}
                 for pos, team, logo, cells in rows],
    }


PAOK_NAME = "ΠΑΟΚ"


def html_tables(page: str, base: str) -> list[list[tuple[list[str], list[str]]]]:
    """Όλοι οι πίνακες της σελίδας: για κάθε γραμμή (κείμενα κελιών, εικόνες κελιών)."""
    out = []
    for t in re.findall(r"<table[^>]*>(.*?)</table>", page, re.S):
        rows = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
            cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)
            texts = [clean(c) for c in cells]
            imgs = [absolute(base, m) for c in cells for m in
                    re.findall(r'<img[^>]+(?:data-twic-src|src)=["\']([^"\']+)["\']', c)]
            rows.append((texts, imgs))
        out.append(rows)
    return out


def _num(text: str) -> int:
    m = re.search(r"-?\d+", text or "")
    return int(m.group()) if m else 0


# ---------------------------------------------------------------- ποδόσφαιρο

def football() -> list[dict]:
    url = "https://site.api.espn.com/apis/v2/sports/soccer/gre.1/standings"
    data = json.loads(fetch(url))
    child = data["children"][0]
    rows = []
    for e in child["standings"]["entries"]:
        st = {s["name"]: s.get("displayValue", "") for s in e["stats"]}
        team = e["team"]
        name = FOOTBALL_NAMES.get(team["displayName"], team["displayName"])
        logo = next((l["href"] for l in team.get("logos", []) if "dark" not in l.get("rel", [])), "")
        rows.append((_num(st.get("rank")), name, logo, [
            st.get("gamesPlayed"), st.get("wins"), st.get("ties"), st.get("losses"),
            f'{st.get("pointsFor")}-{st.get("pointsAgainst")}', st.get("points")]))
    rows.sort(key=lambda r: r[0])
    return [table("Super League", "https://www.espn.com/soccer/standings/_/league/gre.1",
                  ["Αγ", "Ν", "Ι", "Η", "Γκολ", "Β"], rows)]


def football_women() -> list[dict]:
    url = f"{EPO}/el/competition/6/matches"
    page = fetch(url)
    m = re.search(r'<table class="ranking-table">(.*?)</table>', page, re.S)
    if not m:
        raise RuntimeError("Δεν βρέθηκε βαθμολογία στην ΕΠΟ")
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", m.group(1), re.S):
        cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) < 9:
            continue
        logo = re.search(r'<img[^>]+src="([^"]+)"', tr)
        pos, team, pts, gp, w, d, l, gf, ga = cells[:9]
        rows.append((_num(pos), tidy_name(team), absolute(EPO, logo.group(1)) if logo else "",
                     [gp, w, d, l, f"{gf}-{ga}", pts]))
    return [table("Α' Εθνική Γυναικών", url, ["Αγ", "Ν", "Ι", "Η", "Γκολ", "Β"], rows)]


# ---------------------------------------------------------------- μπάσκετ

def basketball() -> list[dict]:
    url = "https://www.esake.gr/el/action/EsakeRanking"
    tables = html_tables(fetch(url), "https://www.esake.gr/")
    rows = []
    for texts, imgs in tables[0][1:]:
        if len(texts) < 7:
            continue
        m = re.match(r"(\d+)\s*(.*)", texts[0])
        if not m:
            continue
        rows.append((int(m.group(1)), basket_name(m.group(2)), imgs[0] if imgs else "",
                     [texts[2], texts[3].replace(" ", ""), texts[-1], texts[1]]))
    out = [table("Basket League", url, ["Αγ", "Ν-Η", "Διαφ", "Β"], rows)]
    out += eurocup()
    return out


def eurocup() -> list[dict]:
    """Βαθμολογία ομίλου του ΠΑΟΚ, υπολογισμένη από τα αποτελέσματα."""
    season = f"U{season_start_year()}"
    data = json.loads(fetch(f"https://api-live.euroleague.net/v2/competitions/U/seasons/{season}/games"))
    games = data.get("data", data) if isinstance(data, dict) else data
    rs = [g for g in games if (g.get("phaseType") or {}).get("code") == "RS"]
    group = next(((g.get("group") or {}).get("name") for g in rs
                  if "PAOK" in (g["local"]["club"]["name"] + g["road"]["club"]["name"]).upper()), None)
    if not group:
        return []
    teams: dict[str, dict] = {}
    for g in rs:
        if (g.get("group") or {}).get("name") != group:
            continue
        for side in ("local", "road"):
            c = g[side]["club"]
            name = PAOK_NAME if "PAOK" in c["name"].upper() else latin_title(c.get("editorialName") or c["name"])
            teams.setdefault(name, {"logo": (c.get("images") or {}).get("crest", ""), "w": 0, "l": 0, "pf": 0, "pa": 0})
        if not g.get("played"):
            continue
        a, b = g["local"], g["road"]
        for me, other in ((a, b), (b, a)):
            c = me["club"]
            name = PAOK_NAME if "PAOK" in c["name"].upper() else latin_title(c.get("editorialName") or c["name"])
            t = teams[name]
            t["pf"] += me.get("score", 0)
            t["pa"] += other.get("score", 0)
            t["w" if me.get("score", 0) > other.get("score", 0) else "l"] += 1
    order = sorted(teams.items(), key=lambda kv: (-kv[1]["w"], kv[1]["l"], -(kv[1]["pf"] - kv[1]["pa"])))
    rows = [(i + 1, name, t["logo"], [t["w"] + t["l"], t["w"], t["l"], f'{t["pf"] - t["pa"]:+d}'])
            for i, (name, t) in enumerate(order)]
    title = "EuroCup – " + group.replace("Group", "Όμιλος")
    return [table(title, "https://www.eurocupbasketball.com/standings", ["Αγ", "Ν", "Η", "Διαφ"], rows)]


def basketball_women() -> list[dict]:
    url = "https://www.basket.gr/wbl1/standings/"
    tables = html_tables(fetch_until(url, lambda p: "<table" in p and "ΠΑΟΚ" in p), url)
    rows = []
    for texts, imgs in tables[0][1:]:
        if len(texts) < 8:
            continue
        pos, _, team, pts, gp, wl, _, diff = texts[:8]
        rows.append((_num(pos), tidy_name(team), imgs[0] if imgs else "", [gp, wl, diff, pts]))
    return [table("Women's Basketball League 1", url, ["Αγ", "Ν-Η", "Διαφ", "Β"], rows)]


# ---------------------------------------------------------------- βόλεϊ

def volley() -> list[dict]:
    """Volley League: υπολογισμός από τα αποτελέσματα (3-0/3-1: 3 βαθμοί, 3-2: 2 και 1)."""
    url, rows_all = volley_rows()
    teams: dict[str, dict] = {}
    for r in rows_all:
        if "αγωνιστική" not in r["heading"].lower():
            continue
        for side in ("home", "away"):
            teams.setdefault(r[side], {"logo": r[side + "_logo"], "p": 0, "w": 0, "l": 0, "sw": 0, "sl": 0})
        m = re.fullmatch(r"(\d)-(\d)", r["score"])
        if not m or max(int(m.group(1)), int(m.group(2))) != 3:
            continue
        hs, as_ = int(m.group(1)), int(m.group(2))
        for me, mine, theirs in ((r["home"], hs, as_), (r["away"], as_, hs)):
            t = teams[me]
            t["sw"] += mine
            t["sl"] += theirs
            won = mine == 3
            t["w" if won else "l"] += 1
            t["p"] += (3 if theirs <= 1 else 2) if won else (1 if mine == 2 else 0)
    order = sorted(teams.items(), key=lambda kv: (-kv[1]["p"], -kv[1]["w"], -(kv[1]["sw"] - kv[1]["sl"])))
    rows = [(i + 1, tidy_name(name), t["logo"], [t["w"] + t["l"], t["w"], t["l"], f'{t["sw"]}-{t["sl"]}', t["p"]])
            for i, (name, t) in enumerate(order)]
    return [table("Volley League", url, ["Αγ", "Ν", "Η", "Σετ", "Β"], rows)]


def num(x: str, default: float = 0.0) -> float:
    try:
        return float(str(x).replace(",", "."))
    except ValueError:
        return default


def volley_women_order(teams: list[dict], results: list[tuple[str, str, int, int]]) -> list[dict]:
    """Σειρά κατάταξης της Volley League Γυναικών (κανονισμός ΕΟΠΕ από τη σεζόν 2026-27).

    Βαθμοί: 2 η νίκη, 1 η ήττα, 0 ο μηδενισμός (ανεξάρτητα από τα σετ).
    Σε ισοβαθμία: 1) τα μεταξύ τους αποτελέσματα με βαθμούς κατά σετ (3-0/3-1: 3, 3-2: 2, 2-3: 1,
    1-3/0-3: 0), 2) οι ίδιοι βαθμοί σε όλους τους αγώνες, 3) λόγος σετ, 4) λόγος πόντων.
    teams: {"team", "points", "results_points", "set_ratio", "point_ratio", …}
    results: (γηπεδούχος, φιλοξενούμενος, σετ γηπεδούχου, σετ φιλοξενούμενου)
    """
    def result_points(own: int, other: int) -> int:
        return (3 if other <= 1 else 2) if own == 3 else (1 if own == 2 else 0)

    by_points: dict[float, list[dict]] = {}
    for t in teams:
        by_points.setdefault(t["points"], []).append(t)
    ordered = []
    for pts in sorted(by_points, reverse=True):
        group = by_points[pts]
        names = {t["team"] for t in group}
        h2h = {n: 0 for n in names}
        for home, away, a, b in results:
            if home in names and away in names and home != away:
                h2h[home] += result_points(a, b)
                h2h[away] += result_points(b, a)
        ordered += sorted(group, key=lambda t: (-h2h[t["team"]], -t["results_points"],
                                                -t["set_ratio"], -t["point_ratio"]))
    return ordered


def volley_women() -> list[dict]:
    y = season_start_year()
    season = f"{y}-{str(y + 1)[-2:]}"
    home_page = fetch(DATAPROJECT + "MainHome.aspx")
    out = []
    for cid, label in re.findall(r'href="CompetitionHome\.aspx\?ID=(\d+)"[^>]*>(.*?)</a>', home_page, re.S):
        name = plain(clean(label))
        if season not in name or "WOMEN" not in name or "CUP" in name:
            continue
        matches = fetch(f"{DATAPROJECT}CompetitionMatches.aspx?ID={cid}")
        pids = sorted(set(re.findall(rf"CompetitionMatches\.aspx\?ID={cid}&amp;PID=(\d+)", matches)))
        for pid in pids[:1]:
            url = f"{DATAPROJECT}CompetitionStandings.aspx?ID={cid}&PID={pid}"
            page = fetch(url)
            teams = []
            parts = re.split(r'<tr class="RG_Standing_Main[^"]*"[^>]*>', page)[1:]
            for part in parts:
                part = part.split("</tbody>", 1)[0]
                f: dict[str, str] = {}
                for k, v in re.findall(r'<span id="([A-Za-z0-9]+)"[^>]*>([^<]*)</span>', part):
                    f.setdefault(k, v.strip())
                if "TeamName" not in f:
                    continue
                logo = re.search(r'id="TeamLogo"[^>]*url\((?:&quot;|["\'])?([^"&)]+)', part)
                won, lost = int(num(f.get("WonMatches"))), int(num(f.get("LostMatches")))
                forfeits = int(num(f.get("Penalty"), 0)) if f.get("Penalty", "-").strip("-").strip() else 0
                teams.append({
                    "team": tidy_name(f["TeamName"]), "logo": logo.group(1) if logo else "",
                    "points": 2 * won + lost - forfeits, "results_points": num(f.get("Points")),
                    "set_ratio": num(f.get("QuotSet")), "point_ratio": num(f.get("QuotPoints")),
                    "cells": [f.get("MatchesPlayed", ""), str(won), str(lost),
                              f'{f.get("SetsWon", "")}-{f.get("SetsLost", "")}'],
                })
            if not teams:
                continue
            # Αποτελέσματα της κανονικής περιόδου, για τα μεταξύ τους σε ισοβαθμία.
            phase = fetch(f"{DATAPROJECT}CompetitionMatches.aspx?ID={cid}&PID={pid}")
            results = []
            for m in _parse_dataproject(phase, "volley-women", cid, "", only_paok=False):
                if m.score:
                    a, b = (int(x) for x in m.score.split("-"))
                    results.append((m.home, m.away, a, b))
            rows = [(i + 1, t["team"], t["logo"], t["cells"] + [f'{t["points"]:g}'])
                    for i, t in enumerate(volley_women_order(teams, results))]
            out.append(table("Volley League Γυναικών", url, ["Αγ", "Ν", "Η", "Σετ", "Β"], rows))
        if out:
            break
    if not out:
        raise RuntimeError("Δεν βρέθηκε βαθμολογία βόλεϊ γυναικών")
    return out


# ---------------------------------------------------------------- χάντμπολ

def handball(women: bool) -> list[dict]:
    season_id = str(season_start_year() + 1)
    form = fetch(HANDBALL + "scorestats.asp", encoding="cp1253")
    out = []
    for block in form.split("var ap = root.findchild(")[1:]:
        nodes = re.findall(r'new cri\((\d+),"([^"]*)"\)', block)
        if len(nodes) < 3 or nodes[0][0] != season_id:
            continue
        cat_name = plain(nodes[1][1])
        if ("ΓΥΝΑΙΚ" in cat_name) != women:
            continue
        if not ("PREMIER" in cat_name or re.match(r"^[AΑ]1\b", cat_name)):
            continue
        data = [("obj", n[0]) for n in nodes[:4]] + [("agper", "x"), ("category", "x"), ("diorg", "x"),
                                                     ("group", "x"), ("B1", "x")]
        page = fetch(HANDBALL + "scorestatsres.asp", data=data, encoding="cp1253")
        # Στήλες: α/α, Σωματείο, Βαθ., Αγ., Υπέρ, Κατά, Διαφ., εντός Ν-Ι-Η, εκτός Ν-Ι-Η, σύνολο Ν-Ι-Η, Μηδ.
        rows = []
        for t in html_tables(page, HANDBALL):
            for texts, _ in t:
                if len(texts) >= 16 and texts[0].isdigit() and texts[1]:
                    rows.append((int(texts[0]), tidy_name(texts[1]), "",
                                 [texts[3], texts[13], texts[14], texts[15], f"{texts[4]}-{texts[5]}", texts[2]]))
        if rows:
            title = "Handball Premier" if "PREMIER" in cat_name else ("Α1 Γυναικών" if women else "Α1 Ανδρών")
            out.append(table(title, HANDBALL + "scorestats.asp", ["Αγ", "Ν", "Ι", "Η", "Γκολ", "Β"], rows))
        if out:
            break
    if not out:
        raise RuntimeError("Δεν βρέθηκε βαθμολογία χάντμπολ")
    return out


# ---------------------------------------------------------------- πόλο

def waterpolo(women: bool) -> list[dict]:
    yy = season_start_year() % 100
    slug = f"wpl-{'women-' if women else ''}{yy:02d}-{(yy + 1) % 100:02d}"
    url = f"https://waterpololeague.gr/championship/{slug}/standings"
    tables = html_tables(fetch(url), url)
    rows = []
    for texts, imgs in tables[0][1:]:
        if len(texts) < 10:
            continue
        pos, team, pts, gp, w, d, l, gf, ga = texts[:9]
        rows.append((_num(pos), tidy_name(team), imgs[0] if imgs else "", [gp, w, d, l, f"{gf}-{ga}", pts]))
    title = "Water Polo League" + (" Γυναικών" if women else "")
    return [table(title, url, ["Αγ", "Ν", "Ι", "Η", "Γκολ", "Β"], rows)]


STANDINGS = {
    "football": football,
    "football-women": football_women,
    "basketball": basketball,
    "basketball-women": basketball_women,
    "volley": volley,
    "volley-women": volley_women,
    "handball": lambda: handball(False),
    "handball-women": lambda: handball(True),
    "waterpolo": lambda: waterpolo(False),
    "waterpolo-women": lambda: waterpolo(True),
}
