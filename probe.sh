#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
python3 -c "
import build_calendars as bc
try: print(len(bc.wbl1_matches()))
except Exception as e: print('ERR', e)"
curl -sSL -m 60 -A "$UA" -o /tmp/w.html -w "%{http_code} %{url_effective} %{size_download}\n" "https://www.basket.gr/wbl1/"
grep -oiE '.{0,120}(ΠΑΟΚ|PAOK).{0,120}' /tmp/w.html | head -5
head -c 600 /tmp/w.html
