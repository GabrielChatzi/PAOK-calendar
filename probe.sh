#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import build_calendars as bc, re, collections
page = bc.fetch(f"{bc.DATAPROJECT}CompetitionMatches.aspx?ID=19&PID=20")
key_re = re.compile(r'_RADLIST_Legs_(ctrl\d+)_(?:RADLIST_Matches_(ctrl\d+)_)?([A-Za-z0-9_]+)"')
fields = collections.defaultdict(dict)
for m in re.finditer(r'id="ctl00_Content_Main_\d+_userControl(_RADLIST_Legs_[^"]+")([^>]*)>([^<]*)', page):
    km = key_re.match(m.group(1))
    if not km or km.group(2) is None: continue
    v = re.search(r'value="([^"]*)"', m.group(2))
    fields[(km.group(1), km.group(2))][km.group(3)] = (v.group(1) if v else m.group(3)).strip()
for k, f in sorted(fields.items()):
    if k[0] == "ctrl2": print(k, {a: b for a, b in f.items() if b and not a.startswith("Logo")})
PY
