#!/usr/bin/env bash
set -u
mkdir -p out
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
n=0
get(){ n=$((n+1)); f="$(printf %02d $n)_$2"; echo "== $1 -> $f"; curl -sSL -A "$UA" -H "Accept-Language: el,en" --max-time 40 -o "out/$f" -w "%{http_code} %{size_download} %{url_effective}\n" "$1" || echo FAIL; }
get "http://statistics.handball.org.gr/gr/sportevents.asp" hb_events.html
get "https://www.epo.gr/el/competition/6" epo_women.html
get "https://www.epo.gr/el/competition/38" epo_wcup.html
get "https://www.basket.gr/stats-women/" eok_stats_women.html
get "https://www.basket.gr/kypello-elladas-gynaikon/" eok_wcup.html
curl -sS --http1.1 -L -A "$UA" --max-time 40 -o out/vb_home.html -w "vb %{http_code} %{size_download} %{url_effective}\n" https://volleyball.gr/ || echo FAIL vb
get "https://www.koe.org.gr/" koe1.html
get "https://koe.gr/" koe2.html
get "https://www.waterpolo.gr/" wp.html
get "https://www.kolimvisi.gr/" koe3.html
