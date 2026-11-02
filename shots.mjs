import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { chromium } from "playwright";
const root = path.resolve("site"), out = path.resolve("docs/shots"); fs.mkdirSync(out, { recursive: true });
const types = { ".html":"text/html", ".js":"text/javascript", ".json":"application/json", ".png":"image/png", ".svg":"image/svg+xml", ".webmanifest":"application/manifest+json" };
const server = http.createServer((req, res) => {
  const f = path.join(root, decodeURIComponent(req.url.split("?")[0]).replace(/\/$/, "/index.html"));
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": types[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(res);
}).listen(0);
const base = `http://localhost:${server.address().port}/`;
const b = await chromium.launch();
const topics = ["s:football:pre","s:football:live","s:football:result","s:basketball:live","s:basketball:result","m:b79cb11881:pre","m:b79cb11881:live","m:b79cb11881:result"];
const list = [["home","#/",0],["match","#/m/23086ad1a5",0],["match-volley","#/m/9f9ca78a96",0],["menu","#/",0,"menu"],
  ["handball-women","#/handball-women",0],["standings","#/football/standings",0],["notifications2","#/notifications",560],
  ["upcoming","#/m/b79cb11881",0],["calendars","#/calendars",0],["home-list","#/",330],["results-list","#/football/results",380],
  ["standings-table","#/football/standings",400],["football","#/football",0]];
for (const [name, route, scroll, act] of list) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, timezoneId: "Europe/Athens", locale: "el-GR" });
  await ctx.addInitScript((t) => { Object.defineProperty(Navigator.prototype, "standalone", { get: () => true });
    try { localStorage.setItem("paok-push-topics", JSON.stringify(t)); } catch (e) {} }, topics);
  const p = await ctx.newPage(); await p.route(/_vercel|\/api\//, r => r.abort());
  await p.goto(base + route); await p.waitForTimeout(2500);
  if (act === "menu") { await p.click("#menu-btn"); await p.waitForTimeout(500); }
  await p.evaluate(() => { document.querySelectorAll(".explain, .follow > div, section div").forEach(el => { if (/μπλοκαρισμένες|Πρώτα βάλε/.test(el.textContent) && el.textContent.length < 400) el.remove(); }); });
  await p.evaluate(y => window.scrollTo(0, y), scroll); await p.waitForTimeout(1500);
  const broken = await p.evaluate(() => [...document.images].filter(i => i.complete && !i.naturalWidth).length);
  const crests = await p.evaluate(() => document.querySelectorAll("img.crest").length);
  console.log(name, "crests", crests, "broken", broken);
  await p.screenshot({ path: `${out}/${name}.png` }); await ctx.close();
}
await b.close(); server.close();
