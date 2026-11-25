#!/usr/bin/env python3
"""Αρχείο σεζόν: οι αγώνες και οι βαθμολογίες κάθε τμήματος, ανά σεζόν (docs/archive/<σεζόν>.json).

Το matches.json και το standings.json έχουν μόνο την τρέχουσα σεζόν. Εδώ κρατιούνται και οι προηγούμενες:

    python3 archive.py                  κάθε ενημέρωση: ό,τι έχει τώρα το matches.json/standings.json μπαίνει
                                        στη σεζόν του (οι αγώνες με το uid, οι βαθμολογίες ολόκληρες)
    python3 archive.py summaries        τελική θέση/κύπελλα ανά σεζόν από τη Wikipedia (wiki_sections.py)
    python3 archive.py standings        βαθμολογίες παλιών σεζόν από τη Wikipedia (wiki_standings.py), όπου λείπουν
    python3 archive.py backfill 2024    μια παλιά σεζόν (2024-25) από τις ίδιες πηγές με το build_calendars
                                        (όσες δίνουν παλιές σεζόν)· τα δεδομένα της σεζόν που υπάρχουν ήδη μένουν
    ONLY=football,basketball python3 archive.py backfill 2024   μόνο κάποια τμήματα

Σεζόν = «2025-26», από τον Ιούλιο ως τον Ιούνιο. Οι βαθμολογίες ενός τμήματος μπαίνουν στη σεζόν του
τελευταίου αγώνα του τμήματος που έχει γίνει (όχι της ημερομηνίας), ώστε τον Ιούλιο, πριν αλλάξουν οι πηγές,
να μη γραφτεί η περσινή βαθμολογία στη νέα σεζόν.

Το docs/archive/index.json λέει ποιες σεζόν υπάρχουν και τι έχει κάθε τμήμα (για τη σελίδα).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import signal
import sys
from pathlib import Path

import build_calendars as bc

ARCHIVE = bc.OUT_DIR / "archive"


def season_of(day: str | dt.date) -> str:
    d = dt.date.fromisoformat(day[:10]) if isinstance(day, str) else day
    y = d.year if d.month >= 7 else d.year - 1  # όχι bc.season_start_year: στο backfill «γυρίζει» στην παλιά σεζόν
    return f"{y}-{(y + 1) % 100:02d}"


def season_label(year: int) -> str:
    return f"{year}-{(year + 1) % 100:02d}"


def load(season: str) -> dict:
    p = ARCHIVE / f"{season}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"season": season, "sections": {}}


def save(data: dict) -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for sec in data["sections"].values():
        sec["matches"].sort(key=lambda m: (m.get("start", ""), m.get("uid", "")))
    bc.write_if_changed(ARCHIVE / f"{data['season']}.json", json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                        ignore=lambda s: json.dumps(json.loads(s), sort_keys=True))


# Ό,τι χρειάζεται η σελίδα του αρχείου· όχι live, στατιστικά κ.λπ. που αλλάζουν ή ζυγίζουν πολύ.
KEEP = ("uid", "nt", "section", "start", "timeKnown", "home", "away", "paokHome", "venue", "competition", "round",
        "score", "periods", "url", "homeLogo", "awayLogo", "postponed", "friendly", "goals", "source")


def slim(m: dict) -> dict:
    return {k: m[k] for k in KEEP if k in m and m[k] not in (None, "", [], {})} | {"paokHome": m.get("paokHome", True)}


def merge_matches(sec: dict, matches: list[dict], replace: bool = True) -> int:
    """Αγώνες στη σεζόν, με το uid. replace: ο νέος αντικαθιστά τον παλιό (από την τρέχουσα ενημέρωση)·
    αλλιώς (παλιές σεζόν) μένει ό,τι υπάρχει. Επιστρέφει πόσοι προστέθηκαν."""
    by = {m["uid"]: m for m in sec.setdefault("matches", [])}
    added = 0
    for m in matches:
        if m["uid"] in by and not replace:
            continue
        if m["uid"] not in by:
            added += 1
        old = by.get(m["uid"], {})
        new = slim(m)
        if old.get("score") and not new.get("score"):  # ένα σκορ δεν χάνεται
            new["score"] = old["score"]
        by[m["uid"]] = new
    sec["matches"] = list(by.values())
    return added


def snapshot() -> None:
    """Η τρέχουσα κατάσταση (matches.json, standings.json) στο αρχείο."""
    data = json.loads((bc.OUT_DIR / "matches.json").read_text(encoding="utf-8"))
    standings = {}
    st_path = bc.OUT_DIR / "standings.json"
    if st_path.exists():
        standings = json.loads(st_path.read_text(encoding="utf-8"))
    now = dt.datetime.now(bc.ATHENS).isoformat(timespec="minutes")
    by_season: dict[str, dict[str, list[dict]]] = {}
    last_played: dict[str, str] = {}
    for m in data.get("matches", []):
        if not m.get("start"):
            continue
        by_season.setdefault(season_of(m["start"]), {}).setdefault(m["section"], []).append(m)
        if m.get("score") and m["start"] > last_played.get(m["section"], ""):
            last_played[m["section"]] = m["start"]
    seasons = set(by_season)
    for key in standings:
        if key in last_played:
            seasons.add(season_of(last_played[key]))
    for season in sorted(seasons):
        arch = load(season)
        for key, ms in by_season.get(season, {}).items():
            merge_matches(arch["sections"].setdefault(key, {}), ms)
        for key, tables in standings.items():
            if tables and key in last_played and season_of(last_played[key]) == season:
                arch["sections"].setdefault(key, {"matches": []})["standings"] = tables
        arch["updated"] = now
        save(arch)
    write_index()


# ---------------------------------------------------------------- παλιές σεζόν

# Βαθμολογίες που ακολουθούν τη σεζόν (δοκιμασμένες με archive.py backfill). Οι υπόλοιπες πηγές δίνουν πάντα
# την τρέχουσα βαθμολογία, που δεν πρέπει να γραφτεί σε παλιά σεζόν.
SEASON_STANDINGS = {"volley", "handball", "handball-women", "futsal", "volley-women", "waterpolo", "waterpolo-women"}


class _Timeout(Exception):
    pass


def _with_timeout(fn, secs: int = 90):
    def boom(*_):
        raise _Timeout(f"πάνω από {secs}″")
    signal.signal(signal.SIGALRM, boom)
    signal.alarm(secs)
    try:
        return fn()
    finally:
        signal.alarm(0)


def backfill(year: int, only: set[str] | None = None) -> list[str]:
    """Μια παλιά σεζόν από τις πηγές: το season_start_year «γυρίζει» στη σεζόν αυτή για όλες τις πηγές.
    Κρατά μόνο αγώνες της σεζόν (κάποιες πηγές δίνουν πάντα την τρέχουσα) και βαθμολογίες μόνο όταν τουλάχιστον
    ένας αγώνας του τμήματος βρέθηκε στη σεζόν. Επιστρέφει γραμμές περίληψης."""
    import standings as st
    season = season_label(year)
    real = bc.season_start_year
    patched = lambda today=None: year  # noqa: E731
    bc.season_start_year, st.season_start_year = patched, patched
    bc.ARCHIVE_YEAR = year
    bc._FETCHED.clear()
    arch = load(season)
    report = []
    try:
        for key, getters in bc.SOURCES.items():
            if only and key not in only:
                continue
            found: list[dict] = []
            errors = []
            for label, get in getters:
                try:
                    found += [m.to_json() for m in (_with_timeout(get) or [])]
                except Exception as e:
                    errors.append(f"{label}: {type(e).__name__}: {str(e)[:100]}")
            mine = [m for m in found if m.get("start") and season_of(m["start"]) == season]
            dropped = len(found) - len(mine)
            tables = []
            if mine and key in st.STANDINGS and key in SEASON_STANDINGS:
                try:
                    tables = _with_timeout(st.STANDINGS[key]) or []
                except Exception as e:
                    errors.append(f"βαθμολογία: {type(e).__name__}: {str(e)[:100]}")
            if mine:
                sec = arch["sections"].setdefault(key, {"matches": []})
                added = merge_matches(sec, mine, replace=False)
                # Η επίσημη βαθμολογία προτιμάται από αυτή της Wikipedia (archive.py standings).
                if tables and (not sec.get("standings") or all(t.get("source") == "wikipedia" for t in sec["standings"])):
                    sec["standings"] = tables
                sec["backfilled"] = True
            else:
                added = 0
            line = (f"{season} {key}: {len(mine)} αγώνες ({added} νέοι, {sum(1 for m in mine if m.get('score'))} με σκορ)"
                    + (f", {dropped} άλλης σεζόν" if dropped else "") + (f", βαθμολογία: {len(tables)} πίνακες" if tables else "")
                    + ("" if not errors else " · " + " | ".join(errors)))
            print(line, flush=True)
            report.append(line)
        if not only or "football" in only:
            report.append(wiki_football(year, arch))
    finally:
        bc.season_start_year, st.season_start_year = real, real
        bc.ARCHIVE_YEAR = None
    if any(sec.get("matches") for sec in arch["sections"].values()):
        arch["updated"] = dt.datetime.now(bc.ATHENS).isoformat(timespec="minutes")
        save(arch)
    write_index()
    return report


def near(day: str, days: set[dt.date], slack: int = 1) -> bool:
    d = dt.date.fromisoformat(day[:10])
    return any(abs((d - x).days) <= slack for x in days)


def wiki_football(year: int, arch: dict) -> str:
    """Ποδόσφαιρο από τη σελίδα σεζόν της Wikipedia (wiki.py): οι αγώνες που δεν υπάρχουν ήδη (ίδια μέρα ±1,
    π.χ. από το ESPN) και η περίληψη της σεζόν (τελική θέση, κύπελλα, πρώτος σκόρερ)."""
    import wiki
    season = season_label(year)
    try:
        matches, summary = wiki.season(year)
    except Exception as e:
        line = f"{season} football (Wikipedia): {type(e).__name__}: {str(e)[:100]}"
        print(line, flush=True)
        return line
    matches = [m for m in matches if season_of(m["start"]) == season]
    sec = arch["sections"].setdefault("football", {"matches": []})
    have = {dt.date.fromisoformat(m["start"][:10]) for m in sec.get("matches", []) if m.get("source") != "wikipedia"}
    fresh = [m for m in matches if not near(m["start"], have)]
    # Οι αγώνες της Wikipedia ξαναγράφονται κάθε φορά (διορθώσεις στη σελίδα)· οι άλλοι μένουν.
    sec["matches"] = [m for m in sec.get("matches", []) if m.get("source") != "wikipedia"]
    merge_matches(sec, fresh)
    if summary:
        sec["summary"] = summary
    if fresh:
        sec["backfilled"] = True
    line = (f"{season} football (Wikipedia): {len(matches)} αγώνες, {len(fresh)} νέοι"
            + (f", {summary.get('league', '')}" if summary else ""))
    print(line, flush=True)
    return line


def summaries(data: dict[str, dict[str, dict]] | None = None) -> None:
    """Περίληψη ανά σεζόν (τελική θέση, κύπελλο, Ευρώπη) από τα άρθρα της Wikipedia (wiki_sections.py), για τα
    τμήματα χωρίς σελίδες σεζόν. Μπαίνει και σε σεζόν χωρίς αγώνες στο αρχείο. Δεν αλλάζει περίληψη από
    σελίδα σεζόν (ποδόσφαιρο, wiki.py)."""
    if data is None:
        import wiki_sections
        data = wiki_sections.summaries()
    by_season: dict[str, dict[str, dict]] = {}
    for key, seasons in data.items():
        for season, info in seasons.items():
            by_season.setdefault(season, {})[key] = info
    for season, secs in sorted(by_season.items()):
        arch = load(season)
        for key, info in secs.items():
            sec = arch["sections"].setdefault(key, {"matches": []})
            old = sec.get("summary") or {}
            if old and "PAOK_FC_season" in str(old.get("source", "")):
                continue
            sec["summary"] = info
        save(arch)
    write_index()


def wiki_standings(keys: list[str] | None = None) -> list[str]:
    """Βαθμολογίες παλιών σεζόν από τη Wikipedia (wiki_standings.py), όπου η σεζόν δεν έχει ήδη βαθμολογία
    από την επίσημη πηγή. Η τρέχουσα σεζόν δεν αγγίζεται."""
    import wiki_standings as ws
    current = bc.season_start_year()
    report = []
    for key in keys or list(ws.SPECS):
        try:
            articles = ws.season_articles(key)
        except Exception as e:
            report.append(f"{key}: αναζήτηση: {e}")
            continue
        got = []
        for year in sorted(articles):
            if year >= current:
                continue
            arch = load(season_label(year))
            sec = arch["sections"].get(key) or {}
            if sec.get("standings") and not all(t.get("source") == "wikipedia" for t in sec["standings"]):
                continue
            try:
                t = ws.season_table(key, year, articles)
            except Exception as e:
                print(f"! {key} {season_label(year)}: {e}", file=sys.stderr)
                continue
            if not t:
                continue
            sec = arch["sections"].setdefault(key, {"matches": []})
            sec["standings"] = [t]
            # Οι παλιοί αγώνες από την αγγλική Wikipedia (wiki.py) έχουν τα ίδια αγγλικά ονόματα με τον πίνακα:
            # ελληνικά ονόματα και σήματα από τον πίνακα της ίδιας σεζόν.
            by_en = {r["en"]: r for r in t["rows"] if r.get("en")}
            for m in sec.get("matches", []):
                for side in ("home", "away"):
                    r = by_en.get(m.get(side, ""))
                    if r:
                        m[side] = r["team"]
                        if r.get("logo") and not m.get(side + "Logo"):
                            m[side + "Logo"] = r["logo"]
            save(arch)
            got.append(season_label(year))
        line = f"{key}: βαθμολογία από Wikipedia σε {len(got)} σεζόν" + (f" ({got[-1]} → {got[0]})" if got else "")
        print(line, flush=True)
        report.append(line)
    write_index()
    return report


def write_index() -> None:
    seasons = []
    for p in sorted(ARCHIVE.glob("*.json"), reverse=True):
        if p.name == "index.json":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        secs = {k: {"matches": len(v.get("matches", [])), "standings": bool(v.get("standings")), "summary": bool(v.get("summary"))}
                for k, v in d["sections"].items() if v.get("matches") or v.get("standings") or v.get("summary")}
        if secs:
            seasons.append({"season": d["season"], "sections": secs})
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    bc.write_if_changed(ARCHIVE / "index.json", json.dumps({"seasons": seasons}, ensure_ascii=False, indent=1) + "\n")


def main(argv: list[str]) -> int:
    if argv[:1] == ["summaries"]:
        summaries()
        return 0
    if argv[:1] == ["standings"]:
        wiki_standings(argv[1:] or None)
        return 0
    if argv[:1] == ["backfill"]:
        only = set(filter(None, os.environ.get("ONLY", "").split(","))) or None
        years = [int(y) for y in argv[1:]]
        for y in years:
            backfill(y, only)
        return 0
    snapshot()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
