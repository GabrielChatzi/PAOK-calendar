import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { chromium } from "playwright";
const root = path.resolve("site"), out = path.resolve("docs/new"); fs.mkdirSync(out, { recursive: true });
const types = { ".html":"text/html", ".js":"text/javascript", ".json":"application/json", ".png":"image/png", ".webmanifest":"application/manifest+json" };
const server = http.createServer((req, res) => { const f = path.join(root, decodeURIComponent(req.url.split("?")[0]).replace(/\/$/, "/index.html"));
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": types[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(res); }).listen(0);
const base = `http://localhost:${server.address().port}/`;
const b = await chromium.launch();
const shots = [["cup-football", "#/football/standings", "Κύπελλο Ελλάδας – Φάση", "Europe/Athens"],
  ["cups-football", "#/football/standings", "Κύπελλα και Ευρώπη", "Europe/Athens"],
  ["cups-handball", "#/handball/standings", "Κύπελλα και Ευρώπη", "Europe/Athens"],
  ["group-waterpolo-women", "#/waterpolo-women/standings", "Euro Cup Γυναικών", "Europe/Athens"],
  ["tv-list", "#/", "Τρίτη 3 Νοεμβρίου", "Europe/Athens"],
  ["tv-match", "#/m/8e16c84199", null, "Europe/Athens"],
  ["abroad-match", "#/m/b79cb11881", null, "Europe/Berlin"]];
for (const [name, route, anchor, tz] of shots) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, timezoneId: tz, locale: "el-GR" });
  await ctx.addInitScript(() => Object.defineProperty(Navigator.prototype, "standalone", { get: () => true }));
  const p = await ctx.newPage(); await p.route(/_vercel|\/api\//, r => r.abort());
  await p.goto(base + route); await p.waitForTimeout(2500);
  if (anchor) await p.evaluate((a) => { const el = [...document.querySelectorAll("h2,h3,h4")].find(x => x.textContent.includes(a)); if (el) window.scrollTo(0, el.getBoundingClientRect().top + scrollY - 70); }, anchor);
  await p.waitForTimeout(1200);
  await p.screenshot({ path: `${out}/${name}.png` }); await ctx.close();
}
await b.close(); server.close();
