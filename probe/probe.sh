#!/usr/bin/env bash
# Temporary: fetch candidate sources so their real structure can be inspected.
set -u
mkdir -p out
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
get(){ echo "== $1 -> $2"; curl -sSL -A "$UA" --max-time 40 -o "out/$2" -w "%{http_code} %{size_download}\n" "$1" || echo FAIL; }
get "https://www.volleyleague.gr/index.php/season/2026-27/regular-season-results-statistics" volley.html
get "https://site.api.espn.com/apis/site/v2/sports/soccer/gre.1/teams" espn_gre1_teams.json
get "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/clubs" el_clubs.json
get "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games" el_games.json
get "https://www.esake.gr/" esake_home.html
get "https://www.esake.gr/el/action/EsakeResults" esake_results.html
get "https://api.sofascore.com/api/v1/search/all?q=PAOK" sofa_search.json
get "https://www.paokbc.gr/el/" paokbc.html
