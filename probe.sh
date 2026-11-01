#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
EA=https://ea.microplustimingservices.com/api/wp
UA="Mozilla/5.0"
T=$(curl -sS -A "$UA" "$EA/site/token" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")
for path in "resultsDBlikeJSON/ASF/2/001/3/URA/PAOK" "resultsDBlikeJSON/ASF/2/001/03/URA/PAOK" "resultsDBlikeJSON/ASF/2/001/3/PBE/PAOK" "schedulereferee/ASF/2/*/*/*" "resultsDBlikeJSON/ASF/2/001/3/ZVL/PAOK"; do
  echo "== $path"; curl -sS -A "$UA" -H "Authorization: Bearer $T" -w " [%{http_code}]" "$EA/EACLUB27/get/$path" | head -c 2500; echo
done
echo "== koe same shape"
KT=$(curl -sS -A "$UA" "https://live.koe.org.gr/api-waterpolo/wp/token" | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])")
curl -sS -A "$UA" -H "x-wp-token: $KT" "https://live.koe.org.gr/api-waterpolo/wp/KOE/get/schedulereferee/ASM/65/*/*/*" | head -c 600; echo
for u in "https://ea.microplustimingservices.com/" "https://ea.microplustimingservices.com/EACLUB27/" "https://europeanaquatics.org/sports/water-polo/club-competitions/schedule/"; do
  echo "== $u"; curl -sSL -A "$UA" "$u" | grep -oiE '(https?:)?//[a-z0-9.-]*microplus[a-z0-9./_-]*|api/wp/[^"'"'"' ]+|livescore[^"'"'"' ]{0,80}' | sort -u | head -20
done
