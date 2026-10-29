#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import time, build_calendars as bc
for label, fn in [("CEV volley", lambda: bc.cev_matches("volley")), ("CEV volley-women", lambda: bc.cev_matches("volley-women")),
                  ("EHF handball", lambda: bc.ehf_matches("handball")), ("EHF handball-women", lambda: bc.ehf_matches("handball-women")),
                  ("UEFA women", bc.football_women_europe), ("EA waterpolo-women", lambda: bc.european_waterpolo_matches("waterpolo-women"))]:
    t = time.time()
    try:
        ms = fn()
    except Exception as e:
        import traceback; traceback.print_exc(); print(label, "ERR", e); continue
    print(f"## {label}: {len(ms)} ({time.time()-t:.1f}s, fetched {len(bc._FETCHED)})")
    for m in sorted(ms, key=lambda m: m.day): print("  ", m.day, m.time, m.home, "–", m.away, "|", m.competition, "|", m.round, "|", m.venue, "|", m.score, "|", m.uid)
PY
