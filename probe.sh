#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
for base in https://api.sofascore.com/api/v1 https://www.sofascore.com/api/v1; do
  curl -sS -m 30 -A "$UA" -H "Accept: application/json, text/plain, */*" -H "Referer: https://www.sofascore.com/" -H "Origin: https://www.sofascore.com" -o /tmp/o -w "$base %{http_code}\n" "$base/search/all?q=PAOK&page=0"; head -c 200 /tmp/o; echo
done
npm i --silent playwright@1.48.2 >/dev/null 2>&1 && npx playwright install --with-deps chromium >/dev/null 2>&1
node -e "
const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('https://www.sofascore.com/', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(e => console.log('goto', e.message));
  const r = await p.evaluate(async () => { const x = await fetch('https://api.sofascore.com/api/v1/search/all?q=PAOK&page=0'); return x.status + ' ' + (await x.text()).slice(0, 3000); });
  console.log(r); await b.close(); })();"
