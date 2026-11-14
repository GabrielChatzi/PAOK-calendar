// Οι κανόνες του πλάνου social (social/week.mjs), χωρίς εικόνες.
import test from "node:test";
import assert from "node:assert/strict";
import { blockKey, cleanTeam, plan, row } from "../social/week.mjs";

const NAMES = { teams: { "football:Ολυμπιακός": { name: "Ολυμπιακός", logo: "olympiakos.png" } }, venues: {}, tv: { "ΣΚΑΪ / SPORT FM TV 1": "ΣΚΑΪ" } };
const M = (section, start, home, away, extra = {}) => ({
  section, start, home, away, paokHome: home === "ΠΑΟΚ", timeKnown: true, venue: "", tv: "", score: "",
  competition: "League", homeLogo: "", awayLogo: "", ...extra,
});
const find = (p, what, day) => p.items.find((i) => i.what === what && i.day === day);

test("Μπλοκ: η Δευτέρα πάει με το Σαββατοκύριακο, Τρίτη ως Παρασκευή μεσοβδόμαδο", () => {
  assert.deepEqual(blockKey("2026-11-07"), { key: "2026-11-07", kind: "weekend" });
  assert.deepEqual(blockKey("2026-11-09"), { key: "2026-11-07", kind: "weekend" });
  assert.deepEqual(blockKey("2026-11-10"), { key: "2026-11-10", kind: "midweek" });
  assert.deepEqual(blockKey("2026-11-13"), { key: "2026-11-10", kind: "midweek" });
});

test("Πρόγραμμα το βράδυ πριν, αποτελέσματα το πρωί μετά, ποτέ στο ίδιο post", () => {
  const ms = [
    M("basketball", "2026-11-07T17:30:00+02:00", "ΠΑΟΚ", "Vikos Falcons"),
    M("football", "2026-11-08T21:00:00+02:00", "Ολυμπιακός", "ΠΑΟΚ"),
    M("volley", "2026-11-09T19:30:00+02:00", "Καλαμάτα", "ΠΑΟΚ"),
    M("basketball", "2026-11-10T19:00:00+02:00", "Balkan", "ΠΑΟΚ"),
    M("volley", "2026-11-13T18:30:00+02:00", "ΠΑΟΚ", "Άρης"),
  ];
  const p = plan(ms, "2026-11-06", { names: NAMES });
  // Σαββατοκύριακο (Σάββατο–Δευτέρα): πρόγραμμα Παρασκευή 19:00, αποτελέσματα Τρίτη 09:00.
  const sched = find(p, "schedule", "2026-11-06");
  assert.equal(sched.time, "19:00");
  assert.deepEqual(sched.cards.map((c) => c.file), ["2026-11-07_2026-11-09"]);  // 3 αγώνες: μία κάρτα
  assert.match(sched.caption, /3 αγώνες σε 3 αθλήματα, από Σάββατο ως Δευτέρα, με το Ολυμπιακός–ΠΑΟΚ την Κυριακή στις 21:00/);
  assert.equal(find(p, "results", "2026-11-10").time, "09:00");
  // Μεσοβδόμαδο: πρόγραμμα Δευτέρα βράδυ, μετά το βόλεϊ της Δευτέρας (19:30 + ~2 ώρες).
  const mid = find(p, "schedule", "2026-11-09");
  assert.equal(mid.time, "22:00");
  assert.deepEqual(mid.cards.map((c) => c.file), ["2026-11-10_2026-11-13"]);  // 2 αγώνες: μία κάρτα
  assert.deepEqual(mid.cards[0].sections.map((x) => `${x.day} ${x.date}`), ["Τρίτη 10.11", "Παρασκευή 13.11"]);
  // Κάθε post έχει μόνο ένα είδος καρτών.
  for (const it of p.items.filter((i) => i.type === "post")) {
    assert.equal(new Set(it.cards.map((c) => c.kind)).size <= 1, true, it.title);
  }
  // Stories: πρωί κάθε μέρας αγώνα και αποτελέσματα μετά τον τελευταίο.
  assert.equal(find(p, "today", "2026-11-08").time, "09:00");
  assert.equal(find(p, "dayResults", "2026-11-08").time, "23:30");
  assert.equal(find(p, "dayResults", "2026-11-08").cards.length, 0);  // δεν έχει ακόμα σκορ
  // Reel: μέρα χωρίς post και χωρίς αγώνα (Τετάρτη ή Πέμπτη).
  const reel = p.items.find((i) => i.type === "reel");
  assert.ok(["2026-11-11", "2026-11-12"].includes(reel.day), reel.day);
});

test("Αποτελέσματα: μόνο όσοι αγώνες έχουν σκορ, και αναφέρονται όσοι λείπουν", () => {
  const ms = [
    M("basketball", "2026-10-31T17:30:00+02:00", "Ηρακλής", "ΠΑΟΚ", { score: "53-63" }),
    M("volley", "2026-10-31T18:00:00+02:00", "ΠΑΟΚ", "Κηφισιά", { score: "3-1" }),
    M("futsal", "2026-11-01T18:00:00+02:00", "ΠΑΟΚ", "Κορυδαλλός"),
  ];
  const r = find(plan(ms, "2026-11-02", { names: NAMES }), "results", "2026-11-02");
  assert.deepEqual(r.cards.map((c) => c.file), ["2026-10-31"]);
  assert.deepEqual(r.missing, ["ΠΑΟΚ – Κορυδαλλός"]);
  assert.match(r.caption, /2 νίκες σε 2 αγώνες/);
});

test("Γραμμή εικόνας: όνομα, σήμα, κανάλι, σκορ από την πλευρά του ΠΑΟΚ", () => {
  const r = row(M("football", "2026-11-08T21:00:00+02:00", "Ολυμπιακός", "ΠΑΟΚ",
    { score: "1-2", tv: "ΣΚΑΪ / SPORT FM TV 1", competition: "Super League" }), NAMES);
  assert.equal(r.opponent, "Ολυμπιακός");
  assert.match(r.logo, /social\/logos\/olympiakos\.png$/);
  assert.deepEqual([r.tv, r.time, r.home, r.us, r.them, r.competition], ["ΣΚΑΪ", "21:00", false, 2, 1, undefined]);
  assert.equal(row(M("basketball", "2026-11-10T19:00:00+02:00", "Balkan", "ΠΑΟΚ", { competition: "EuroCup" }), NAMES).competition, "EuroCup");
});

test("Καθάρισμα ονομάτων", () => {
  assert.equal(cleanTeam("Α.Ο.Καλαμάτα 80 Affidea"), "Καλαμάτα 80");
  assert.equal(cleanTeam("ΟΔΥΣΣΕΑΣ ΜΟΣΧΑΤΟΥ WFC"), "ΟΔΥΣΣΕΑΣ ΜΟΣΧΑΤΟΥ");
  assert.equal(cleanTeam("Γ.Α.Σ ΚΑΜΑΤΕΡΟΥ"), "ΚΑΜΑΤΕΡΟΥ");
  assert.equal(cleanTeam("ΣΑΛΑΜΙΝΑ ΓΣ"), "ΣΑΛΑΜΙΝΑ");
  assert.equal(cleanTeam("Balkan"), "Balkan");
});
