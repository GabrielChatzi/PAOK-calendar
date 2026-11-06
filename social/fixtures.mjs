// Εικόνες «Πρόγραμμα αγώνων» για Instagram / Facebook (το σχέδιο που διαλέξαμε, Νοέμβριος 2026).
//
//   node social/fixtures.mjs social/days/2026-11-07.json [out-dir]
//
// Βγάζει <out>/<όνομα>-post.png (1080×1350) και <out>/<όνομα>-story.png (1080×1920).
// Σκούρο φόντο με λεπτές κάθετες ρίγες, μέρα με χοντρή στενή γραμματοσειρά που σβήνει προς τα κάτω,
// ημερομηνία καλλιγραφική μισή πάνω στη μέρα, αντίπαλος με σήμα, τμήμα (ανδρών / γυναικών) | ώρα | κανάλι,
// εντός (γήπεδο) / εκτός (αεροπλάνο) και κάτω μόνο το λογότυπο. Τα αποτελέσματα θα έχουν άλλο σχέδιο
// (ανοιχτό, λευκό με μαύρο), για να ξεχωρίζουν.
//
// Το JSON: {"day":"Σάββατο","date":"07.11","file":"2026-11-07","matches":[
//   {"time":"11:45","section":"Μπάσκετ Γυναικών","opponent":"Αθηναϊκός","logo":"logos/ath.png",
//    "venue":"PAOK Sports Arena","tv":"ΕΟΚ TV","home":true}, ...]}
// Το "logo" είναι διαδρομή σε σχέση με το JSON ή URL (κατεβαίνει αν υπάρχει δίκτυο).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { MONO_CRESTS } from "./crests.mjs";

// Το Playwright φορτώνεται μόνο όταν χρειάζεται (τα tests του πλάνου τρέχουν και χωρίς αυτό).
export async function chromium() {
  try { return createRequire(import.meta.url)("playwright").chromium; } catch {
    return (await import("/opt/npm-tools/node_modules/playwright/index.mjs")).chromium;
  }
}

const HERE = path.dirname(fileURLToPath(import.meta.url));

const font = (fam, w, file) =>
  `@font-face{font-family:${fam};font-weight:${w};src:url(data:font/woff2;base64,${fs.readFileSync(path.join(HERE, "fonts", file)).toString("base64")})}`;
const FONTS = ["greek", "latin"].flatMap((s) => [
  font("F", 700, `fira-sans-extra-condensed-${s}-700-normal.woff2`),
  font("F", 800, `fira-sans-extra-condensed-${s}-800-normal.woff2`),
  font("S", 900, `sofia-sans-extra-condensed-${s}-900-normal.woff2`),
]).join("") + font("GV", 400, "great-vibes-latin-400-normal.woff2");

async function logo(src, base) {
  if (!src) return "";
  let buf;
  if (/^https?:/.test(src)) {
    const r = await fetch(src, { headers: { "User-Agent": "Mozilla/5.0" } });
    buf = Buffer.from(await r.arrayBuffer());
  } else buf = fs.readFileSync(path.resolve(base, src));
  const t = buf[0] === 0x89 ? "png" : buf[0] === 0x47 ? "gif" : buf[0] === 0x3c ? "svg+xml" : buf[0] === 0x52 ? "webp" : "jpeg";
  return `data:image/${t};base64,${buf.toString("base64")}`;
}
const UP = (t) => String(t || "").normalize("NFD").replace(/\p{M}/gu, "").toUpperCase();
const HOME = '<svg viewBox="0 0 48 48" width="22" height="22"><path d="M4 22c0-4 9-7 20-7s20 3 20 7v12c0 4-9 7-20 7S4 38 4 34z" fill="none" stroke="currentColor" stroke-width="4"/><ellipse cx="24" cy="23" rx="12" ry="3.5" fill="currentColor"/><path d="M8 6v12M40 6v12" stroke="currentColor" stroke-width="3"/><rect x="5" y="4" width="6" height="4" fill="currentColor"/><rect x="37" y="4" width="6" height="4" fill="currentColor"/></svg>';
const AWAY = '<svg viewBox="0 0 48 48" width="22" height="22"><path d="M44 21c0-2-2-3-4-3H30L19 4h-5l6 14H10l-4-5H2l3 11-3 11h4l4-5h10l-6 14h5l11-14h10c2 0 4-1 4-3z" fill="currentColor"/></svg>';

