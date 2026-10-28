const { chromium, devices } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ ...devices['iPhone 15 Pro'], colorScheme: 'light' });
  await ctx.addInitScript(() => {
    let sub = { endpoint: 'https://web.push.apple.com/x', options: {}, toJSON() { return { endpoint: this.endpoint, keys: { p256dh: 'p', auth: 'a' } }; }, unsubscribe() { return Promise.resolve(true); } };
    if (window.PushManager) {
      PushManager.prototype.getSubscription = function () { return Promise.resolve(sub); };
      PushManager.prototype.subscribe = function () { return Promise.resolve(sub); };
    }
    try {
      localStorage.setItem('paok-push-topics', JSON.stringify(['s:football:pre','s:football:live','s:football:result','s:basketball:pre','s:basketball:live','s:basketball:result','s:volley:result','s:volley:pre']));
      localStorage.setItem('paok-push-synced', String(Date.now()));
      localStorage.setItem('paok-install-snooze-until', String(Date.now() + 1e10));
    } catch (e) {}
  });
  await ctx.route('**/api/**', r => r.fulfill({ json: { ok: true, publicKey: 'BAAA' } }));
  const p = await ctx.newPage();
  const B = 'https://paokalendar.vercel.app/';
  const shot = async (hash, name, full, scrollTo) => {
    await p.goto(B + hash); await p.waitForTimeout(4000);
    if (scrollTo) { await p.evaluate(s => { const el = document.querySelector(s); if (el) el.scrollIntoView(); }, scrollTo); await p.waitForTimeout(800); }
    await p.screenshot({ path: 'docs/' + name + '.png', fullPage: !!full });
  };
  await shot('#/', 'home');
  await shot('#/', 'home-full', true);
  await shot('#/m/32aab779be', 'match');
  await shot('#/m/32aab779be', 'match-full', true);
  await shot('#/notifications', 'notifications');
  await shot('#/basketball/standings', 'standings');
  await shot('#/basketball', 'section');
  const m = await p.evaluate(() => fetch('matches.json').then(r => r.json()).then(d => d.matches.filter(x => x.section === 'football' && x.score).slice(-1)[0].nt));
  await shot('#/m/' + m, 'match-football-full', true);
  console.log('done', m);
  await b.close();
})();
