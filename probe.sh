#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import datetime as dt, club, build_calendars as b, html
posts = club.get_json("posts?search=%CF%86%CE%B9%CE%BB%CE%B9%CE%BA&per_page=40&_fields=id,date,title,content,link,categories")
club._DATA["posts"] = posts
ents = [e for e in club.announcement_entries(dt.date(2026, 8, 1)) if e["friendly"]]
for e in ents:
    print("ANN", e["day"], e["section"], e["time"], "opp:", e["opponent"], "home:", e["home_flag"], "|", e["title"][:70])
for e in ents:
    m = club.friendly_match(e["section"], e, e["home_flag"], [])
    if not m: print("  no match for", e["title"][:50]); continue
    club.results(e["section"], [m], now=dt.datetime.combine(e["day"], dt.time(23, 0), b.ATHENS))
    print("  MATCH", m.section, m.day, m.time, m.home, "-", m.away, "|", m.competition, "| score:", m.score)
PY
