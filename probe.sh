#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 60 -A "$UA" "https://www.volleyleague.gr/" -o /tmp/h.html
grep -oiE 'href="[^"]*"[^>]*>[^<]*(cup|καπ|κύπελλ|κυπελλ)[^<]*' /tmp/h.html | sort -u | head -20
grep -oiE 'href="[^"]*(cup|kap|kypel)[^"]*"' /tmp/h.html | sort -u | head -20
curl -sSL -m 60 -A "$UA" "https://www.volleyleague.gr/index.php/season/2026-27/regular-season-results-statistics" -o /tmp/v.html
python3 - <<'PY'
import re
t=open("/tmp/v.html",encoding="utf-8",errors="replace").read()
print(re.findall(r"<h3[^>]*>(.*?)</h3>", t, re.S)[:40])
PY
