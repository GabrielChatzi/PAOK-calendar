#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
echo "== watchdog reminders (DRY)"; DRY=1 GITHUB_TOKEN="$GH_TOKEN" GITHUB_REPOSITORY=GabrielChatzi/PAOK-calendar python3 watchdog.py reminders
echo "== watchdog update (DRY)"; DRY=1 GITHUB_TOKEN="$GH_TOKEN" GITHUB_REPOSITORY=GabrielChatzi/PAOK-calendar python3 watchdog.py update
echo "== live.py start"; timeout 70 python3 live.py; echo "exit $?"
