#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import build_calendars as bc, re, collections
first = bc.fetch(f"{bc.DATAPROJECT}CompetitionMatches.aspx?ID=19")
pids = sorted(set(re.findall(r"CompetitionMatches\.aspx\?ID=19&amp;PID=(\d+)", first)))
print("pids", pids)
for pid in [None] + pids:
    page = first if pid is None else bc.fetch(f"{bc.DATAPROJECT}CompetitionMatches.aspx?ID=19&PID={pid}")
    ms = bc._parse_dataproject(page, "volley-women", "19", "", only_paok=False)
    print(pid, len(ms), collections.Counter(m.round for m in ms).most_common(30))
    print("   legs in html:", len(re.findall(r"LYR_LegName", page)), "matchday labels:", sorted(set(re.findall(r"MATCH DAY\s*\d+", page, re.I)))[:30])
    print("   other links:", sorted(set(re.findall(r'href="(Competition[A-Za-z]+\.aspx\?[^"]+)"', page)))[:20])
PY
