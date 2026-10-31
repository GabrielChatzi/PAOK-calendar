#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
gh api --allow-escape-sequences repos/GabrielChatzi/PAOK-calendar/actions/jobs/124594451066/logs | sed "s/\x1b\[[0-9;]*m//g" | grep -E "ΠΑΟΚ|push|!" | sed -E 's/^[0-9TZ:.-]+ //' | cut -c1-200 | tail -30
