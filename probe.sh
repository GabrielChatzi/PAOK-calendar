#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
for t in paokcal-x7q3-m-32aab779be paokcal-x7q3-m-32aab779be-live paokcal-x7q3-m-32aab779be-pre paokcal-x7q3-basketball-pre paokcal-x7q3-basketball-live; do
  echo "== $t"
  curl -sS "https://ntfy.sh/$t/json?poll=1&since=24h"
done
