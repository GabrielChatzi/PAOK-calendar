#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0"
EA=https://ea.microplustimingservices.com/api/wp
T=$(curl -sS -A "$UA" "$EA/site/token" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")
curl -sS -A "$UA" -H "Authorization: Bearer $T" "$EA/EACLUB27/get/schedule/*/*/*/*/*?live=1" > /tmp/s.json
python3 - "$T" <<'PY'
import json, sys, urllib.request
T=sys.argv[1]
d=json.load(open('/tmp/s.json'))['Schedule']
today=[o for o in d if o['OraMatchDate'] in ('01/11/2026',)]
for o in today:
    u=f"https://ea.microplustimingservices.com/api/wp/EACLUB27/get/results/{o['OraCatCode']}/{o['OraGaraCode']}/{o['OraTurCode']}/{o['OraGruCode']}/{o['OraTeamCodeA']}/{o['OraTeamCodeB']}?live=1"
    try:
        r=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'Authorization':'Bearer '+T,'User-Agent':'Mozilla/5.0'}),timeout=20))
        per=[(p['PerStatus'],p['PerResA'],p['PerResB']) for p in r['Results'][0]['Periods']]
    except Exception as e: per=str(e)
    print(o['OraTime'], o['TimeZone'][:6], o['OraTeamNameBreveA'], '-', o['OraTeamNameBreveB'], 'st', o['OraStatus'], 'per', o['OraPeriods'], o['OraResA'], o['OraResB'], per)
PY
