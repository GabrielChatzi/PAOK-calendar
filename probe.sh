#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
B=https://paokalendar.vercel.app
for u in /api/health /api/vapid /icons/badge-96.png /sw.js; do
  echo "== $u"; curl -sS -m 30 -o /tmp/o -w "%{http_code} %{content_type}\n" "$B$u"; head -c 300 /tmp/o | strings | head -5; echo
done
echo "== push without token"; curl -sS -m 30 -X POST "$B/api/push" -H 'Content-Type: application/json' -d '{"topics":["s:football:pre"],"title":"x"}'; echo
echo "== subscribe bad"; curl -sS -m 30 -X POST "$B/api/subscribe" -H 'Content-Type: application/json' -d '{"subscription":{"endpoint":"https://evil.example/x","keys":{"p256dh":"a","auth":"b"}}}'; echo
