// Reel «Πώς βάζεις ειδοποίηση για έναν αγώνα» (1080×1920, 30 fps, χωρίς ήχο: η μουσική μπαίνει στο Instagram).
//
//   node social/reel.mjs [--out out/reel] [--nt <αγώνας>]
//
// Χρειάζεται τα δεδομένα στο docs/ (matches.json κ.λπ.) και ffmpeg. Τραβά την ίδια την εφαρμογή σε
// κινητό (Playwright), και στήνει τις σκηνές σε μια σελίδα 1080×1920 που ζωγραφίζεται καρέ καρέ:
//   1. η ειδοποίηση «ΓΚΟΛ ΤΟΥ ΠΑΟΚ!» στην κλειδωμένη οθόνη (το αγκίστρι)
//   2. αρχική → μενού → Ποδόσφαιρο → ο αγώνας
//   3. η σελίδα του αγώνα κυλά ως τις ειδοποιήσεις
//   4. ζουμ στους διακόπτες: «Πριν τον αγώνα» και «Live» ανοίγουν
//   5. κλείσιμο: paokalendar.gr
// Βγάζει reel.mp4 και cover.jpg (εξώφυλλο).
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { spawn, execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "./fixtures.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DOCS = path.join(HERE, "..", "docs");
const W = 1080, H = 1920, FPS = 30, DSF = 3;
// --όνομα τιμή (η τιμή μπορεί να έχει κενά: --date "Κυρ 8 Νοε").
const args = {};
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith("--")) args[a.slice(2)] = process.argv[i + 1] && !process.argv[i + 1].startsWith("--") ? process.argv[++i] : true;
}
const OUT = path.resolve(args.out || "out/reel");
// Προαιρετικά: στιγμιότυπα της κλειδωμένης και της αρχικής οθόνης ενός iPhone (1320×2868), με το
// εικονίδιο του PAOKalendar. --icon x,y: το κέντρο του εικονιδίου σε px της αρχικής οθόνης.
const LOCK = args.lock && fs.readFileSync(args.lock), HOMESCREEN = args.home && fs.readFileSync(args.home);
const ICON_AT = (args.icon || "1125,1637").split(",").map(Number);
// Η ειδοποίηση και η ώρα στο κινητό (π.χ. από πραγματικό γκολ): --goal "Ολυμπιακός 1–1 ΠΑΟΚ"
// --goal-body "71' Ζίβκοβιτς" --clock 22:31 --date "Κυρ 8 Νοε". Χωρίς αυτά: ένα 1–0 στον αγώνα του Reel.
const GOAL = args.goal, GOAL_BODY = args["goal-body"] || "", CLOCK = args.clock, DATE = args.date;
fs.mkdirSync(OUT, { recursive: true });

const font = (fam, file, w) =>
  `@font-face{font-family:${fam};font-weight:${w};src:url(data:font/woff2;base64,${fs.readFileSync(path.join(HERE, "fonts", file)).toString("base64")})}`;
const FONTS = [
  font("S", "sofia-sans-extra-condensed-greek-900-normal.woff2", 900), font("S", "sofia-sans-extra-condensed-latin-900-normal.woff2", 900),
  font("F", "fira-sans-extra-condensed-greek-700-normal.woff2", 700), font("F", "fira-sans-extra-condensed-latin-700-normal.woff2", 700),
  font("F", "fira-sans-extra-condensed-greek-800-normal.woff2", 800), font("F", "fira-sans-extra-condensed-latin-800-normal.woff2", 800),
].join("");
const uri = (buf, type = "image/jpeg") => `data:${type};base64,${buf.toString("base64")}`;

// ---------------------------------------------------------------- 1. λήψεις από την εφαρμογή

