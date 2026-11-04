import { chromium } from "playwright";
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1" });
const p = await ctx.newPage();
for (const r of ["#/handball", "#/handball/standings", "#/handball-women"]) {
  await p.goto("https://paokalendar.vercel.app/" + r); await p.waitForTimeout(4000);
  await p.evaluate(() => window.scrollTo(0, 600)); await p.waitForTimeout(2500);
  const st = await p.evaluate(() => { const im = [...document.querySelectorAll("img.crest")];
    return { total: im.length, ok: im.filter(i => i.complete && i.naturalWidth).length, hb: im.filter(i => i.src.includes("handball.org.gr")).length,
      initials: document.querySelectorAll(".initials").length }; });
  console.log(r, JSON.stringify(st));
  await p.screenshot({ path: `docs/live-${r.replace(/[#/]/g, "")}.png` });
}
await b.close();