function html(spec, rows, story) {
  const n = rows.length;
  // Λιγότεροι αγώνες → μεγαλύτερα στοιχεία.
  const k = story ? Math.min(1.25, 1 + (6 - n) * 0.06) : n > 5 ? 1 - (n - 5) * 0.2 : Math.min(1.15, 1 + (5 - n) * 0.05);
  const H = story ? 1920 : 1350;
  const top = story ? 250 : 60;
  return `<!doctype html><html><head><meta charset=utf-8><style>${FONTS}
*{margin:0;box-sizing:border-box}
body{display:flow-root;width:1080px;height:${H}px;color:#fff;font-family:F;overflow:hidden;position:relative;background:#0b0b0b}
.st{position:absolute;inset:0;background:repeating-linear-gradient(90deg,#fff 0 1.5px,transparent 1.5px 60px);opacity:.10;-webkit-mask:radial-gradient(ellipse 70% 60% at 50% ${story ? 25 : 20}%,#000,transparent)}
.glow{position:absolute;inset:0;background:radial-gradient(ellipse 60% 35% at 50% ${story ? 18 : 12}%,rgba(255,255,255,.16),transparent 70%)}
.grain{position:absolute;inset:0;opacity:.16;mix-blend-mode:overlay;background:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/></filter><rect width='300' height='300' filter='url(%23n)'/></svg>")}
.head,.orn,.list,.foot{position:relative;z-index:2}
.head{text-align:center;padding-top:${top}px;height:${top + 360}px}
.kick{font-weight:700;font-size:24px;letter-spacing:10px;color:#bbb}
.day{font-family:S;font-weight:900;font-size:${Math.min(330, Math.round(330 * 7.4 / [...spec.day].length))}px;line-height:.78;letter-spacing:-6px;transform:scaleX(.68);margin-top:20px;color:transparent;background:linear-gradient(#fff 35%,rgba(255,255,255,.12) 78%);-webkit-background-clip:text;background-clip:text;white-space:nowrap}
.date{position:absolute;left:0;right:0;top:${top + 205}px;font-family:GV;font-size:170px;line-height:1;color:#fff;text-shadow:0 6px 24px rgba(0,0,0,.9),0 0 40px rgba(0,0,0,.8)}
.orn{display:flex;align-items:center;justify-content:center;gap:16px;margin:0 auto;width:640px;color:#999}
.orn i{flex:1;height:1px;background:linear-gradient(90deg,transparent,#999)}.orn i:last-child{background:linear-gradient(270deg,transparent,#999)}
.mid{position:absolute;z-index:2;left:0;right:0;top:${top + 395}px;bottom:${(story ? 210 : 44) + 70}px;display:flex;align-items:center;justify-content:center}
.list{width:max-content;max-width:900px;display:flex;flex-direction:column;gap:${(story ? 44 : 20) * k}px}
.m{display:flex;align-items:center;gap:30px}
.lg{width:${96 * k}px;height:${96 * k}px;flex:none;display:flex;align-items:center;justify-content:center}
.lg img{width:100%;height:100%;object-fit:contain}
.opp{white-space:nowrap;font-family:S;font-weight:900;font-size:${76 * k}px;line-height:.9}
.info{font-weight:700;font-size:${23 * k}px;letter-spacing:4px;margin-top:6px;display:flex;align-items:center;gap:12px;color:#ddd;white-space:nowrap}
.info b{color:#fff;font-weight:800}.info s{display:inline-block;width:2px;height:${22 * k}px;background:#888;text-decoration:none}
.ha{font-weight:700;font-size:${20 * k}px;letter-spacing:4px;color:#999;margin-top:4px;display:flex;align-items:center;gap:8px}
.foot{position:absolute;bottom:${story ? 210 : 44}px;left:0;right:0;text-align:center;font-weight:800;font-size:50px;letter-spacing:-1px;line-height:1}
.foot em{font-style:normal;color:#8a8a84}
</style></head><body><div class="st"></div><div class="glow"></div>
<div class="head"><div class="kick">ΠΡΟΓΡΑΜΜΑ ΑΓΩΝΩΝ</div><div class="day">${UP(spec.day)}</div><div class="date">${spec.date}</div></div>
<div class="orn"><i></i><span>✦</span><i></i></div>
<div class="mid"><div class="list">${rows.join("")}</div></div>
<div class="foot"><b>PAOK</b><em>alendar</em></div><div class="grain"></div></body></html>`;
}

// Βγάζει τις εικόνες ενός JSON (βλ. πάνω). base: ο φάκελος για τα σχετικά "logo".
export async function render(spec, outDir, { browser, base = outDir, kinds = ["post", "story"] } = {}) {
  const rows = [];
  for (const m of spec.matches) {
    const src = await logo(m.logo, base).catch(() => "");
    rows.push(`<div class="m"><div class="lg">${src ? `<img src="${src}">` : ""}</div><div>
  <div class="opp">${UP(m.opponent)}</div>
  <div class="info">${[UP(m.section), `<b>${m.time}</b>`, UP(m.tv)].filter((x) => x && x !== "<b></b>").join(" <s></s> ")}</div>
  <div class="ha">${m.home ? HOME : AWAY} ${m.home ? "ΕΝΤΟΣ" : "ΕΚΤΟΣ"}${m.venue ? ` · ${UP(m.venue)}` : ""}</div></div></div>`);
  }
  fs.mkdirSync(outDir, { recursive: true });
  const own = !browser;
  if (own) browser = await (await chromium()).launch();
  const files = [];
  for (const story of kinds.map((k) => k === "story")) {
    const page = await browser.newPage({ viewport: { width: 1080, height: story ? 1920 : 1350 } });
    await page.setContent(html(spec, rows, story));
    await page.evaluate(MONO_CRESTS, 255);
    await page.waitForTimeout(400);
    const out = path.join(outDir, `${spec.file || "programma"}-${story ? "story" : "post"}.png`);
    await page.screenshot({ path: out });
    await page.close();
    files.push(out);
  }
  if (own) await browser.close();
  return files;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const [specPath, outDir = path.dirname(specPath)] = process.argv.slice(2);
  const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
  for (const f of await render(spec, outDir, { base: path.dirname(specPath) })) console.log(f);
}
