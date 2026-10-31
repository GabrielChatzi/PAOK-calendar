#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
API=https://ea.microplustimingservices.com/api/wp
echo "== microplus CORS token"
curl -sS -m 30 -A "$UA" -D - -o /tmp/tok -H "Origin: https://paokalendar.vercel.app" "$API/site/token" | grep -i "^access-control\|^HTTP"
TOK=$(python3 -c "import json;print(json.load(open('/tmp/tok'))['data']['token'])")
echo "== microplus CORS schedule"
curl -sS -m 60 -A "$UA" -D - -o /tmp/sch -H "Origin: https://paokalendar.vercel.app" -H "Authorization: Bearer $TOK" "$API/EACLUB27/get/schedule/*/*/*/*/*" | grep -i "^access-control\|^HTTP"
python3 - <<'PY'
import json
d=json.load(open('/tmp/sch'))
print("keys", list(d.keys()))
for x in d["Schedule"]:
    if "PAOK" in (x.get("OraTeamCodeA",""),x.get("OraTeamCodeB","")) or "PAOK" in (x.get("OraTeamNameA","")+x.get("OraTeamNameB","")):
        print(json.dumps(x, ensure_ascii=False))
PY
echo "== microplus site js"
curl -sS -m 30 -A "$UA" https://ea.microplustimingservices.com/ -o /tmp/site.html; grep -o 'src="[^"]*\.js[^"]*"' /tmp/site.html | head
for js in $(grep -o 'src="[^"]*\.js[^"]*"' /tmp/site.html | sed 's/src="//;s/"$//' | head -8); do
  case "$js" in http*) u=$js;; /*) u=https://ea.microplustimingservices.com$js;; *) u=https://ea.microplustimingservices.com/$js;; esac
  curl -sS -m 30 -A "$UA" "$u" | grep -o '"/\?get/[A-Za-z_/${}*+." ]*\|get/[a-zA-Z_]*/' | sort -u | head -60
done
echo "== waterpololeague fixture"
curl -sS -m 30 -A "$UA" "https://waterpololeague.gr/fixture/paok-domus-ergo-ethnikos-ofpf-2026-10-31" -o /tmp/wpl.html; wc -c /tmp/wpl.html
grep -o 'https\?://[^"'"'"' ]*api[^"'"'"' ]*' /tmp/wpl.html | sort -u | head -20
grep -io 'live[^<]\{0,80\}' /tmp/wpl.html | head -10
grep -o '_next/static/[^"]*\.js' /tmp/wpl.html | head -5
grep -o '"score[^,]\{0,60\}' /tmp/wpl.html | head; grep -o '__NEXT_DATA__' /tmp/wpl.html | head -1
python3 - <<'PY'
import re
s=open('/tmp/wpl.html',encoding='utf-8',errors='replace').read()
m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',s,re.S)
if m: print(m.group(1)[:3000])
else:
  i=s.find('ΕΘΝΙΚΟΣ'); print(re.sub(r'\s+',' ',s[max(0,i-1500):i+1500]))
PY
echo "== sofascore"
npm i --silent playwright@1.48.2 >/dev/null 2>&1 && npx playwright install --with-deps chromium >/dev/null 2>&1
node -e "
const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ userAgent: '$UA' });
  await p.goto('https://paokalendar.vercel.app/', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(e => console.log('goto', e.message));
  const r = await p.evaluate(async () => {
    const out = [];
    const get = async (u) => { const x = await fetch('https://api.sofascore.com/api/v1/' + u); out.push(u + ' -> ' + x.status); return x.ok ? x.json() : null; };
    for (const q of ['PAOK', 'PAOK women', 'PAOK W']) {
      const d = await get('search/all?q=' + encodeURIComponent(q) + '&page=0');
      (d && d.results || []).filter(r => r.type === 'team').forEach(r => out.push('  ' + r.entity.id + ' ' + r.entity.name + ' | ' + (r.entity.sport||{}).slug + ' ' + r.entity.gender + ' ' + ((r.entity.country||{}).alpha2||'')));
    }
    const d2 = await get('sport/waterpolo/scheduled-events/2026-10-31');
    (d2 && d2.events || []).forEach(e => out.push('  wp ' + e.id + ' ' + e.homeTeam.name + ' - ' + e.awayTeam.name + ' ' + e.status.type + ' ' + (e.homeScore||{}).current + '-' + (e.awayScore||{}).current + ' ' + e.tournament.name));
    return out.join('\n');
  });
  console.log(r); await b.close(); })();"
