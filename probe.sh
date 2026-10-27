#!/usr/bin/env bash
mkdir -p docs/p
curl -sS -o docs/p/espn_summary.json "https://site.api.espn.com/apis/site/v2/sports/soccer/gre.1/summary?event=401896740"
curl -sS -o docs/p/el_header.json "https://live.euroleague.net/api/Header?gamecode=64&seasoncode=U2026"
ls -la docs/p
