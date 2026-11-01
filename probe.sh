#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0"
EA=https://ea.microplustimingservices.com/api/wp
T=$(curl -sS -A "$UA" "$EA/site/token" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")
curl -sSL -A "$UA" https://ea.microplustimingservices.com/EAWPClubs2027/assets/api_config.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('API_AGG')), [k for k in d])"
for path in "results/ASF/2/001/3/URA/PAOK?live=1" "results/ASF/2/001/3/URA/PAOK" "playbyplay/ASF/2/001/3/URA/PAOK?live=1" "schedule/*/*/*/*/*?live=1"; do
  echo "== $path"; curl -sS -D /tmp/hd -A "$UA" -H "Authorization: Bearer $T" -w " [%{http_code}]" "$EA/EACLUB27/get/$path" > /tmp/b; grep -iE "cache|age|expires" /tmp/hd; head -c 3000 /tmp/b; echo
done
