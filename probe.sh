#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
for u in https://epssalas.gr/ https://www.epssalas.gr/; do curl -sSL -m 30 -A "$UA" -o docs/eps.html -w "$u %{http_code} %{url_effective} %{size_download}\n" "$u"; done
grep -oE 'href="[^"]+"' docs/eps.html | sort -u | grep -viE "\.(css|js|png|jpg|svg|ico)|facebook|twitter|instagram|youtube" | head -80