const server = http.createServer((req, res) => {
  const f = path.join(DOCS, decodeURIComponent(req.url.split("?")[0]).replace(/\/$/, "/index.html"));
  if (!f.startsWith(DOCS) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  const ext = path.extname(f);
  res.writeHead(200, { "Content-Type": { ".html": "text/html", ".json": "application/json", ".png": "image/png", ".js": "text/javascript" }[ext] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
}).listen(0);
const base = `http://localhost:${server.address().port}/`;
const data = JSON.parse(fs.readFileSync(path.join(DOCS, "matches.json"), "utf8"));
const now = new Date().toISOString();
const pick = () => data.matches.find((m) => m.nt === args.nt) ||
  data.matches.filter((m) => m.start > now && m.live && m.section === "football").sort((a, b) => a.start.localeCompare(b.start))[0] ||
  data.matches.filter((m) => m.start > now && m.live).sort((a, b) => a.start.localeCompare(b.start))[0];

const browser = await (await chromium()).launch();

// Οι λήψεις μπορούν να γίνουν χωριστά (--capture dir, π.χ. στο GitHub, όπου φορτώνουν τα σήματα)
// και το μοντάζ αλλού (--from dir).
const SHOTS = ["home", "menu", "sectionTop", "matchOff", "matchPre", "matchLive"];
let shots;
if (args.from) {
  shots = JSON.parse(fs.readFileSync(path.join(args.from, "meta.json"), "utf8"));
  for (const k of SHOTS) shots[k] = fs.readFileSync(path.join(args.from, `${k}.jpg`));
} else {
  shots = await capture();
  if (args.capture) {
    fs.mkdirSync(args.capture, { recursive: true });
    const meta = { ...shots };
    for (const k of SHOTS) { fs.writeFileSync(path.join(args.capture, `${k}.jpg`), shots[k]); delete meta[k]; }
    fs.writeFileSync(path.join(args.capture, "meta.json"), JSON.stringify(meta, null, 1));
    console.log("Λήψεις →", args.capture);
    await browser.close(); server.close(); process.exit(0);
  }
}
const { home, menu, sectionTop, matchOff, matchPre, matchLive, menuBtn, sectionLink, sectionScroll, matchLink, notifyTop, sw, match } = shots;
const opponent = match.paokHome ? match.away : match.home;
console.log("Αγώνας:", match.home, "–", match.away, match.start);

async function capture() {
  const match = pick();
  const page = await browser.newPage({ viewport: { width: 440, height: 956 }, deviceScaleFactor: DSF, isMobile: true, hasTouch: true,
  timezoneId: "Europe/Athens", locale: "el-GR" });
  await page.route(/\/api\/|_vercel/, (r) => r.abort());
  const shot = async (opts = {}) => page.screenshot({ type: "jpeg", quality: 92, ...opts });
  const box = async (sel) => { const b = await page.locator(sel).first().boundingBox(); return b && { x: b.x + b.width / 2, y: b.y + b.height / 2 }; };
  const settle = () => page.waitForTimeout(900);

  await page.goto(base + "#/"); await settle();
  const home = await shot();
  const menuBtn = await box("#menu-btn");
  await page.click("#menu-btn"); await page.waitForTimeout(500);
  const menu = await shot();
  const sectionHref = `#/${match.section}`;
  const sectionLink = await box(`#menu-panel a[href="${sectionHref}"]`);
  await page.keyboard.press("Escape");
  await page.goto(base + sectionHref); await settle();
  await page.locator(`a[href="#/m/${match.nt}"]`).first().scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollBy(0, 120));
  await page.waitForTimeout(300);
  const sectionScroll = await page.evaluate(() => window.scrollY);
  await page.evaluate(() => window.scrollTo(0, 0)); await page.waitForTimeout(200);
  const sectionTop = await shot({ fullPage: true });
  const matchLink = await page.evaluate((nt) => {
    const r = document.querySelector(`a[href="#/m/${nt}"]`).getBoundingClientRect();
    const name = document.querySelector(`a[href="#/m/${nt}"] .teams, a[href="#/m/${nt}"] strong`)?.getBoundingClientRect() || r;
  return { x: name.left + Math.min(name.width, 160) / 2 + 10, y: r.top + window.scrollY + r.height / 2 };
  }, match.nt);

  await page.goto(base + "#/m/" + match.nt); await settle();
  // Οι ειδοποιήσεις όπως σε iPhone με την εφαρμογή στην αρχική οθόνη (εδώ ο browser δεν έχει push).
  await page.evaluate(() => {
    const s = document.querySelector("#match-notify");
    s.querySelectorAll(".explain, .push-note, .push-on").forEach((e) => e.remove());
    s.querySelectorAll(".switch").forEach((b) => { b.disabled = false; b.style.transition = "none"; });
  });
  const notifyTop = await page.evaluate(() => document.querySelector("#match-notify").getBoundingClientRect().top + scrollY);
  const sw = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll("#match-notify .switch")].map((b) => {
    const r = b.getBoundingClientRect(); return [b.getAttribute("aria-label"), { x: r.left + r.width / 2, y: r.top + scrollY + r.height / 2 }];
  })));
  const setOn = (labels) => page.evaluate((labels) => document.querySelectorAll("#match-notify .switch")
    .forEach((b) => b.setAttribute("aria-checked", String(labels.includes(b.getAttribute("aria-label"))))), labels);
  const matchOff = await shot({ fullPage: true });
  await setOn(["Πριν τον αγώνα"]);
  const matchPre = await shot({ fullPage: true });
  await setOn(["Πριν τον αγώνα", "Live"]);
  const matchLive = await shot({ fullPage: true });
  return { home, menu, sectionTop, matchOff, matchPre, matchLive, menuBtn, sectionLink, sectionScroll, matchLink, notifyTop, sw, match };
}
const icon = fs.readFileSync(path.join(DOCS, "icons", "icon-192.png"));


