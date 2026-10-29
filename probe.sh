#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sS -m 40 -A "$UA" "https://ehfec.eurohandball.com/umbraco/api/competitionmatchesapi/GetInitMatches?contentId=138859&competitionId=0NO-qzR3XKKIL4ING3vbOA" -o docs/ec.json
curl -sS -m 40 -A "$UA" "https://ehfel.eurohandball.com/umbraco/api/competitionmatchesapi/GetInitMatches?contentId=138827&competitionId=1Mk4is0UZJOoUlO9RHsR4w" -o docs/elw.json
curl -sSL -m 40 -A "$UA" "https://ehfel.eurohandball.com/women/2026-27/matches/" -o docs/elw.html
grep -oE '.{0,200}(competitionId|contentId|data-id|138827).{0,200}' docs/elw.html | head -8
