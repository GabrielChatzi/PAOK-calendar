#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
gh api --allow-escape-sequences repos/GabrielChatzi/PAOK-calendar/actions/jobs/124610869132/logs | sed "s/\x1b\[[0-9;]*m//g" | grep -E 'watchdog|Προβλήματα|push|!|Traceback|Error|error' | sed -E 's/^[0-9TZ:.-]+ //' | cut -c1-250 | head -30
