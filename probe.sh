#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
gh api --allow-escape-sequences repos/GabrielChatzi/PAOK-calendar/actions/jobs/124790277881/logs | sed "s/\x1b\[[0-9;]*m//g" | grep -E "^\S+ ! |Καμία|Προβλήματα|push " | sed -E 's/^[0-9TZ:.-]+ //' | cut -c1-220 | head -20
