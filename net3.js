const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36' });
  const reqs = [];
  p.on('request', r => { const u = r.url(); if (!/\.(dll|wasm|css|png|jpg|svg|woff2?|gif|webp|ico|otf|ttf|dat|blat)(\?|$)/i.test(u) && !/google|iubenda|facebook|doubleclick|tiktok|segment|hotjar|cookieconsent/i.test(u)) reqs.push(r.method() + ' ' + u); });
  p.on('response', async r => { const u = r.url(); if (/json|api|ashx|svc/i.test((r.headers()['content-type'] || '') + u) && !/blazor\.boot|\.dll/.test(u)) { let t=''; try { t = (await r.text()).slice(0, 500); } catch(e){}; console.log('JSON', u, '\n   ', t.replace(/\s+/g,' ')); } });
  await p.goto(process.argv[2], { waitUntil: 'networkidle', timeout: 90000 });
  for (let i = 0; i < 8; i++) { await p.mouse.wheel(0, 1200); await p.waitForTimeout(2000); }
  console.log(reqs.join('\n'));
  const txt = await p.evaluate(() => document.body.innerText);
  for (const k of ['PAOK', 'Galati', 'Arkada']) { const i = txt.indexOf(k); console.log(k, i, i >= 0 ? txt.slice(Math.max(0, i - 400), i + 300).replace(/\s+/g, ' ') : ''); }
  await b.close();
})();
