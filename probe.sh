#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
gh api --allow-escape-sequences repos/GabrielChatzi/PAOK-calendar/actions/jobs/124570043839/logs | sed "s/\x1b\[[0-9;]*m//g" | grep -E "ΕΘΝΙΚΟΣ|push|!|Αγώνες|Traceback|Error" | sed -E 's/^[0-9TZ:.-]+ //' | cut -c1-200 | tail -25
curl -sS "https://paokalendar.vercel.app/api/live?src=koe&cat=ASM&gara=65&tur=A01&gru=1&a=9175200&b=9175106"; echo
