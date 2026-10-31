#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
for r in $(gh run list --workflow reminders.yml --limit 12 --json databaseId --jq '.[].databaseId') $(gh run list --workflow update.yml --limit 6 --json databaseId --jq '.[].databaseId'); do
  gh run view $r --log 2>/dev/null | sed "s/\x1b\[[0-9;]*m//g" | grep -E " push " | sed -E 's/^.*Z //' | cut -c1-200
done
