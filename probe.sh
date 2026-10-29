#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import build_calendars as bc, urllib.error
orig = bc.fetch
def logged(url, *a, **k):
    try:
        return orig(url, *a, **k)
    except Exception as e:
        print("FAIL", url, e); raise
bc.fetch = logged
for i in range(2):
    try: print(len(bc.ehf_matches("handball-women")))
    except Exception as e: print("ERR", e)
    bc._FETCHED.clear()
PY
