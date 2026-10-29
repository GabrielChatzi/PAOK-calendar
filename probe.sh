#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import club, datetime as dt
for e in club.entries(): print({k: (str(v) if isinstance(v, (dt.date, dt.time)) else v) for k, v in e.items() if k not in ("link", "title")})
PY
python3 build_calendars.py > build.log 2>&1; echo "exit $?"
grep -E "!|(χωρίς αποστολή)|Έλεγχοι" build.log | cut -c1-220 | head -40
echo "---- checks.md"; cat checks.md 2>/dev/null
rm -rf docs/*.ics; mkdir -p docs; touch docs/.keep