// ---------------------------------------------------------------- 2. οι σκηνές

const scrollTo = Math.max(0, notifyTop - 150);
const T = (t) => t;  // δευτερόλεπτα μέσα στη σκηνή
// Πιο αργός ρυθμός: κάθε οθόνη μένει ~1″ πριν το πάτημα, ώστε να φαίνεται τι γίνεται (~21″ συνολικά).
const H0 = HOMESCREEN ? 1.4 : 0;   // πόσο κρατά η αρχική οθόνη του κινητού
const scenes = [
  { name: "1-hook", dur: 3.2, lock: true, caption: ["Μάθε για το γκολ", "πριν το δεις στην TV"],
    zoom: [[0, 1], [3.2, 1.06]] },
  { name: "2-choose", dur: H0 + 5.2, caption: ["1", "Διάλεξε αγώνα"],
    screens: [...(HOMESCREEN ? [{ t: 0, src: "homescreen" }] : []), { t: H0, src: "home" }, { t: H0 + 1.25, src: "menu" },
      { t: H0 + 2.5, src: "section", y0: 0, y1: sectionScroll, ys: H0 + 2.9, ye: H0 + 4.2 }],
    taps: [...(HOMESCREEN ? [{ t: 1.1, x: ICON_AT[0] / DSF, y: ICON_AT[1] / DSF }] : []), { t: H0 + 0.95, ...menuBtn },
      { t: H0 + 2.2, ...sectionLink }, { t: H0 + 4.85, x: matchLink.x, y: matchLink.y - sectionScroll }] },
  { name: "3-notify", dur: 3.0, caption: ["2", "Πάτα «Ειδοποιήσεις»"],
    screens: [{ t: 0, src: "matchOff", y0: 0, y1: scrollTo, ys: 0.8, ye: 2.3 }] },
  { name: "4-live", dur: 4.6, caption: ["3", "Live σε κάθε γκολ"],
    screens: [{ t: 0, src: "matchOff", y0: scrollTo, y1: scrollTo }, { t: 1.65, src: "matchPre", y0: scrollTo, y1: scrollTo, fade: 0 },
      { t: 3.15, src: "matchLive", y0: scrollTo, y1: scrollTo, fade: 0 }],
    taps: [{ t: 1.5, x: sw["Πριν τον αγώνα"].x, y: sw["Πριν τον αγώνα"].y - scrollTo },
      { t: 3.0, x: sw["Live"].x, y: sw["Live"].y - scrollTo }],
    zoomOn: { x: 220, y: (sw["Πριν τον αγώνα"].y + sw["Live"].y) / 2 - scrollTo },
    zoom: [[0, 1], [0.8, 1.42], [4.6, 1.5]] },
  { name: "5-end", dur: 3.5, end: true },
];

