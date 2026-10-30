#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
echo "== ESPN gre leagues"; for lg in gre.cup gre.2 gre.1; do curl -sS -m 20 -o /dev/null -w "$lg %{http_code}\n" "https://site.api.espn.com/apis/site/v2/sports/soccer/$lg/scoreboard?dates=20261028"; done
echo "== EPO match links"; curl -sSL -m 30 -A "$UA" "https://www.epo.gr/el/competition/5/matches" | grep -oiE 'href="[^"]*(match|live|game)[^"]*"' | sort -u | head -8
echo "== Data Project live"; for u in "https://eope-web.dataproject.com/LiveScore.aspx" "https://eope-web.dataproject.com/MainLiveScore.aspx"; do curl -sSL -m 30 -A "$UA" -o /tmp/l.html -w "$u %{http_code} %{size_download}\n" "$u"; grep -oiE '(wss?://|https?://)[^"'"'"' ]*(live|signalr|socket|json)[^"'"'"' ]*' /tmp/l.html | sort -u | head -5; done
echo "== esake live"; curl -sSL -m 30 -A "$UA" "https://www.esake.gr/" | grep -oiE 'https?://[^"'"'"' ]*(live|geniussports|fibalivestats|synergy)[^"'"'"' ]*' | sort -u | head -8
echo "== handball"; curl -sSL -m 30 -A "$UA" "https://statistics.handball.org.gr/" | grep -oiE 'href="[^"]*live[^"]*"' | head -5
echo "== waterpolo"; curl -sSL -m 30 -A "$UA" "https://waterpololeague.gr/" | grep -oiE '(href|src)="[^"]*(live|microplus|score)[^"]*"' | sort -u | head -8
echo "== volleyleague"; curl -sSL -m 30 -A "$UA" "https://www.volleyleague.gr/" | grep -oiE '(href|src)="[^"]*(live|dataproject)[^"]*"' | sort -u | head -8
