// Η σελίδα ανοίγει χωρίς σφάλματα σε όλες τις διαδρομές (τρέχει στο tests.yml με Playwright).
//   node tests/page-smoke.mjs   (χρειάζεται τα δεδομένα στο docs/: matches.json, standings.json)
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const root = path.join(path.dirname(new URL(import.meta.url).pathname), "..", "docs");
const types = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".png": "image/png",
  ".webmanifest": "application/manifest+json", ".ics": "text/calendar" };
const server = http.createServer((req, res) => {
  const file = path.join(root, decodeURIComponent(req.url.split("?")[0]).replace(/\/$/, "/index.html"));
  if (!file.startsWith(root) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": types[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
}).listen(0);
const base = `http://localhost:${server.address().port}/`;

const routes = ["#/", "#/football", "#/basketball/standings", "#/volley/results", "#/waterpolo-women/follow",
  "#/notifications", "#/calendars", "#/app"];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.route(/\/api\/|_vercel|fonts\.g/, (r) => r.abort());
const data = JSON.parse(fs.readFileSync(path.join(root, "matches.json"), "utf8"));
const someMatch = data.matches.find((m) => m.live) || data.matches[0];
routes.push(`#/m/${someMatch.nt}`);
let failed = 0;
for (const r of routes) {
  await page.goto(base + r);
  await page.waitForTimeout(600);
  const text = (await page.textContent("main")) || "";
  const ok = text.length > 200 && !/δεν φόρτωσε/.test(text);
  if (!ok) failed++;
  console.log(`${ok ? "ok  " : "FAIL"} ${r} (${text.length} χαρακτήρες)`);
}
// Το μενού ανοίγει και κλείνει.
await page.goto(base + "#/");
await page.click("#menu-btn");
const menuOpen = await page.isVisible("#menu-panel");
await page.keyboard.press("Escape");
if (!menuOpen) { failed++; console.log("FAIL μενού"); }
await browser.close();
server.close();
if (errors.length) console.log("Σφάλματα JavaScript:\n  " + errors.join("\n  "));
process.exit(failed || errors.length ? 1 : 0);
