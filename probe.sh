#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
python3 - <<'PY'
import build_calendars as bc
url, rows = bc.volley_rows()
for r in rows:
    if "αγωνιστική" not in r["heading"].lower(): print(r)
PY
curl -sSL -m 60 -A "$UA" "https://www.volleyleague.gr/index.php/league-cup" -o /tmp/l.html; wc -c /tmp/l.html
python3 - <<'PY'
import re, html
t = open("/tmp/l.html", encoding="utf-8", errors="replace").read()
x = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S))))
i = x.find("ΠΑΟΚ"); print(x[max(0, i-1500):i+800] if i >= 0 else x[:1500])
print(sorted(set(re.findall(r'href="([^"]*league[^"]*)"', t, re.I)))[:20])
PY
