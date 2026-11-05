import fs from "node:fs"; import { chromium } from "playwright";
fs.mkdirSync("docs/ig", { recursive: true });
const img = (n) => `data:image/png;base64,${fs.readFileSync(`ig/${n}.png`).toString("base64")}`;
const slides = [
  ["1-paokalendar", null, "Όλος ο ΠΑΟΚ σε μία εφαρμογή", "Πρόγραμμα, αποτελέσματα, live και ειδοποιήσεις για όλα τα τμήματα", ["home", "match", "match-volley"]],
  ["2-tmimata", "Όλα τα τμήματα", "Ποδόσφαιρο, μπάσκετ, βόλεϊ, χάντμπολ, πόλο, futsal — ανδρών και γυναικών", "", ["menu", "handball-women", "standings"]],
  ["3-eidopoiiseis", "Ειδοποιήσεις", "1 ώρα πριν, σε κάθε γκολ ή περίοδο και στο τελικό. Εσύ διαλέγεις τι θέλεις.", "", ["notifications2", "upcoming", "calendars"]],
  ["4-programma", "Το πρόγραμμα", "Όλοι οι αγώνες σε μία λίστα, με ώρα, κανάλι και βαθμολογίες", "", ["home-list", "results-list", "standings-table"]],
];
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1080, height: 1350 } });
for (const [file, title, sub, sub2, shots] of slides) {
  const cover = !title;
  const phones = shots.map((s, i) => `<div class="phone p${i}"><img src="${img(s)}"></div>`).join("");
  await p.setContent(`<!doctype html><html><head><meta charset="utf-8">
  <link href="https://fonts.googleapis.com/css2?family=Fira+Sans+Extra+Condensed:wght@800&family=Fira+Sans:wght@400;500;600&display=block&subset=greek" rel="stylesheet">
  <style>*{box-sizing:border-box;margin:0}
  body{width:1080px;height:1350px;overflow:hidden;position:relative;background:repeating-linear-gradient(90deg,#000 0 60px,#fff 60px 120px)}
  .card{position:absolute;left:60px;right:60px;top:60px;background:#fff;border:12px solid #000;padding:44px 52px 48px}
  .brand{font:800 44px/1 'Fira Sans Extra Condensed';margin-bottom:22px}.brand span,.big span{color:#66655f}
  h1{font:800 104px/0.95 'Fira Sans Extra Condensed';letter-spacing:-1px;margin-bottom:22px}
  .big{font:800 150px/0.9 'Fira Sans Extra Condensed';letter-spacing:-2px;margin-bottom:24px}
  p{font:500 36px/1.3 'Fira Sans';color:#222}
  .sub2{margin-top:14px;font-weight:400;color:#555;font-size:32px}
  .phone{position:absolute;width:300px;height:649px;background:#000;border-radius:44px;padding:11px;box-shadow:0 26px 60px rgba(0,0,0,.45)}
  .phone img{width:100%;height:100%;object-fit:cover;object-position:top;border-radius:34px;display:block}
  .p0{left:68px;top:${cover ? 640 : 610}px}.p1{left:390px;top:${cover ? 590 : 560}px}.p2{left:712px;top:${cover ? 640 : 610}px}
  .url{position:absolute;left:0;right:0;bottom:0;height:64px;background:#000;color:#fff;font:600 30px/64px 'Fira Sans';text-align:center;letter-spacing:.5px}
  </style></head><body>
  <div class="card">${cover ? `<div class="big">PAOK<span>alendar</span></div><p>${sub}</p><p class="sub2">${sub2}</p>`
    : `<div class="brand">PAOK<span>alendar</span></div><h1>${title}</h1><p>${sub}</p>`}</div>
  ${phones}<div class="url">paokalendar.vercel.app · ανεπίσημη σελίδα φιλάθλων</div></body></html>`);
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(800);
  await p.screenshot({ path: `docs/ig/${file}.png` });
}
await b.close();
