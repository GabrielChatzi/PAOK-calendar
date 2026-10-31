#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
for q in "src=koe&cat=ASM&gara=65&tur=A01&gru=1&a=9175200&b=9175106" "src=ea&code=EACLUB27&cat=ASF&gara=2&tur=001&a=ZVL&b=PAOK"; do
  curl -sS -m 30 -D /tmp/h "https://paokalendar.vercel.app/api/live?$q"; echo; grep -i "cache-control\|x-vercel-cache" /tmp/h
done
