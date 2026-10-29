const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36' });
  const seen = [];
  p.on('response', async r => {
    const u = r.url(); const ct = r.headers()['content-type'] || '';
    if (/\.(dll|wasm|js|css|png|jpg|svg|woff2?|gif|webp|ico)(\?|$)/i.test(u)) return;
    if (/google|iubenda|facebook|doubleclick|minute-ly|sentry|segment|onetrust|cookie|hotjar|twitter|instagram|youtube/i.test(u)) return;
    let body = ''; try { body = (await r.text()).slice(0, 400).replace(/\s+/g, ' '); } catch (e) {}
    seen.push(r.status() + ' ' + ct.split(';')[0] + ' ' + u + (/json/.test(ct) ? '\n     ' + body : ''));
  });
  for (const url of process.argv.slice(2)) {
    seen.length = 0;
    try { await p.goto(url, { waitUntil: 'networkidle', timeout: 60000 }); } catch (e) { console.log('goto err', e.message); }
    for (let i = 0; i < 6; i++) { await p.mouse.wheel(0, 1500); await p.waitForTimeout(1500); }
    console.log('#### ' + url); console.log(seen.slice(0, 50).join('\n'));
    const txt = await p.evaluate(() => document.body.innerText);
    const i = txt.search(/PAOK/i); console.log('PAOK in text:', i, i >= 0 ? txt.slice(Math.max(0, i - 300), i + 300).replace(/\s+/g, ' ') : '');
  }
  await b.close();
})();
