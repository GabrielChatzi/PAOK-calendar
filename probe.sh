#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
W=https://ea.microplustimingservices.com/api/wp
H=(-A "Mozilla/5.0" -H "Origin: https://ea.microplustimingservices.com" -H "Referer: https://ea.microplustimingservices.com/EAWPClubs2027/")
T=$(curl -sS -m 30 "${H[@]}" "$W/site/token"); echo "token resp: ${T:0:300}"
TOK=$(echo "$T" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")
for p in "events/*" "schedule/*/*/*/*/*" "teams" "rounds" "groupstandings"; do
  f="docs/$(echo $p | tr '/*' '__').json"
  curl -sS -m 60 "${H[@]}" -H "Authorization: Bearer $TOK" "$W/EACLUB27/get/$p" -o "$f"; echo "== $p $(wc -c < $f)"
done
python3 - <<'PY'
import json,glob
for f in sorted(glob.glob("docs/*.json")):
    try: d=json.load(open(f))
    except Exception as e: print(f,"not json",open(f).read()[:150]); continue
    s=json.dumps(d,ensure_ascii=False)
    print("####",f, s[:700])
    i=s.find("PAOK")
    if i>=0: print("  PAOK ctx:", s[max(0,i-1500):i+700])
PY
