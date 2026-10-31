#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
gh api repos/GabrielChatzi/PAOK-calendar/actions/jobs/124567722836/logs | grep -E "ΕΘΝΙΚΟΣ|push|!|Αγώνες" | sed -E 's/^[0-9TZ:.-]+ //' | cut -c1-200 | tail -25
