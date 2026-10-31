#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
S=https://paokalendar.vercel.app
echo "selftest: $(curl -sS "$S/api/health?selftest=1")"
SUB='{"endpoint":"https://fcm.googleapis.com/fcm/send/claude-probe-test","keys":{"p256dh":"BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM","auth":"tBHItJI5svbpez7KI4CCXg"}}'
echo "save: $(curl -sS -X POST "$S/api/subscribe" -H 'Content-Type: application/json' -d "{\"subscription\":$SUB,\"topics\":[\"s:volley:live\"]}")"
echo "check: $(curl -sS -X POST "$S/api/subscribe" -H 'Content-Type: application/json' -d "{\"subscription\":$SUB,\"action\":\"check\"}")"
echo "delete: $(curl -sS -X DELETE "$S/api/subscribe" -H 'Content-Type: application/json' -d "{\"subscription\":$SUB}")"
curl -sS -D /tmp/h "$S/matches.json" -o /tmp/m.json; grep -iE "^content-type|^x-vercel-cache|^cache-control" /tmp/h; python3 -c "import json; d=json.load(open('/tmp/m.json')); print('matches', len(d['matches']), max(d['updated'].values()))"
curl -sS -D /tmp/h2 "$S/football-home.ics" -o /tmp/f.ics; grep -iE "^content-type" /tmp/h2; head -c 60 /tmp/f.ics; echo
curl -sS -o /dev/null -w "index %{http_code}\n" "$S/"
