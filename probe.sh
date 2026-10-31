#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
node sr.mjs 2>&1 | head -30
curl -sS -m 30 -A "Mozilla/5.0" "https://hvl-web.dataproject.com/MainLiveScore.aspx" | grep -oE 'id="HF_MatchesList" value="[^"]*"'
