#!/usr/bin/env bash
set -u
mkdir -p out
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
n=0
get(){ n=$((n+1)); f="$(printf %02d $n)_$2"; echo "== $1 -> $f"; curl -sSL -A "$UA" -H "Accept-Language: el,en" --max-time 40 -o "out/$f" -w "%{http_code} %{size_download} %{url_effective}\n" "$1" || echo FAIL; }
get "https://www.epo.gr/el/competition/6/matches" epo_women_matches.html
get "https://www.epo.gr/el/competition/5/season/0/stage/0/group/0/matches" epo_cup_matches.html
get "https://www.basket.gr/wbl1/" eok_wbl1.html
get "https://waterpololeague.gr/" wpl.html
get "https://koe.org.gr/sports/water-polo" koe_wp.html
hb(){ n=$((n+1)); f="$(printf %02d $n)_$3"; echo "== handball $1/$2 -> $f"
  curl -sS -A "$UA" --max-time 40 -o "out/$f" -w "%{http_code} %{size_download}\n" \
    --data "obj=2027&obj=$1&obj=201&obj=1&agper=x&category=x&fasi=x&omilos=x&B1=x" \
    http://statistics.handball.org.gr/gr/agperes.asp || echo FAIL; }
hb 201 men hb_men.html
hb 205 women hb_women.html
for u in https://volleyball.gr/ http://volleyball.gr/ https://www.volleyball.gr/index.php; do
  n=$((n+1)); curl -sS --http1.1 -L -A "$UA" --max-time 40 -o "out/$(printf %02d $n)_vb.html" -w "vb $u %{http_code} %{size_download}\n" "$u" || echo "FAIL $u"; done
