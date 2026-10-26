#!/usr/bin/env bash
set -u
mkdir -p out
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
n=0
get(){ n=$((n+1)); f="$(printf %02d $n)_$2"; echo "== $1 -> $f"; curl -sSL -A "$UA" -H "Accept-Language: el,en" --max-time 40 -o "out/$f" -w "%{http_code} %{size_download} %{url_effective}\n" "$1" || echo FAIL; }
get "https://www.volleyball.gr/" eope.html
get "https://www.basket.gr/" eok.html
get "https://www.handball.org.gr/" ohe.html
get "https://www.kolymbisi.gr/" koe.html
get "https://www.epo.gr/" epo.html
get "https://www.paok.gr/" paokgr.html
get "https://www.paokac.gr/" paokac.html
get "https://www.paokvolley.gr/" paokvolley.html
get "https://www.sofascore.com/api/v1/search/all?q=PAOK" sofa_www.json
get "https://api.sofascore.app/api/v1/search/all?q=PAOK" sofa_app.json
get "https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t=PAOK" tsdb.json
get "https://site.api.espn.com/apis/site/v2/sports/soccer/gre.w.1/teams" espn_grew.json