const css = `${FONTS}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:${W}px;height:${H}px;overflow:hidden;background:#0a0a0a}
#bg{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 30%,#2a2a2a 0%,#0b0b0b 62%,#050505 100%)}
#stripes{position:absolute;inset:0;background:repeating-linear-gradient(90deg,rgba(255,255,255,.035) 0 46px,transparent 46px 92px)}
#cap{position:absolute;left:0;right:0;top:0;padding:120px 0 90px;text-align:center;color:#fff;z-index:10;
  background:linear-gradient(180deg,rgba(8,8,8,.96) 0%,rgba(8,8,8,.9) 70%,rgba(8,8,8,0) 100%)}
#cap .n{font:900 120px/0.8 S;letter-spacing:-2px;color:#fff;opacity:.9}
#cap .l{font:900 104px/0.92 S;text-transform:uppercase;letter-spacing:-1px}
#cap .l2{font:900 104px/0.92 S;text-transform:uppercase;letter-spacing:-1px;color:#bdbdbd}
#stage{position:absolute;left:0;top:0;width:${W}px;height:${H}px;transform-origin:0 0;z-index:1}
#phone{position:absolute;left:${(W - 700) / 2 - 18}px;top:520px;width:736px;height:1557px;border-radius:96px;background:#111;
  box-shadow:0 0 0 3px #3a3a3a,0 40px 120px rgba(0,0,0,.8)}
#screen{position:absolute;left:18px;top:18px;width:700px;height:1521px;border-radius:80px;overflow:hidden;background:#fff}
#screen > img{position:absolute;left:0;top:0;width:700px}
#island{position:absolute;left:50%;top:30px;width:200px;height:56px;margin-left:-100px;border-radius:30px;background:#000;z-index:3}
.tap{position:absolute;width:120px;height:120px;margin:-60px 0 0 -60px;border-radius:50%;border:8px solid rgba(255,255,255,.95);
  background:rgba(0,0,0,.28);box-shadow:0 0 0 4px rgba(0,0,0,.35);z-index:4}
#lock{position:absolute;inset:0;background:linear-gradient(180deg,#1b1b1b,#050505) center/cover;display:none}
#lock.own .st{display:none}
#lock.own .date{top:134px;font:600 33px Inter,F;color:rgba(255,255,255,.92)}
#lock.own .clock{top:168px;font:700 200px/1 "Inter Display",Inter,F;letter-spacing:-6px;color:rgba(214,220,226,.74);
  text-shadow:0 2px 18px rgba(0,0,0,.25)}
#sbtime{position:absolute;left:56px;top:28px;width:100px;text-align:center;font:600 27px Inter,F;color:#fff;display:none;z-index:2}
#lock .st{position:absolute;inset:0;background:repeating-linear-gradient(90deg,rgba(255,255,255,.06) 0 38px,transparent 38px 76px)}
#lock .date{position:absolute;top:170px;width:100%;text-align:center;color:#ddd;font:700 40px F}
#lock .clock{position:absolute;top:210px;width:100%;text-align:center;color:#fff;font:800 230px/1 F;letter-spacing:-4px}
#notif{position:absolute;left:24px;right:24px;top:var(--ny,560px);padding:30px 32px;border-radius:44px;background:rgba(245,245,245,.92);
  display:flex;gap:26px;align-items:flex-start;color:#111}
#notif img{width:92px;height:92px;border-radius:22px;flex:none}
#notif .h{display:flex;justify-content:space-between;font:700 30px F;color:#555}
#notif .t{font:800 42px/1.1 F;margin-top:6px;color:#000}
#notif .b{font:700 34px/1.15 F;color:#333;margin-top:2px}
#example{position:absolute;left:0;right:0;top:calc(var(--ny,560px) + 186px);text-align:center;font:700 26px F;color:rgba(255,255,255,.85);
  text-shadow:0 1px 6px rgba(0,0,0,.9)}
#end{position:absolute;inset:0;display:none;text-align:center;color:#fff}
#end img{width:300px;height:300px;border-radius:66px;margin-top:470px;box-shadow:0 0 0 4px #fff}
#end .name{font:900 170px/1 S;margin-top:70px;letter-spacing:-2px}
#end .name span{color:#8f8f8f}
#end .sub{font:900 70px/1 S;color:#cfcfcf;margin-top:34px}
#end .url{display:inline-block;font:800 72px/1 F;margin-top:90px;padding:30px 54px;border:5px solid #fff}
#end .free{font:700 44px F;color:#9a9a9a;margin-top:44px}
`;
const html = `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body>
<div id="bg"></div><div id="stripes"></div>
<div id="cap"></div>
<div id="stage"><div id="phone"><div id="screen">
  <img id="a"><img id="b">
  <div id="lock"><div class="st"></div><div class="date"></div><div class="clock"></div>
    <div id="notif"><img src="${uri(icon, "image/png")}"><div style="flex:1"><div class="h"><span>PAOKalendar</span><span>τώρα</span></div>
    <div class="t">ΓΚΟΛ ΤΟΥ ΠΑΟΚ!</div><div class="b"></div></div></div></div>
  <div id="sbtime"></div><div id="island"></div><div class="tap" id="tap"></div>
</div></div></div>
<div id="end"><img src="${uri(icon, "image/png")}"><div class="name">PAOK<span>alendar</span></div>
  <div class="sub">ΟΛΑ ΤΑ ΤΜΗΜΑΤΑ, ΑΝΔΡΩΝ ΚΑΙ ΓΥΝΑΙΚΩΝ</div><div class="url">paokalendar.gr</div>
  <div class="free">Δωρεάν · Χωρίς λογαριασμό</div></div>
</body></html>`;

