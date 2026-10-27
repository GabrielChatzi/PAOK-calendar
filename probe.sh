#!/usr/bin/env bash
mkdir -p docs/p
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
ORIGIN="https://paokalendar.vercel.app"
get(){ echo "== $2 <- $1"; curl -sSL -A "$UA" -H "Origin: $ORIGIN" -D "docs/p/$2.h" -o "docs/p/$2" -w "%{http_code} %{size_download}\n" --max-time 40 "$1"; grep -i "^access-control-allow-origin" "docs/p/$2.h" || echo "  (no CORS header)"; }
get "https://site.api.espn.com/apis/site/v2/sports/soccer/gre.1/summary?event=401896740" espn_summary.json
get "https://site.api.espn.com/apis/site/v2/sports/soccer/gre.1/scoreboard" espn_scoreboard.json
get "https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/605/schedule?fixture=true" espn_fix.json
get "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games" el_games.json
CODE=$(python3 -c "
import json;d=json.load(open('docs/p/el_games.json'))['data']
g=[x for x in d if 'PAOK' in (x['local']['club']['name']+x['road']['club']['name']).upper() and x.get('played')]
g.sort(key=lambda x:x['utcDate']); print(g[-1]['gameCode'])")
echo "EuroCup played code: $CODE"
get "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games/$CODE" el_game.json
get "https://live.euroleague.net/api/Header?gamecode=$CODE&seasoncode=U2026" el_header.json
get "https://live.euroleague.net/api/PlayByPlay?gamecode=$CODE&seasoncode=U2026" el_pbp.json
get "https://api-live.euroleague.net/v3/competitions/U/seasons/U2026/games/$CODE/report" el_report.json
get "https://www.esake.gr/el/action/EsakegameView?idgame=BD2162B8&mode=2" esake_pbp.html
get "https://basket.gr/files/live/data/livescore.html" eok_live.html
get "https://eope-web.dataproject.com/LiveScore_adv.aspx?ID=19" dp_live.html
get "https://waterpololeague.gr/fixture/panionios-gss-paok-domus-ergo-2026-10-21" wpl_fixture.html
