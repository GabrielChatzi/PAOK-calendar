#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import standings
for k in ("football", "waterpolo-women", "waterpolo"):
    for t in standings.STANDINGS[k]():
        print(k, "|", t["title"], "|", len(t["rows"]), "rows |", [(r["pos"], r["team"], r["cells"]) for r in t["rows"]][:4])
import club, datetime as dt
for e in club.program_entries(dt.date(2026,11,3)): print("prog", e["day"], e["section"], e["home"], "-", e["away"], "|", e["channel"])
PY
