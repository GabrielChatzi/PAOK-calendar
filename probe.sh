#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
curl -sSL -A "Mozilla/5.0" "https://eope-web.dataproject.com/CompetitionStandings.aspx?ID=19&PID=20" -o /tmp/st.html
grep -oiE '.{0,120}standing.{0,160}' /tmp/st.html | head -20
echo ----
grep -oiE '(src|href)="[^"]*\.(aspx|ashx|js|asmx)[^"]*"' /tmp/st.html | sort -u | head -40
echo ----; grep -oiE '[A-Za-z]+\.(asmx|ashx|svc)/[A-Za-z]+' /tmp/st.html | sort -u
echo ---- women phases; curl -sSL -A "Mozilla/5.0" "https://eope-web.dataproject.com/CompetitionMatches.aspx?ID=19" | grep -oiE 'PID=[0-9]+[^>]{0,80}>[^<]{0,60}' | sort -u | head
