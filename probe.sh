#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import datetime as dt, club, build_calendars as b
day=dt.date(2026,11,1)
ms=[b.Match(section="football-women",uid="a",day=day,time=dt.time(14,0),home="ΠΑΣ ΠΥΡΓΟΣ",away="ΠΑΟΚ",paok_home=False),
    b.Match(section="futsal",uid="b",day=day,time=dt.time(14,0),home="ΠΑΟΚ",away="ΚΟΡΥΔΑΛΛΟΥ ΑΟΔ",paok_home=True),
    b.Match(section="basketball-women",uid="c",day=day,time=dt.time(16,0),home="ΑΕΟ ΠΡΩΤΕΑΣ ΒΟΥΛΑΣ",away="ΠΑΟΚ",paok_home=False)]
now=dt.datetime(2026,11,1,23,0,tzinfo=b.ATHENS)
for m in ms:
    club.results(m.section,[m],now=now); print(m.section, repr(m.score))
import html
for p in club.recent_posts()[:12]:
    print(p["date"], html.unescape(p["title"]["rendered"]), "||", b.clean(p["content"]["rendered"])[:260])
PY
