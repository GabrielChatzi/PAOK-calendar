#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
B="https://epssalas.gr/wp-json/sportspress/v2"
curl -sS -m 30 -A "$UA" "$B/tables/23930?_fields=id,title,data,link" -o docs/table.json
curl -sS -m 60 -A "$UA" "$B/events?leagues=56&seasons=227&per_page=100&page=1&_fields=id,date,link,title,teams,main_results,results,venues,status,day" -o docs/ev1.json
curl -sS -m 60 -A "$UA" "$B/events?leagues=56&seasons=227&per_page=100&page=2&_fields=id,date,link,title,teams,main_results,results,venues,status,day" -o docs/ev2.json
curl -sS -m 30 -A "$UA" "$B/teams?leagues=56&seasons=227&per_page=100&_fields=id,title,featured_media" -o docs/fteams.json
curl -sS -m 30 -A "$UA" "$B/venues?per_page=100&_fields=id,name" -o docs/venues.json
