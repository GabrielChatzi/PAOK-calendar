#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
EA=https://ea.microplustimingservices.com/api/wp
UA="Mozilla/5.0"
T=$(curl -sS -A "$UA" "$EA/site/token" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")
echo "token len ${#T}"
curl -sS -A "$UA" -H "Authorization: Bearer $T" "$EA/EACLUB27/get/schedule/*/*/*/*/*" > docs/sched.json
python3 - <<'PY'
import json
d=json.load(open('docs/sched.json'))
for o in d.get('Schedule',[]):
    if o.get('OraTeamCodeB')=='PAOK' or o.get('OraTeamCodeA')=='PAOK':
        print(json.dumps(o,ensure_ascii=False))
print('keys top', list(d.keys()))
PY
for path in "resultsDBlikeJSON/ASF/2/001/1/URA/PAOK" "resultsDBlikeJSON/ASF/2/001/C/URA/PAOK" "resultsDBlikeJSON/ASF/2/001/*/URA/PAOK" "results/ASF/2/001/URA/PAOK" "livescore/ASF/2/001" "live/ASF/2/001"; do
  echo "== $path"; curl -sS -A "$UA" -H "Authorization: Bearer $T" -w " [%{http_code}]" "$EA/EACLUB27/get/$path" | head -c 1500; echo
done
echo "== site html"; curl -sS -A "$UA" "https://ea.microplustimingservices.com/" | grep -oE 'src="[^"]+\.js"|api/wp/[A-Za-z/{}$._-]+' | sort -u | head -30
