// Κοινά για τις σελίδες που βλέπουν οι μηχανές αναζήτησης (api/page.js, api/sitemap.js).
// Οι διευθύνσεις και οι τίτλοι είναι στο docs/seo.js (το ίδιο αρχείο φορτώνει και η σελίδα).
import fs from "node:fs/promises";
import path from "node:path";
import vm from "node:vm";

export const SITE = "https://paokalendar.gr";
const RAW = "https://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/data/";

// Τα αρχεία του docs/ μπαίνουν στη λειτουργία με το includeFiles του vercel.json· αν λείπουν, από το site.
async function readDoc(name) {
  try {
    return await fs.readFile(path.join(process.cwd(), "docs", name), "utf8");
  } catch {
    const r = await fetch(`${SITE}/${name}`);
    if (!r.ok) throw new Error(`${name}: ${r.status}`);
    return r.text();
  }
}

let seoPromise = null;
export function loadSeo() {
  seoPromise ??= readDoc("seo.js").then((code) => {
    const ctx = {};
    vm.runInNewContext(code + "\nthis.PKSEO = PKSEO;", ctx);
    return ctx.PKSEO;
  }).catch((e) => { seoPromise = null; throw e; });
  return seoPromise;
}

let shellPromise = null;
export function loadShell() {
  shellPromise ??= readDoc("index.html").catch((e) => { shellPromise = null; throw e; });
  return shellPromise;
}

// Το πρόγραμμα: 1 λεπτό στη μνήμη της λειτουργίας (το CDN κρατά και τη σελίδα).
let cache = { at: 0, data: null };
export async function loadMatches() {
  if (cache.data && Date.now() - cache.at < 60_000) return cache.data;
  try {
    const r = await fetch(`${RAW}matches.json?t=${Math.floor(Date.now() / 60000)}`, {
      headers: { "User-Agent": "PAOKalendar (+https://paokalendar.gr)" },
    });
    if (!r.ok) throw new Error(`GitHub ${r.status}`);
    cache = { at: Date.now(), data: await r.json() };
  } catch (e) {
    if (!cache.data) throw e;
  }
  return cache.data;
}

export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
