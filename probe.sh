#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
B=https://paokalendar.vercel.app
for i in $(seq 1 20); do h=$(curl -sS -m 30 "$B/api/health"); case "$h" in *byService*) break;; esac; sleep 10; done
echo "all: $h"
for t in m:32aab779be:pre m:32aab779be:live s:basketball:pre s:basketball:live; do echo "$t: $(curl -sS -m 30 "$B/api/health?topic=$t")"; done
