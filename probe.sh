#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
for s in "" "?season=2026" "?fixture=true"; do
  echo "== club.friendly $s"
  curl -sS -A "Mozilla/5.0" "https://site.api.espn.com/apis/site/v2/sports/soccer/club.friendly/teams/605/schedule$s" | python3 -c "
import json,sys; d=json.load(sys.stdin)
for e in d.get('events',[]): print(e['date'][:16], e['name'], e['competitions'][0].get('status',{}).get('type',{}).get('name'))" | tail -15
done
