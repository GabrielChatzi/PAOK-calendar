#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 60 -A "$UA" "https://www-old.cev.eu/Competition-Area/MatchPage.aspx?mID=87546&ID=1949&CID=13348&PID=3546" -o /tmp/m.html
python3 - <<'PY'
import re,html
t=open("/tmp/m.html",encoding="utf-8",errors="replace").read()
print([ (a, html.unescape(b).strip()) for a,b in re.findall(r'<span id="[^"]*_(L[BT]?_?[A-Za-z0-9]+)"[^>]*>([^<]*)</span>', t) if b.strip()][:60])
print(sorted(set(re.findall(r'Flags[^"]*/([A-Z]{3})', t))))
PY
