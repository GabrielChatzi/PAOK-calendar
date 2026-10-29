#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import standings, build_calendars as bc, re
for t in standings.volley_women():
    print(t["title"], t["url"])
    for r in t["rows"]: print("  ", r["pos"], r["team"], r["cells"])
# results used
cid = re.search(r"ID=(\d+)&PID=(\d+)", t["url"])
page = bc.fetch(f"{bc.DATAPROJECT}CompetitionMatches.aspx?ID={cid.group(1)}&PID={cid.group(2)}")
for m in bc._parse_dataproject(page, "volley-women", cid.group(1), "", only_paok=False):
    if m.score: print("   R", m.day, m.home, m.score, m.away)
PY
