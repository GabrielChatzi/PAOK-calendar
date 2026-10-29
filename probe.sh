#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 60 -A "$UA" "https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?ID=1949&PID=3546" -o docs/cevmain.html
curl -sSL -m 60 -A "$UA" "https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?ID=1801&PID=$(curl -sSL -m 60 -A "$UA" 'https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?ID=1801' | grep -oE 'PID=[0-9]+' | head -1 | cut -d= -f2)" -o docs/cevold26.html
wc -c docs/*.html
