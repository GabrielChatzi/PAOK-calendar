#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 -c "
import build_calendars as bc
for m in bc.ehf_matches('handball-women'): print(m.day, m.home, m.away, m.score)"
