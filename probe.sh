#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import re, build_calendars as b
from build_calendars import DATAPROJECT, fetch, plain, clean
home = fetch(DATAPROJECT + "MainHome.aspx")
for cid, label in re.findall(r'href="CompetitionHome\.aspx\?ID=(\d+)"[^>]*>(.*?)</a>', home, re.S):
    print(cid, plain(clean(label)))
cid = next((c for c, l in re.findall(r'href="CompetitionHome\.aspx\?ID=(\d+)"[^>]*>(.*?)</a>', home, re.S) if "WOMEN" in plain(clean(l)) and "CUP" not in plain(clean(l))), None)
print("cid", cid)
if cid:
    m = fetch(f"{DATAPROJECT}CompetitionMatches.aspx?ID={cid}")
    pids = sorted(set(re.findall(rf"CompetitionMatches\.aspx\?ID={cid}&amp;PID=(\d+)", m)))
    print("pids", pids)
    for pid in pids:
        page = fetch(f"{DATAPROJECT}CompetitionStandings.aspx?ID={cid}&PID={pid}")
        print(pid, "rows", len(re.findall(r'RG_Standing_Main', page)), "teamnames", len(re.findall(r'id="TeamName"', page)), len(page))
PY
