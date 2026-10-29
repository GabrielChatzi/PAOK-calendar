#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 40 -A "$UA" "https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?ID=1801" -o /tmp/o.html -w "%{http_code} %{url_effective}\n"; wc -c /tmp/o.html
grep -oE '<title>[^<]*' /tmp/o.html; grep -oE 'CompetitionView\.aspx\?ID=[0-9]+[^"]*"[^>]*>[^<]*' /tmp/o.html | sort -u | head -30
grep -oiE '.{0,120}(Galati|PAOK).{0,200}' /tmp/o.html | head
for id in 1850 1880 1900 1920; do t=$(curl -sSL -m 30 -A "$UA" "https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?ID=$id" | grep -oE '<title>[^<]*|<h1[^>]*>[^<]*' | head -2 | tr '\n' ' '); echo "$id $t"; done
