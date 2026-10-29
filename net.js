const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36' });
  const seen = [];
  p.on('response', async r => {
    const u = r.url(); const ct = r.headers()['content-type'] || '';
    if (/json|api/i.test(ct + u) && !/google|iubenda|facebook|doubleclick|minute-ly|sentry|analytics|onetrust|cookie/i.test(u)) {
      let body = ''; try { body = (await r.text()).slice(0, 300).replace(/\s+/g, ' '); } catch (e) {}
      seen.push(r.status() + ' ' + u + '\n     ' + body);
    }
  });
  for (const url of process.argv.slice(2)) {
    seen.length = 0;
    try { await p.goto(url, { waitUntil: 'networkidle', timeout: 60000 }); } catch (e) { console.log('goto err', e.message); }
    await p.waitForTimeout(4000);
    console.log('#### ' + url); console.log(seen.slice(0, 40).join('\n'));
  }
  await b.close();
})();
