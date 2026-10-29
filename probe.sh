#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sS -m 30 -A "$UA" "https://epssalas.gr/wp-json/" | python3 -c "import json,sys; d=json.load(sys.stdin); print([n for n in d.get('namespaces',[])]); print([r for r in d['routes'] if 'sportspress' in r][:40])"
curl -sSL -m 30 -A "$UA" "https://epssalas.gr/calendar/futsal-super-league-2026-27/" -o docs/cal.html; wc -c docs/cal.html
python3 - <<'PY'
import re, html
t = open("docs/cal.html", encoding="utf-8", errors="replace").read()
i = t.find("PAOK") if "PAOK" in t else t.find("ΠΑΟΚ")
print(re.sub(r"\s+", " ", t[max(0,i-2500):i+800]))
print(re.findall(r'class="(sp-[a-z-]+)', t)[:30])
PY
