#!/usr/bin/env bash
cd /home/claude/probe2 && ./run.sh 2>&1 | grep -v "^[a-z_-]*\.ics$\|^matches.json$\|^status.json$\|^standings.json$"
