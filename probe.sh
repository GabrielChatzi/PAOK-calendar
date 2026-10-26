#!/usr/bin/env bash
set -u
mkdir -p docs/p
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
get(){ echo "== $1 -> $2" >> docs/p/log.txt; curl -sSL -A "$UA" -H "Accept-Language: el,en" --max-time 40 -o "docs/p/$2" -w "%{http_code} %{size_download} %{url_effective}\n" "$1" >> docs/p/log.txt 2>&1 || echo FAIL >> docs/p/log.txt; }
get "https://site.api.espn.com/apis/v2/sports/soccer/gre.1/standings" espn_st.json
get "https://www.esake.gr/el/action/EsakeRanking" esake_rank.html
get "https://www.basket.gr/wbl1/standings/" wbl1_st.html
get "https://eope-web.dataproject.com/CompetitionStandings.aspx?ID=19&PID=20" dp_st.html
get "https://eope-web.dataproject.com/CompetitionMatches.aspx?ID=19&PID=20" dp_m.html
get "http://statistics.handball.org.gr/gr/scorestats.asp" hb_st_form.html
get "https://waterpololeague.gr/championship/wpl-26-27/standings" wpl_st.html
get "https://www.epo.gr/el/competition/6/matches" epo6.html
get "https://www.volleyleague.gr/index.php/season/2026-27/regular-season-results-statistics" volley.html
