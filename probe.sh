#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 60 -A "$UA" "https://www.volleyleague.gr/index.php/news/league-cup/item/13616-novibet-league-cup-nikos-samaras-2026-27-to-panorama" -o docs/pan.html; wc -c docs/pan.html
python3 - <<'PY'
import re, html
t = open("docs/pan.html", encoding="utf-8", errors="replace").read()
i = t.find("itemFullText"); body = t[i:i+20000]
x = re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<(?!/?(tr|td|p|br|h\d)\b)[^>]+>", "", body)))
print(x[:5000])
PY
