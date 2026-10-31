#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
r=$(gh run list --workflow update.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run view $r --log 2>/dev/null | sed "s/\x1b\[[0-9;]*m//g" | grep -E " push |    ! |σε εξέλιξη" | sed -E 's/^.*Z //' | cut -c1-220
