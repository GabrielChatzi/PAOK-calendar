// /sitemap.xml: η αρχική, οι σελίδες της εφαρμογής, κάθε τμήμα (και ακαδημίες) και κάθε αγώνας της σεζόν,
// με τις καθαρές διευθύνσεις του docs/seo.js. Φτιάχνεται από το τρέχον matches.json (κλάδος data).
import { SITE, loadSeo, loadMatches, esc } from "./_seo.js";

export async function buildSitemap() {
  const [S, data] = await Promise.all([loadSeo(), loadMatches()]);
  const day = (s) => String(s || "").slice(0, 10);
  const updated = new Date().toISOString().slice(0, 10);
  const urls = [[`${SITE}/`, updated, "1.0"]];
  for (const p of Object.keys(S.PAGES)) if (p !== "aporrito") urls.push([`${SITE}/${p}`, updated, "0.7"]);
  for (const s of data.sections || []) urls.push([`${SITE}/${S.sectionSlug(s.key)}`, day(data.updated?.[s.key]) || updated, s.academy ? "0.6" : "0.9"]);
  const now = Date.now();
  for (const m of data.matches || []) {
    // Οι αγώνες των επόμενων εβδομάδων είναι οι πιο σημαντικοί.
    const soon = Math.abs(new Date(m.start) - now) < 14 * 86400e3;
    urls.push([`${SITE}/${S.matchSlug(m)}`, null, soon ? "0.8" : "0.5"]);
  }
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
    urls.map(([loc, mod, pr]) => `  <url><loc>${esc(loc)}</loc>${mod ? `<lastmod>${mod}</lastmod>` : ""}<priority>${pr}</priority></url>`).join("\n") +
    `\n</urlset>\n`;
}

export default async function handler(req, res) {
  try {
    const xml = await buildSitemap();
    res.setHeader("Content-Type", "application/xml; charset=utf-8");
    res.setHeader("Cache-Control", "public, max-age=0, s-maxage=3600, stale-while-revalidate=3600, stale-if-error=86400");
    return res.status(200).send(xml);
  } catch (e) {
    res.setHeader("Cache-Control", "no-store");
    return res.status(502).send("Σφάλμα: " + e.message);
  }
}
