const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36' });
  p.on('request', r => { if (/competitionmatchesapi/i.test(r.url())) console.log('REQ', r.method(), r.url(), r.postData() || ''); });
  p.on('response', async r => { if (/GetMatches/i.test(r.url())) { const t = await r.text(); console.log('RESP', t.slice(0, 300)); const i = t.indexOf('PAOK'); if (i >= 0) console.log('PAOK ctx', t.slice(Math.max(0, i - 2500), i + 200)); } });
  await p.goto(process.argv[2], { waitUntil: 'networkidle', timeout: 60000 });
  for (const txt of ['Load Past Matches', 'Load Future Matches']) {
    const btn = p.getByText(txt, { exact: false });
    if (await btn.count()) { await btn.first().click({ timeout: 5000 }).catch(e => console.log('click err', e.message)); await p.waitForTimeout(4000); }
    else console.log('no button', txt);
  }
  const html = await p.content(); const m = html.match(/load-more-matches[^>]*>[^<]*/g); console.log(m);
  await b.close();
})();
