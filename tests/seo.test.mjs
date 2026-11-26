// Καθαρές διευθύνσεις, σελίδες για τις μηχανές αναζήτησης και sitemap (docs/seo.js, api/page.js, api/sitemap.js).
import test from "node:test";
import assert from "node:assert/strict";

const sections = [
  { key: "football", name: "Ποδόσφαιρο", sport: "Ποδόσφαιρο" },
  { key: "basketball-women", name: "Μπάσκετ Γυναικών", sport: "Μπάσκετ", women: true },
  { key: "football-u19", name: "Κ19", sport: "Ποδόσφαιρο", academy: true },
  { key: "football-b", name: "ΠΑΟΚ Β", sport: "Ποδόσφαιρο", academy: true },
];
const future = new Date(Date.now() + 3 * 86400e3).toISOString();
const past = new Date(Date.now() - 3 * 86400e3).toISOString();
const matches = [
  { section: "football", nt: "0123456789", home: "ΠΑΟΚ", away: "Άρης", start: future, timeKnown: true, competition: "Super League", venue: "Τούμπα", tv: "Cosmote Sport 1", score: "" },
  { section: "football", nt: "abcdefabcd", home: "Ολυμπιακός", away: "ΠΑΟΚ", start: past, timeKnown: true, competition: "Super League", score: "0-2" },
];
globalThis.fetch = async () => ({ ok: true, json: async () => ({ sections, matches, updated: { football: "2026-11-26T10:00+02:00" } }) });
const { build } = await import("../api/page.js");
const { buildSitemap } = await import("../api/sitemap.js");
const { loadSeo } = await import("../api/_seo.js");
const S = await loadSeo();

test("διευθύνσεις ↔ #/...", () => {
  assert.equal(S.slugify("Ολυμπιακός Σ.Φ.Π."), "olympiakos-s-f-p");
  assert.equal(S.matchSlug(matches[0]), "paok-aris-0123456789");
  assert.equal(S.hashFor("/podosfairo"), "#/football");
  assert.equal(S.hashFor("akadimia-football-u19"), "#/football-u19");
  assert.equal(S.hashFor("paok-aris-0123456789"), "#/m/0123456789");
  assert.equal(S.hashFor("programma"), "#/program");
  assert.equal(S.hashFor("kati-allo"), null);
  assert.equal(S.pathFor("#/m/0123456789", matches[0]), "/paok-aris-0123456789");
  assert.equal(S.pathFor("#/football"), "/podosfairo");
  assert.equal(S.pathFor("#/history/trophies"), "/tropaia");
  assert.equal(S.pathFor("#/profile"), null);
  assert.equal(S.pathFor("#/football/standings"), null);
  // Κάθε τμήμα και σελίδα γυρίζει στην ίδια διεύθυνση.
  for (const k of Object.keys(S.SECTIONS)) assert.equal(S.hashFor(S.sectionSlug(k)), "#/" + k);
  for (const p of Object.keys(S.PAGES)) assert.equal(S.pathFor(S.PAGES[p]), "/" + p);
});

test("τίτλοι", () => {
  assert.equal(S.sectionLabel(sections[1]), "ΠΑΟΚ Μπάσκετ Γυναικών");
  assert.equal(S.sectionLabel(sections[2]), "ΠΑΟΚ Ποδόσφαιρο Κ19");
  assert.equal(S.sectionLabel(sections[3]), "ΠΑΟΚ Β");
  assert.match(S.matchTitle(matches[1]), /^Ολυμπιακός 0-2 ΠΑΟΚ, /);
});

test("σελίδα τμήματος", async () => {
  const { status, html } = await build("podosfairo");
  assert.equal(status, 200);
  assert.match(html, /<title>ΠΑΟΚ Ποδόσφαιρο: πρόγραμμα/);
  assert.match(html, /<link rel="canonical" href="https:\/\/paokalendar.gr\/podosfairo">/);
  assert.match(html, /href="\/paok-aris-0123456789"/);
  assert.match(html, /Ολυμπιακός 0-2 ΠΑΟΚ/);
});

test("σελίδα αγώνα με SportsEvent", async () => {
  const { status, html } = await build("paok-aris-0123456789");
  assert.equal(status, 200);
  assert.match(html, /"@type":"SportsEvent"/);
  assert.match(html, /Γήπεδο: Τούμπα/);
  // Ο ίδιος αγώνας με άλλα ονόματα στη διεύθυνση: canonical στη σωστή.
  const other = await build("0123456789");
  assert.match(other.html, /canonical" href="https:\/\/paokalendar.gr\/paok-aris-0123456789"/);
});

test("άγνωστη σελίδα: 404 και noindex", async () => {
  for (const slug of ["den-yparxei", "x-ffffffffff"]) {
    const { status, html } = await build(slug);
    assert.equal(status, 404);
    assert.match(html, /<meta name="robots" content="noindex">/);
    assert.doesNotMatch(html, /rel="canonical"/);
  }
});

test("sitemap", async () => {
  const xml = await buildSitemap();
  for (const u of ["/", "/podosfairo", "/akadimia-football-u19", "/programma", "/paok-aris-0123456789", "/olympiakos-paok-abcdefabcd"])
    assert.ok(xml.includes(`<loc>https://paokalendar.gr${u}</loc>`), u);
  assert.ok(xml.includes("<lastmod>2026-11-26</lastmod>"));
});
