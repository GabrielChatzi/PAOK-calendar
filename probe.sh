#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
for i in $(seq 1 20); do s=$(gh run view 40531309855 -R GabrielChatzi/PAOK-calendar --json status --jq .status); [ "$s" = completed ] && break; sleep 5; done
gh run view 40531309855 -R GabrielChatzi/PAOK-calendar --log | grep "Παρακολούθηση" | cut -f3- | grep -v "^\s*$" | cut -c1-300 | head -80
