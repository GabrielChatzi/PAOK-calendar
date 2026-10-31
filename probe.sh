#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
curl -sS -m 30 "https://paokalendar.vercel.app/api/live?src=koe&cat=ASM&gara=65&tur=A01&gru=1&a=9175200&b=9175106"; echo
