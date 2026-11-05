#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
curl -sSL -A "Mozilla/5.0" "https://eope-web.dataproject.com/CompetitionStandings.aspx?ID=19&PID=20" -o docs/st.html
python3 - <<'PY'
import re, html
p = open("docs/st.html", encoding="utf-8", errors="replace").read()
i = p.find("ΠΑΟΚ"); i = i if i >= 0 else p.upper().find("P.A.O.K")
print("paok at", i)
print(re.sub(r"\s+", " ", p[max(0, i - 2500):i + 1500]))
print("ids:", sorted(set(re.findall(r'id="([A-Za-z_]*Team[A-Za-z_]*|[A-Za-z_]*Won[A-Za-z_]*|[A-Za-z_]*Point[A-Za-z_]*)', p)))[:40])
PY
