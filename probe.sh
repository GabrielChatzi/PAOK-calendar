#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 60 -A "$UA" "https://www-old.cev.eu/Competition-Area/CompetitionTeamDetails.aspx?TeamID=14498&ID=1949" -o /tmp/t.html
grep -oE 'Flags[^"]*' /tmp/t.html | sort | uniq -c | sort -rn | head; grep -oiE '.{0,200}(Country|Nation|Address|City)[^<]{0,40}<.{0,200}' /tmp/t.html | head -5
