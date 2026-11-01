#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0"
EA=https://ea.microplustimingservices.com/api/wp
T=$(curl -sS -A "$UA" "$EA/site/token" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")
for q in "" "?live=1" "" ; do
  echo "== schedule$q"; curl -sS -D - -o /dev/null -A "$UA" -H "Authorization: Bearer $T" "$EA/EACLUB27/get/schedule/*/*/*/*/*$q" | grep -iE "^(x-cache|cache-control|age|expires|last-modified|etag|date):"
  sleep 2
done
