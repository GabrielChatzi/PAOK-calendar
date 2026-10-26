#!/usr/bin/env bash
# Push the probe branch, wait for the run, fetch results into /home/claude/probe2-data
cd /home/claude/probe2
git add -A && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -qm "probe" --allow-empty
git push -qf https://github.com/GabrielChatzi/PAOK-calendar.git probe 2>&1 | tail -1
sleep 10
for i in $(seq 1 40); do
  s=$(gh api "repos/GabrielChatzi/PAOK-calendar/actions/runs?branch=probe&per_page=1" --jq '.workflow_runs[0] | "\(.id) \(.status) \(.conclusion)"')
  case "$s" in *completed*) echo "$s"; break;; esac; sleep 8
done
rm -rf /home/claude/probe2-data; mkdir -p /home/claude/probe2-data; cd /home/claude/probe2-data && git init -q
git fetch -q https://github.com/GabrielChatzi/PAOK-calendar.git probe-data && git checkout -q FETCH_HEAD && cat probe-log.txt; ls docs
