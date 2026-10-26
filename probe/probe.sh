#!/usr/bin/env bash
set -u
mkdir -p out
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
get(){ echo "== $1 -> $2"; curl -sSL -A "$UA" --max-time 40 -o "out/$2" -w "%{http_code} %{size_download}\n" "$1" || echo FAIL; }
E=https://site.api.espn.com/apis/site/v2/sports/soccer
for L in gre.1 gre.cup uefa.champions uefa.europa uefa.europa.conf all; do
  get "$E/$L/teams/605/schedule?fixture=true" "espn_${L}_fix.json"
  get "$E/$L/teams/605/schedule" "espn_${L}_res.json"
done
for m in 1 2 3 4 5; do get "https://www.esake.gr/el/action/EsaketeamView?idteam=0000000C&mode=$m" "esake_team_m$m.html"; done
get "https://www.esake.gr/el/action/EsakeResults?mode=1" esake_res_m1.html
get "https://www.esake.gr/el/action/EsakeResults?mode=2" esake_res_m2.html
