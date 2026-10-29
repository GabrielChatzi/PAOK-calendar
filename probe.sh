#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
A=https://ea.microplustimingservices.com/api/wp/EACLUB27/get
for p in "events/*" "schedule/*/*/*/*/*" "teams" "rounds" "groupstandings"; do
  curl -sS -m 60 -A "Mozilla/5.0" -H "Origin: https://europeanaquatics.org" "$A/$p" -o "docs/$(echo $p | tr '/*' '__').json"
  echo "== $p $(wc -c < "docs/$(echo $p | tr '/*' '__').json")"
done
python3 - <<'PY'
import json,glob
for f in sorted(glob.glob("docs/*.json")):
    try: d=json.load(open(f))
    except Exception as e: print(f,"not json",open(f).read()[:200]); continue
    s=json.dumps(d,ensure_ascii=False)
    print("####",f,type(d).__name__, s[:600])
    i=s.find("PAOK")
    if i>=0: print("  PAOK ctx:", s[max(0,i-900):i+500])
PY
