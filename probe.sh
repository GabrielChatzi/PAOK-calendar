#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 60 -A "$UA" "https://eope-web.dataproject.com/CompetitionTeamDetails.aspx?TeamID=118&ID=19" -o /tmp/t.html; wc -c /tmp/t.html
python3 - <<'PY'
import re, html
t = open("/tmp/t.html", encoding="utf-8", errors="replace").read()
x = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S))))
for k in ("MATCH DAY", "Match Day", "/2026", "/2027"):
    i = x.find(k); print(k, i, x[max(0,i-200):i+800] if i >= 0 else "")
print(sorted(set(re.findall(r'href="([A-Za-z]+\.aspx\?[^"]+)"', t)))[:30])
PY
curl -sS -m 30 -o /dev/null -w "volleyball.gr %{http_code}\n" -A "$UA" "https://www.volleyball.gr/" || echo fail
curl -sS -m 30 -o /dev/null -w "volleyball.gr http %{http_code}\n" -A "$UA" "http://www.volleyball.gr/" || echo fail2
