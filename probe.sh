#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0"
EA=https://ea.microplustimingservices.com/api/wp
T=$(curl -sS -A "$UA" "$EA/site/token" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")
curl -sS -A "$UA" -H "Authorization: Bearer $T" "$EA/EACLUB27/get/playbyplay/ASF/2/001/3/URA/PAOK?live=1" > docs/pbp.json
python3 - <<'PY'
import json, collections
ev=json.load(open('docs/pbp.json'))['Events']
print(len(ev), 'events')
c=collections.Counter((e['EveCode'], e['EveDescrEng']) for e in ev)
for k,v in sorted(c.items()): print(v, k)
print('--- non-player / period-ish events')
for e in ev:
    if not e.get('EvePlaCode') or e['EveCode'] in ('STP','ENP','SOP','EOP','END','STA','TO','TOA','TOB','EOG','BOP','FIN') :
        print(e['EvePeriod'], e['EveGameTime'], e['EveUTCTime'], e['EveCode'], e['EveDescrEng'], e['EveTeamCode'], e['EveResA'], e['EveResB'])
print('--- last 6')
for e in ev[-6:]: print(e['EvePeriod'], e['EveGameTime'], e['EveUTCTime'], e['EveCode'], e['EveDescrEng'], e['EveResA'], e['EveResB'])
PY
