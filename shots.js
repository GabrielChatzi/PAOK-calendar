const { chromium, devices } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ ...devices['iPhone 15 Pro'], colorScheme: 'light' });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'standalone', { get: () => true });
    const sub = { endpoint: 'https://web.push.apple.com/x', options: {}, toJSON() { return { endpoint: this.endpoint, keys: { p256dh: 'p', auth: 'a' } }; }, unsubscribe() { return Promise.resolve(true); } };
    if (window.PushManager) {
      PushManager.prototype.getSubscription = function () { return Promise.resolve(sub); };
      PushManager.prototype.subscribe = function () { return Promise.resolve(sub); };
    }
    if (window.Notification) Object.defineProperty(Notification, 'permission', { get: () => 'granted' });
    try { localStorage.setItem('paok-install-snooze-until', String(Date.now() + 1e10)); } catch (e) {}
  });
  await ctx.route('**/api/**', r => r.fulfill({ json: { ok: true, publicKey: 'BAAA' } }));
  const p = await ctx.newPage();
  const B = 'https://paokalendar.vercel.app/';
  await p.goto(B); await p.waitForTimeout(3000);
  const nt = await p.evaluate(() => fetch('matches.json').then(r => r.json()).then(d => d.matches.filter(x => x.section === 'football' && !x.score && new Date(x.start) > Date.now() - 3*3600e3)[0].nt));
  await p.evaluate((nt) => {
    const t = ['s:football:pre','s:football:live','s:football:result','s:basketball:pre','s:basketball:live','s:basketball:result','s:volley:pre','s:volley:result','s:volley-women:result','s:handball:result'];
    ['pre','time','live','result'].forEach(k => t.push('m:' + nt + ':' + k));
    localStorage.setItem('paok-push-topics', JSON.stringify(t));
    localStorage.setItem('paok-push-synced', String(Date.now()));
  }, nt);
  const shot = async (hash, name, scrollSel, offset) => {
    await p.goto(B + hash); await p.reload(); await p.waitForTimeout(4000);
    if (scrollSel) {
      await p.evaluate(([s, o]) => { const el = document.querySelector(s); if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - (o || 0)); }, [scrollSel, offset]);
      await p.waitForTimeout(800);
    }
    // Σήματα ομάδων → αρχικά (η εικόνα προώθησης δεν δείχνει σήματα συλλόγων).
    await p.evaluate(() => document.querySelectorAll('img.crest').forEach(i => { i.outerHTML = i.dataset.f; }));
    await p.waitForTimeout(200);
    await p.screenshot({ path: 'docs/' + name + '.png' });
  };
  await shot('#/', 'p-home');
  await shot('#/', 'p-home-tiles', '.tiles', 120);
  await shot('#/notifications', 'p-notif', '.nsec', 250);
  await shot('#/m/' + nt, 'p-match');
  await shot('#/m/' + nt, 'p-match-notify', '#match-notify', 20);
  await shot('#/basketball/standings', 'p-standings', 'table.st', 220);
  await shot('#/football', 'p-football');
  console.log('done', nt);
  await b.close();
})();
