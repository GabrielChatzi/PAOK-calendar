#!/usr/bin/env bash
set -u
mkdir -p out
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
n=0
get(){ n=$((n+1)); f="$(printf %02d $n)_$2"; echo "== $1 -> $f"; curl -sSL -A "$UA" -H "Accept-Language: el,en" --max-time 40 -o "out/$f" -w "%{http_code} %{size_download} %{url_effective}\n" "$1" || echo FAIL; }
for h in eope-web.dataproject.com hvf-web.dataproject.com esap-web.dataproject.com gre-web.dataproject.com; do get "https://$h/" "dp_$h.html"; get "https://$h/MainHome.aspx" "dp_main_$h.html"; done
get "https://www.cev.eu/club/volleyball-champions-league/women/" cev_w.html
