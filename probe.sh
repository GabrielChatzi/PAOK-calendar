#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
B="https://epssalas.gr/wp-json/sportspress/v2"
curl -sS -m 30 -A "$UA" "$B/leagues?per_page=100&_fields=id,name,slug,count" -o docs/leagues.json
curl -sS -m 30 -A "$UA" "$B/seasons?per_page=100&_fields=id,name,slug,count" -o docs/seasons.json
curl -sS -m 30 -A "$UA" "$B/teams?search=%CE%A0%CE%91%CE%9F%CE%9A&per_page=20&_fields=id,title,slug,leagues,seasons,featured_media" -o docs/teams.json
curl -sS -m 30 -A "$UA" "$B/tables?per_page=30&_fields=id,title,slug,leagues,seasons" -o docs/tables.json
curl -sS -m 30 -A "$UA" "$B/events?per_page=3&_embed=0" -o docs/ev.json
