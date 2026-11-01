#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import datetime as dt, club, build_calendars as b, html
day=dt.date(2026,11,1)
ms=[b.Match(section="football-women",uid="a",day=day,time=dt.time(14,0),home="ΠΑΣ ΠΥΡΓΟΣ",away="ΠΑΟΚ",paok_home=False),
    b.Match(section="futsal",uid="b",day=day,time=dt.time(14,0),home="ΠΑΟΚ",away="ΚΟΡΥΔΑΛΛΟΥ ΑΟΔ",paok_home=True),
    b.Match(section="basketball-women",uid="c",day=day,time=dt.time(16,0),home="ΑΕΟ ΠΡΩΤΕΑΣ ΒΟΥΛΑΣ",away="ΠΑΟΚ",paok_home=False)]
now=dt.datetime(2026,11,1,23,0,tzinfo=b.ATHENS)
for m in ms:
    club.results(m.section,[m],now=now); print("RESULT", m.section, repr(m.score))
print("--- όλες οι αναρτήσεις (ως αν ο ΠΑΟΚ ήταν γηπεδούχος)")
for p in club.recent_posts():
    t=html.unescape(p["title"]["rendered"])
    print(p["date"][:16], club.score_from_post(t, b.clean(p["content"]["rendered"]), "ΠΑΟΚ", "X", True), "|", t[:70])
PY
