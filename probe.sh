#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
S=https://paokalendar.vercel.app
echo "ea:   $(curl -sS "$S/api/live?src=ea&code=EACLUB27&cat=ASF&gara=2&tur=001&a=URA&b=PAOK")"
echo "eok:  $(curl -sS "$S/api/live?src=eok&day=2026-11-01&side=a&comp=WOMEN")"
echo "dp:   $(curl -sS "$S/api/live?src=dp&fed=eope&id=756&side=h")"
echo "espn: $(curl -sS "https://site.api.espn.com/apis/site/v2/sports/soccer/gre.1/summary?event=401896734" | python3 -c "import json,sys; d=json.load(sys.stdin); c=d['header']['competitions'][0]; print(c['status']['type']['name'], c['date'])")"
for t in s:waterpolo-women:pre s:waterpolo-women:live s:basketball-women:live s:football:pre s:football:live s:volley-women:live s:ops:live; do echo -n "$t "; curl -sS "$S/api/health?topic=$t" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('matching'))"; done
echo "selftest: $(curl -sS "$S/api/health?selftest=1")"
echo "subs total: $(curl -sS "$S/api/health" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('subscribers'), d.get('byService'))")"
curl -sS -o /dev/null -w "ics %{http_code} %{content_type}\n" "$S/waterpolo-women-away.ics"
curl -sS "$S/matches.json" | python3 -c "import json,sys; d=json.load(sys.stdin); print('served matches', len(d['matches']))"