const IMGS = { homescreen: HOMESCREEN ? uri(HOMESCREEN, "image/png") : "", home: uri(home), menu: uri(menu), section: uri(sectionTop), matchOff: uri(matchOff), matchPre: uri(matchPre), matchLive: uri(matchLive) };
const clockTime = new Intl.DateTimeFormat("el-GR", { timeZone: "Europe/Athens", hour: "2-digit", minute: "2-digit", hourCycle: "h23" })
  .format(new Date(new Date(match.start).getTime() + 23 * 60000));
const dateText = new Intl.DateTimeFormat("el-GR", { timeZone: "Europe/Athens", weekday: "long", day: "numeric", month: "long" }).format(new Date(match.start));
const scoreLine = GOAL ? GOAL_BODY : match.paokHome ? `ΠΑΟΚ 1–0 ${opponent}` : `${opponent} 0–1 ΠΑΟΚ`;
const goalTitle = GOAL ? `ΓΚΟΛ ΤΟΥ ΠΑΟΚ! ${GOAL}` : "ΓΚΟΛ ΤΟΥ ΠΑΟΚ!";

const stage = await browser.newPage({ viewport: { width: W, height: H } });
await stage.setContent(html);
await stage.evaluate(({ IMGS, clockTime, dateText, scoreLine, goalTitle, DSF, lock }) => {
  document.querySelector("#notif .t").textContent = goalTitle;
  document.getElementById("sbtime").textContent = clockTime;
  window.IMGS = IMGS; window.DSF = DSF;
  if (lock) {
    const l = document.getElementById("lock");
    l.classList.add("own"); l.style.backgroundImage = `url(${lock})`;
    l.style.setProperty("--ny", "392px");
  }
  document.querySelector("#lock .clock").textContent = clockTime;
  document.querySelector("#lock .date").textContent = dateText.replace(/^./, (c) => c.toUpperCase());
  document.querySelector("#notif .b").textContent = scoreLine;
  const ease = (x) => (x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
  const K = 700 / 440;              // css px εφαρμογής → px οθόνης στο κινητό
  const SX = (1080 - 700) / 2, SY = 520 + 18;  // πού είναι η οθόνη στη σκηνή
  let lastCap = "";
  window.frame = (sc, t) => {
    // Λεζάντα: ανεβαίνει και εμφανίζεται στην αρχή της σκηνής.
    const cap = document.getElementById("cap");
    const key = (sc.caption || []).join("|");
    if (key !== lastCap) {
      lastCap = key;
      const [a, b] = sc.caption || [];
      // Κεφαλαία χωρίς τόνους (όπως στις εικόνες των social).
      const up = (x) => x.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
      cap.innerHTML = !a ? "" : /^\d$/.test(a) ? `<div class="n">${a}</div><div class="l">${up(b)}</div>` : `<div class="l">${up(a)}</div><div class="l2">${up(b)}</div>`;
    }
    const ci = ease(t / 0.35);
    cap.style.opacity = ci; cap.style.transform = `translateY(${(1 - ci) * 40}px)`;
    document.getElementById("end").style.display = sc.end ? "block" : "none";
    document.getElementById("phone").style.display = sc.end ? "none" : "block";
    if (sc.end) {
      const e = document.getElementById("end"), k = ease(t / 0.5);
      e.style.opacity = k; e.style.transform = `scale(${0.94 + 0.06 * k})`;
      return;
    }
    document.getElementById("lock").style.display = sc.lock ? "block" : "none";
    if (sc.lock) {
      const n = ease((t - 0.35) / 0.45);
      const notif = document.getElementById("notif");
      notif.style.transform = `translateY(${(1 - n) * -260}px) scale(${0.9 + 0.1 * n})`; notif.style.opacity = n;

    }
    // Οθόνες της εφαρμογής, με κύλιση.
    const a = document.getElementById("a"), b = document.getElementById("b");
    const list = sc.screens || [];
    let i = -1; list.forEach((s, j) => { if (s.t <= t) i = j; });
    const place = (img, s) => {
      if (!s) { img.style.display = "none"; return; }
      img.style.display = "block";
      if (img.dataset.src !== s.src) { img.src = IMGS[s.src]; img.dataset.src = s.src; }
      const p = s.ys === undefined ? 1 : ease((t - s.ys) / (s.ye - s.ys));
      const y = (s.y0 || 0) + ((s.y1 ?? s.y0 ?? 0) - (s.y0 || 0)) * p;
      img.style.transform = `translateY(${-y * K}px)`;
      return y;
    };
    const cur = list[i], prev = list[i - 1];
    document.getElementById("sbtime").style.display = cur && cur.src === "homescreen" ? "block" : "none";
    const fade = cur && prev && cur.fade !== 0 ? Math.min(1, (t - cur.t) / 0.15) : 1;
    place(b, fade < 1 ? prev : null);
    const y = place(a, cur);
    a.style.opacity = fade;
    // Πάτημα: κύκλος που μικραίνει πάνω στο σημείο και μετά σβήνει.
    const tap = document.getElementById("tap");
    const tp = (sc.taps || []).filter((p) => t >= p.t - 0.25 && t <= p.t + 0.35).pop();
    if (tp) {
      const u = (t - (tp.t - 0.25)) / 0.6;
      tap.style.display = "block";
      tap.style.left = tp.x * K + "px"; tap.style.top = tp.y * K + "px";
      tap.style.opacity = u < 0.15 ? u / 0.15 : u > 0.7 ? (1 - u) / 0.3 : 1;
      tap.style.transform = `scale(${u < 0.42 ? 1.25 - 0.6 * (u / 0.42) : 0.65 + 0.5 * ((u - 0.42) / 0.58)})`;
    } else tap.style.display = "none";
    // Ζουμ της σκηνής: [χρόνος, κλίμακα] με κέντρο ένα σημείο της οθόνης ή της σκηνής.
    const z = sc.zoom || [[0, 1]];
    let s = z[0][1];
    for (let j = 1; j < z.length; j++) if (t >= z[j - 1][0]) s = z[j - 1][1] + (z[j][1] - z[j - 1][1]) * ease((t - z[j - 1][0]) / (z[j][0] - z[j - 1][0]));
    if (z.length === 1) s = z[0][1];
    const cx = sc.zoomOn ? SX + sc.zoomOn.x * K : 540, cy = sc.zoomOn ? SY + sc.zoomOn.y * K : 1180;
    const tx = 540 - cx * s, ty = (sc.zoomOn ? 1250 : 1180) - cy * s;
    const k = sc.zoomOn ? ease(t / 0.8) : 0;
    const st = document.getElementById("stage");
    if (sc.zoomOn) st.style.transform = `translate(${tx * k}px,${ty * k + (1 - k) * 0}px) scale(${1 + (s - 1) * k})`;
    else st.style.transform = `translate(${540 - 540 * s}px,${1060 - 1060 * s}px) scale(${s})`;
  };
}, { IMGS, clockTime: CLOCK || clockTime, dateText: DATE || dateText, scoreLine, goalTitle, DSF, lock: LOCK ? uri(LOCK, "image/png") : "" });
await stage.evaluate(() => document.fonts.ready);

// ---------------------------------------------------------------- 3. καρέ → βίντεο

const only = args.frames;  // --frames 1-hook:1.2,4-live:2.5 : μόνο αυτά τα καρέ ως JPEG, για έλεγχο
if (only) {
  for (const spec of only.split(",")) {
    const [name, t] = spec.split(":");
    await stage.evaluate(([sc, t]) => frame(sc, t), [scenes.find((s) => s.name === name), +t]);
    fs.writeFileSync(path.join(OUT, `frame-${name}-${t}.jpg`), await stage.screenshot({ type: "jpeg", quality: 92 }));
  }
} else {
  const files = [];
  for (const sc of scenes) {
    const tmp = path.join(OUT, `${sc.name}.part.mp4`), done = path.join(OUT, `${sc.name}.mp4`);
    const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-",
      "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", String(FPS), tmp], { stdio: ["pipe", "inherit", "inherit"] });
    const n = Math.round(sc.dur * FPS);
    for (let f = 0; f < n; f++) {
      await stage.evaluate(([sc, t]) => frame(sc, t), [sc, f / FPS]);
      const jpg = await stage.screenshot({ type: "jpeg", quality: 92 });
      if (!ff.stdin.write(jpg)) await new Promise((r) => ff.stdin.once("drain", r));
          }
    ff.stdin.end();
    const code = await new Promise((r) => ff.on("close", r));
    if (code !== 0) throw new Error(`ffmpeg ${sc.name}: ${code}`);
    fs.renameSync(tmp, done);
    files.push(done);
    console.log(sc.name, n, "καρέ");
  }
  // Εξώφυλλο: η ειδοποίηση στην κλειδωμένη οθόνη.
  await stage.evaluate(([sc]) => frame(sc, 2.6), [scenes[0]]);
  fs.writeFileSync(path.join(OUT, "cover.jpg"), await stage.screenshot({ type: "jpeg", quality: 92 }));
  fs.writeFileSync(path.join(OUT, "list.txt"), files.map((f) => `file '${f}'`).join("\n"));
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", path.join(OUT, "list.txt"), "-c", "copy",
    "-movflags", "+faststart", path.join(OUT, "reel.part.mp4")]);
  fs.renameSync(path.join(OUT, "reel.part.mp4"), path.join(OUT, "reel.mp4"));
  for (const f of files) fs.rmSync(f);
  fs.rmSync(path.join(OUT, "list.txt"));
  console.log("→", path.join(OUT, "reel.mp4"));
}
await browser.close();
server.close();
