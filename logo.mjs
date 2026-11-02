import fs from "node:fs"; import { chromium } from "playwright";
fs.mkdirSync("docs/logo", { recursive: true });
const font = `<link href="https://fonts.googleapis.com/css2?family=Fira+Sans+Extra+Condensed:wght@800&family=Fira+Sans:wght@400;500&display=block&subset=greek" rel="stylesheet">`;
// Το εικονίδιο σε 512 μονάδες: 9 ρίγες, πλαίσιο με «PK».
const icon = (size) => `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 512 512">
  <rect width="512" height="512" fill="#fff"/>${[0,2,4,6,8].map(i => `<rect x="${i*512/9}" width="${512/9}" height="512" fill="#000"/>`).join("")}
  <rect x="82" y="137" width="348" height="240" fill="#000"/><rect x="96" y="151" width="320" height="212" fill="#fff"/>
  <text x="256" y="314" text-anchor="middle" font-family="Fira Sans Extra Condensed" font-weight="800" font-size="168" letter-spacing="-2">PK</text></svg>`;
const stripes = (w) => `repeating-linear-gradient(90deg,#000 0 ${w}px,#fff ${w}px ${2*w}px)`;
const wordmark = (px, gray = "#66655f", ink = "#000") => `<span style="font:800 ${px}px/0.9 'Fira Sans Extra Condensed';letter-spacing:-.01em;color:${ink}">PAOK<span style="color:${gray}">alendar</span></span>`;
const scenes = {
  "1-eikonidio-2048": [2048, 2048, `<body style="margin:0">${icon(2048)}</body>`],
  "2-eikonidio-se-gkri-1920x1080": [1920, 1080, `<body style="margin:0;background:#e9e8e3;display:grid;place-items:center;height:1080px">
    <div style="box-shadow:0 30px 70px rgba(0,0,0,.25);border-radius:120px;overflow:hidden;width:560px;height:560px">${icon(560)}</div></body>`],
  "3-logo-me-rigés-1920x1080": [1920, 1080, `<body style="margin:0;height:1080px;background:${stripes(64)};display:grid;place-items:center">
    <div style="background:#fff;border:14px solid #000;padding:46px 80px 56px">${wordmark(210)}</div></body>`],
  "4-logo-se-mavro-1920x1080": [1920, 1080, `<body style="margin:0;height:1080px;background:#000;display:flex;align-items:center;justify-content:center;gap:80px">
    <div style="width:420px;height:420px;border-radius:90px;overflow:hidden;outline:4px solid #fff">${icon(420)}</div>
    <div>${wordmark(190, "#a9a79e", "#fff")}<div style="font:400 44px/1.3 'Fira Sans';color:#cfcdc6;margin-top:22px">Όλος ο ΠΑΟΚ σε μία εφαρμογή</div></div></body>`],
  "5-logo-se-lefko-1920x1080": [1920, 1080, `<body style="margin:0;height:1080px;background:#fff;display:flex;align-items:center;justify-content:center;gap:80px">
    <div style="width:420px;height:420px;border-radius:90px;overflow:hidden;box-shadow:0 24px 60px rgba(0,0,0,.22)">${icon(420)}</div>
    <div>${wordmark(190)}<div style="font:400 44px/1.3 'Fira Sans';color:#555;margin-top:22px">Όλος ο ΠΑΟΚ σε μία εφαρμογή</div></div></body>`],
  "6-logo-diafano-2400": [2400, 560, `<body style="margin:0;background:transparent;display:flex;align-items:center;height:560px;padding:0 40px">${wordmark(330)}</body>`],
};
const b = await chromium.launch();
for (const [name, [w, h, body]] of Object.entries(scenes)) {
  const p = await b.newPage({ viewport: { width: w, height: h } });
  await p.setContent(`<!doctype html><html><head><meta charset="utf-8">${font}</head>${body}</html>`);
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(800);
  await p.screenshot({ path: `docs/logo/${name}.png`, omitBackground: name.includes("diafano") });
  await p.close();
}
fs.writeFileSync("docs/logo/eikonidio.svg", icon(512));
await b.close();
