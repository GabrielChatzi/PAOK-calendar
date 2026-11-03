import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { chromium } from "playwright";
const root = path.resolve("site"), out = path.resolve("docs/new"); fs.mkdirSync(out, { recursive: true });
const types = { ".html":"text/html", ".js":"text/javascript", ".json":"application/json", ".png":"image/png", ".webmanifest":"application/manifest+json" };
const server = http.createServer((req, res) => { const f = path.join(root, decodeURIComponent(req.url.split("?")[0]).replace(/\/$/, "/index.html"));
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": types[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(res); }).listen(0);
const base = `http://localhost:${server.address().port}/`;
const b = await chromium.launch();
const shots = [["cups-handball", "#/handball/standings", "Κύπελλα και Ευρώπη", "Europe/Athens"], ["cups-football", "#/football/standings", "Κύπελλα και Ευρώπη", "Europe/Athens"]];
