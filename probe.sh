#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
sleep 40
for i in 1 2 3; do curl -sS -m 30 -o /tmp/s -w "%{http_code} %{content_type} %{size_download}\n" https://paokalendar.vercel.app/_vercel/insights/script.js; head -c 120 /tmp/s; echo; sleep 15; done
curl -sS -m 30 https://paokalendar.vercel.app/ | grep -c "_vercel/insights"
