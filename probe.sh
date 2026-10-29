#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 60 -A "$UA" "https://eope-web.dataproject.com/CompetitionStandings.aspx?ID=19&PID=20" -o /tmp/s.html
python3 - <<'PY'
import re, html
t = open("/tmp/s.html", encoding="utf-8", errors="replace").read()
parts = re.split(r'<tr class="RG_Standing_Main[^"]*"[^>]*>', t)[1:]
for part in parts[:12]:
    part = part.split("</tbody>", 1)[0]
    f = re.findall(r'<span id="([A-Za-z0-9_]+)"[^>]*>([^<]*)</span>', part)
    print([(k, v.strip()) for k, v in f if v.strip()][:40])
hdr = re.findall(r'<th[^>]*>(.*?)</th>', t, re.S)
print([re.sub(r"<[^>]+>|\s+", " ", h).strip() for h in hdr][:40])
i = t.find("RG_Standing_Main"); print(re.sub(r"\s+", " ", t[max(0, i-3000):i])[-2500:])
PY
