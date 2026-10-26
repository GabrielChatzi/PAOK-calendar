#!/usr/bin/env bash
set -u
mkdir -p out
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
n=0
get(){ n=$((n+1)); f="$(printf %02d $n)_$2"; echo "== $1 -> $f"; curl -sSL -A "$UA" -H "Accept-Language: el,en" --max-time 40 -o "out/$f" -w "%{http_code} %{size_download} %{url_effective}\n" "$1" || echo FAIL; }
get "https://www.basket.gr/wbl1/schedule/" wbl1_schedule.html
get "https://waterpololeague.gr/championship/wpl-26-27/fixtures" wpl_men.html
get "https://waterpololeague.gr/championship/wpl-women-26-27/fixtures" wpl_women.html
get "https://www.epo.gr/el/competition/38/matches" epo_wcup_matches.html
