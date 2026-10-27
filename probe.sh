#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
B=https://paokalendar.vercel.app
for i in $(seq 1 30); do
  h=$(curl -sS -m 30 "$B/api/health"); echo "$(date -u +%T) $h"
  case "$h" in *'"configured":true'*) break;; esac; sleep 10
done
echo "== vapid"; curl -sS -m 30 "$B/api/vapid"; echo
echo "== vapid again (same key?)"; curl -sS -m 30 "$B/api/vapid"; echo
S='{"subscription":{"endpoint":"https://fcm.googleapis.com/fcm/send/probe-test-device","keys":{"p256dh":"BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM","auth":"tBHItJI5svbpez7KI4CCXg"}},"topics":["s:football:pre","m:32aab779be:live","bad:topic"]}'
echo "== subscribe"; curl -sS -m 30 -X POST "$B/api/subscribe" -H 'Content-Type: application/json' -d "$S"; echo
echo "== health"; curl -sS -m 30 "$B/api/health"; echo
echo "== test push to fake device"; curl -sS -m 30 -X POST "$B/api/test" -H 'Content-Type: application/json' -d "$S"; echo
echo "== test again (rate limit)"; curl -sS -m 30 -X POST "$B/api/test" -H 'Content-Type: application/json' -d "$S"; echo
echo "== push without token"; curl -sS -m 30 -X POST "$B/api/push" -H 'Content-Type: application/json' -d '{"topics":["s:football:pre"],"title":"x"}'; echo
echo "== push bad token"; curl -sS -m 30 -X POST "$B/api/push" -H 'Authorization: Bearer abc.def.ghi' -H 'Content-Type: application/json' -d '{"topics":["s:football:pre"],"title":"x"}'; echo
echo "== unsubscribe"; curl -sS -m 30 -X DELETE "$B/api/subscribe" -H 'Content-Type: application/json' -d "$S"; echo
echo "== health"; curl -sS -m 30 "$B/api/health"; echo
