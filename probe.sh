#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import build_calendars as b, datetime as dt
for name, fn in [("basket", b.basket_league_matches), ("volley", b.volley_matches),
                 ("handball-women", lambda: b.handball_matches("handball-women")), ("wbl1", b.wbl1_matches)]:
    try:
        for m in fn():
            if m.day == dt.date(2026, 10, 31): print(name, m.home, "-", m.away, repr(m.score), m.uid, m.url)
    except Exception as e: print(name, "ERR", e)
PY
