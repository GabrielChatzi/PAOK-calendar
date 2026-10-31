#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
S=https://paokalendar.vercel.app
SUB='{"endpoint":"https://fcm.googleapis.com/fcm/send/claude-probe-test","keys":{"p256dh":"BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM","auth":"tBHItJI5svbpez7KI4CCXg"}}'
curl -sS -X POST "$S/api/subscribe" -H "Content-Type: application/json" -d "{\"subscription\":$SUB,\"topics\":[\"s:volley:live\"]}" -w "  [%{http_code}]"; echo
curl -sS "$S/api/health?topic=s:volley:live"; echo
curl -sS -X DELETE "$S/api/subscribe" -H "Content-Type: application/json" -d "{\"subscription\":$SUB}" -w "  [%{http_code}]"; echo
