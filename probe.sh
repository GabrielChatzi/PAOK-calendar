#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
echo "== Header"; curl -sS -m 30 -A "Mozilla/5.0 (PAOKalendar live; +https://paokalendar.vercel.app)" -H "Cache-Control: no-cache" "https://live.euroleague.net/api/Header?gamecode=78&seasoncode=U2026" | head -c 1500; echo
echo "== Header (plain UA)"; curl -sS -m 30 -o /dev/null -w "%{http_code}\n" "https://live.euroleague.net/api/Header?gamecode=78&seasoncode=U2026"
echo "== api v2 game"; curl -sS -m 30 "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games/78" | head -c 800; echo
gh run list -R GabrielChatzi/PAOK-calendar --workflow live.yml -L 2
