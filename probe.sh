#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
for t in paokcal-x7q3-basketball-pre paokcal-x7q3-m-32aab779be paokcal-x7q3-basketball-live paokcal-x7q3-m-32aab779be-live; do
echo "== $t"; curl -sS -m 30 "https://ntfy.sh/$t/json?poll=1&since=all" | cut -c1-250
done
