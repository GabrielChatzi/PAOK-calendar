// Έλεγχοι για τις functions της Vercel (τρέχουν στο tests.yml):  node --test tests/
// Οι πηγές αντικαθίστανται με ψεύτικες απαντήσεις, στη μορφή που είδαμε σε πραγματικούς αγώνες.
import assert from "node:assert/strict";
import { test } from "node:test";

process.env.MONGODB_URI = process.env.MONGODB_URI || "";
const live = (await import("../api/live.js")).default;
const data = (await import("../api/data.js")).default;
const lib = await import("../api/_lib.js");
const admin = await import("../api/admin.js");

// Ψεύτικο fetch: η πρώτη διεύθυνση που ταιριάζει δίνει την απάντηση.
function mockFetch(routes) {
  globalThis.fetch = async (url) => {
    const hit = routes.find(([re]) => re.test(String(url)));
    if (!hit) throw new Error(`χωρίς απάντηση για ${url}`);
    const body = typeof hit[1] === "string" ? hit[1] : JSON.stringify(hit[1]);
    return { ok: true, status: 200, text: async () => body, json: async () => JSON.parse(body),
      arrayBuffer: async () => Buffer.from(body) };
  };
}
function call(handler, query) {
  return new Promise((resolve) => {
    handler({ query }, {
      setHeader() {}, status(c) { this.c = c; return this; },
      json(o) { resolve({ status: this.c, body: o }); }, send(o) { resolve({ status: this.c, body: String(o) }); },
    });
  });
}
const KOE_Q = { src: "koe", cat: "ASM", gara: "65", tur: "A01", gru: "1", a: "1", b: "2" };
const koeRoutes = (status, q, r1, r2) => [
  [/\/token$/, { token: "t", expiresInSec: 900 }],
  [/schedulereferee/, { Schedule: [{ OraTurCode: "A01", OraTeamCodeA: "1", OraTeamCodeB: "2", OraStatus: status, OraResA: r1, OraResB: r2 }] }],
  [/resultsDBlikeJSON/, { r1, r2, q }],
];

test("ΚΟΕ: time-out στην 4η (st=2) δεν είναι τέλος όσο το πρόγραμμα λέει «σε εξέλιξη»", async () => {
  const q = [{ r1: "2", r2: "4", st: "2" }, { r1: "3", r2: "2", st: "2" }, { r1: "5", r2: "2", st: "2" }, { r1: "1", r2: "1", st: "2" }, { st: "0" }];
  mockFetch(koeRoutes(1, q, 11, 9));
  const { body } = await call(live, KOE_Q);
  assert.equal(body.state, "in");
  assert.equal(body.quarter, 4);
  assert.equal(body.done, 3);
});

test("ΚΟΕ: τέλος μόνο με OraStatus 2", async () => {
  const q = [1, 2, 3, 4].map(() => ({ r1: "3", r2: "2", st: "2" })).concat([{ st: "0" }]);
  mockFetch(koeRoutes(2, q, 12, 8));
  const { body } = await call(live, { ...KOE_Q, b: "2" });
  assert.equal(body.state, "post");
  assert.deepEqual([body.home, body.away], [12, 8]);
});

test("Data Project: σετ, πόντοι και τρέχον σετ, με αλλαγή γηπεδούχου", async () => {
  mockFetch([
    [/negotiate/, { ConnectionToken: "x" }], [/\/connect\?/, "{}"], [/\/start\?/, "{}"], [/\/abort\?/, "{}"],
    [/\/send\?/, { R: [{ ChampionshipMatchID: 752, HomeEmpty: "A.O. KIFISIA", GuestEmpty: "P.A.O.K.", Status: 1,
      WonSetHome: 0, WonSetGuest: 2, Set1Home: 23, Set1Guest: 25, Set2Home: 12, Set2Guest: 25, Set3Home: 9, Set3Guest: 5 }] }],
  ]);
  const { body } = await call(live, { src: "dp", fed: "eope", id: "752", side: "h" });
  assert.deepEqual([body.state, body.home, body.away, body.quarter, body.clock], ["in", 2, 0, 3, "5-9"]);
});

test("Data Project: χρυσό σετ στο τελικό", async () => {
  mockFetch([
    [/negotiate/, { ConnectionToken: "x" }], [/\/connect\?/, "{}"], [/\/start\?/, "{}"], [/\/abort\?/, "{}"],
    [/\/send\?/, { R: [{ ChampionshipMatchID: 9, HomeEmpty: "P.A.O.K.", GuestEmpty: "X", Status: 2, WonSetHome: 3, WonSetGuest: 1,
      Set1Home: 25, Set1Guest: 20, Set2Home: 25, Set2Guest: 20, Set3Home: 20, Set3Guest: 25, Set4Home: 25, Set4Guest: 22,
      GoldenSetPlayed: true, GoldenSetHome: 13, GoldenSetGuest: 15 }] }],
  ]);
  const { body } = await call(live, { src: "dp", fed: "eope", id: "9", side: "h" });
  assert.deepEqual(body.golden, { home: 13, away: 15 });
  assert.equal(body.note, "χρυσό σετ 13–15");
});

test("ΚΟΕ: αναβολή από το πρόγραμμα (MatReason)", async () => {
  mockFetch([
    [/\/token$/, { token: "t", expiresInSec: 900 }],
    [/schedulereferee/, { Schedule: [{ OraTurCode: "A01", OraTeamCodeA: "1", OraTeamCodeB: "3", OraStatus: 0, MatReason: "P", MatReasonDescr: "Αναβολή" }] }],
    [/resultsDBlikeJSON/, { r1: "", r2: "", q: [] }],
  ]);
  const { body } = await call(live, { ...KOE_Q, b: "3" });
  assert.deepEqual([body.state, body.off], ["pre", "Αναβολή"]);
});

test("Genius: στην αρχή της 3ης, done = 2 (όχι «Τέλος 3ης»)", async () => {
  const widget = `var html = ${JSON.stringify('<li class="spls_lsmatch "><a href="http://www.fibalivestats.com/webcast/ESAKE/9/"><span class="spls_matchstatus">Live</span><span class="teamname">IRA</span><span class="teamname">PBC</span></a></li>')};\n`;
  mockFetch([
    [/widget/, widget],
    [/data\/9\/data\.json/, { period: 3, clock: "09:50", tm: { 1: { name: "Iraklis BC", score: 31 }, 2: { name: "PAOK BC", score: 36 } },
      pbp: [{ actionType: "period", subType: "end", period: 2, s1: "31", s2: "36" }] }],
  ]);
  const today = new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Athens" });
  const { body } = await call(live, { src: "gs", key: "K", day: today, side: "a" });
  assert.equal(body.state, "in");
  assert.equal(body.done, 2);
});

test("Genius: στατιστικά παικτών και ομάδας (box), χωρίς όσους δεν αγωνίστηκαν", async () => {
  const widget = `var html = ${JSON.stringify('<li class="spls_lsmatch "><a href="http://www.fibalivestats.com/webcast/ESAKE/9/"><span class="spls_matchstatus">Final</span><span class="spls_datefield">8 Nov 2026</span><span class="teamname">PBC</span><span class="teamname">ARI</span></a></li>')};\n`;
  const pl = (o) => ({ firstName: "Nikos", familyName: "Papas", shirtNumber: 7, starter: 1, sMinutes: "25:13", sPoints: 18,
    sTwoPointersMade: 3, sTwoPointersAttempted: 6, sThreePointersMade: 3, sThreePointersAttempted: 5, sFreeThrowsMade: 3,
    sFreeThrowsAttempted: 4, sReboundsTotal: 5, sAssists: 4, sSteals: 1, sTurnovers: 2, sBlocks: 0, sFoulsPersonal: 3, ...o });
  mockFetch([
    [/widget/, widget],
    [/data\/9\/data\.json/, { period: 4, tm: {
      1: { name: "PAOK BC", score: 80, tot_sPoints: 80, tot_sTwoPointersMade: 20, tot_sTwoPointersAttempted: 40,
        pl: { 1: pl(), 2: pl({ familyName: "Bench", starter: 0, sMinutes: "0:00", sPoints: 0 }) } },
      2: { name: "Aris", score: 70, pl: { 1: pl({ familyName: "Other", sPoints: 9 }) } } },
      pbp: [{ actionType: "game", subType: "end", period: 4, s1: "80", s2: "70" }] }],
  ]);
  const { body } = await call(live, { src: "gs", key: "K", day: "2026-11-08", side: "h" });
  assert.equal(body.state, "post");
  assert.deepEqual(body.box.home.players.map((p) => [p.name, p.no, p.starter, p.min, p.pts, p.m3]), [["N. Papas", "7", true, "25:13", 18, 3]]);
  assert.equal(body.box.home.tot.pts, 80);       // από τα tot_s… της ομάδας
  assert.equal(body.box.home.tot.m2, 20);
  assert.equal(body.box.away.tot.pts, 9);        // χωρίς tot_s…: άθροισμα των παικτών
});

test("EHF: ημίχρονο από το σκορ ημιχρόνου, τέλος από isFinished", async () => {
  mockFetch([[/GetMatchDetails/, { matchDetails: { details: { isFinished: true, scoreDetails: "(14:16)" },
    statistics: { state: 2, homeStatistics: { totalGoals: 23 }, guestStatistics: { totalGoals: 33 } } } }]]);
  const { body } = await call(live, { src: "ehf", id: "202712020702020" });
  assert.equal(body.state, "post");
  assert.deepEqual(body.quarters, [{ home: 14, away: 16 }, { home: 9, away: 17 }]);
});

test("ΕΟΚ: ποτέ «τελικό» από το livescore (το «stopped» είναι και διάλειμμα)", async () => {
  const page = '<div class="competition-name text-center">ALLWYN WOMEN&#039;S BASKETBALL LEAGUE 1</div>' +
    '<div id="match-card-5" class="match-card"><div class="match-card-score-first-column"> <span>ΠΑΟΚ</span></div>' +
    '<div class="match-card-score-first-column"> <span>ΑΘΗΝΑΙΚΟΣ</span></div></div>';
  mockFetch([[/get-matches-info/, { data: [{ match_id: 5, livescore_state: "stopped", has_livescore_started: false,
    home_team_result: 70, visiting_team_result: 60, current_period: "Π4", minute: "00", second: "00" }] }], [/livescores\?date=/, page]]);
  const { body } = await call(live, { src: "eok", day: "2026-11-07", side: "h", comp: "WOMEN" });
  assert.equal(body.state, "in");
  assert.deepEqual([body.home, body.away], [70, 60]);
});

const EA_Q = { src: "ea", code: "EACLUB27", cat: "ASF", gara: "2", tur: "001", gru: "3", a: "URA", b: "PAOK" };
const eaRoutes = (status, periods) => [
  [/site\/token$/, { data: { token: "t" } }],
  [/get\/schedule\//, { Schedule: [{ OraCatCode: "ASF", OraGaraCode: "2", OraTurCode: "001", OraTeamCodeA: "URA",
    OraTeamCodeB: "PAOK", OraResA: 0, OraResB: 0, OraStatus: status, OraPeriods: null }] }],
  [/get\/results\/ASF\/2\/001\/3\/URA\/PAOK\?live=1/, { Results: [{ ResTeamCodeA: "URA", ResTeamCodeB: "PAOK",
    ResTeamA: periods.reduce((t, p) => t + (p[0] ?? 0), 0), ResTeamB: periods.reduce((t, p) => t + (p[1] ?? 0), 0),
    Periods: [0, 1, 2, 3, 4].map((i) => ({ PerNumber: i + 1, PerResA: periods[i]?.[0] ?? null, PerResB: periods[i]?.[1] ?? null,
      PerStatus: periods[i]?.[2] ?? null, PerGameTime: periods[i]?.[3] ?? "" })) }] }],
];

test("European Aquatics: σε εξέλιξη από τις περιόδους, ακόμα κι αν το πρόγραμμα λέει «0»", async () => {
  mockFetch(eaRoutes(0, [[7, 3, 2], [2, 1, 1, "04:12"]]));
  const { body } = await call(live, EA_Q);
  assert.deepEqual([body.state, body.home, body.away, body.quarter, body.done, body.clock], ["in", 9, 4, 2, 1, "04:12"]);
  assert.deepEqual(body.quarters[0], { home: 7, away: 3 });
});

test("European Aquatics: πριν την έναρξη και τελικό από το πρόγραμμα", async () => {
  mockFetch(eaRoutes(0, []));
  assert.equal((await call(live, EA_Q)).body.state, "pre");
  mockFetch(eaRoutes(2, [[7, 3, 2], [7, 4, 2], [5, 3, 2], [6, 5, 2]]));
  const { body } = await call(live, EA_Q);
  assert.deepEqual([body.state, body.home, body.away, body.done], ["post", 25, 15, 4]);
});

test("Διαχειριστής: το τελικό με το ίδιο κλειδί με το αυτόματο, το σκορ με το ίδιο κλειδί με τα γκολ", () => {
  const m = { nt: "abcdef0123", section: "futsal", home: "ΠΑΟΚ", away: "Κορυδαλλός", live: null, competition: "Futsal" };
  const fin = admin.message(m, { home: 7, away: 3, final: true, note: "" });
  assert.equal(fin.once, "abcdef0123-result");
  assert.equal(fin.payload.title, "🥅 Τελικό: ΠΑΟΚ 7–3 Κορυδαλλός");
  assert.ok(fin.topics.includes("m:abcdef0123:result") && fin.topics.includes("s:futsal:live"));
  const now = admin.message(m, { home: 1, away: 0, final: false, note: "" });
  assert.equal(now.once, admin.scoreKey("abcdef0123", 1, 0));
  assert.ok(now.topics.includes("s:futsal:pre"));  // χωρίς live: και σε όσους θέλουν την υπενθύμιση
  assert.ok(!admin.message({ ...m, live: { src: "espn" } }, { home: 1, away: 0 }).topics.includes("s:futsal:pre"));
});

test("Διαχειριστής: γεγονότα με τους τίτλους και τα κλειδιά του live.py", () => {
  const m = { nt: "abcdef0123", section: "football-women", home: "ΟΔΥΣΣΕΑΣ", away: "ΠΑΟΚ", paokHome: false,
    live: null, competition: "Α' Εθνική Γυναικών" };
  const ev = (body) => admin.message(m, admin.parseEvent(body));
  const goal = ev({ event: "goal", side: "away", home: 0, away: 1, minute: "23", scorer: "Παπαδοπούλου" });
  assert.equal(goal.payload.title, "⚽ ΓΚΟΛ ΤΟΥ ΠΑΟΚ! ΟΔΥΣΣΕΑΣ 0–1 ΠΑΟΚ");
  assert.equal(goal.payload.body, "23' Παπαδοπούλου");
  assert.equal(goal.once, "abcdef0123-s0-1");
  assert.equal(goal.payload.tag, undefined);
  const theirs = ev({ event: "goal", side: "home", home: 1, away: 1 });
  assert.equal(theirs.payload.title, "⚽ ΓΚΟΛ! ΟΔΥΣΣΕΑΣ 1–1 ΠΑΟΚ");
  assert.equal(theirs.payload.body, "Α' Εθνική Γυναικών");
  const half = ev({ event: "half", home: 1, away: 1 });
  assert.equal(half.payload.title, "⚽ Ημίχρονο: ΟΔΥΣΣΕΑΣ 1–1 ΠΑΟΚ");
  assert.equal(half.once, "abcdef0123-ht");
  const second = ev({ event: "second", home: 0, away: 2 });
  assert.equal(second.payload.title, "⚽ Ξεκίνησε το 2ο ημίχρονο: ΟΔΥΣΣΕΑΣ 0–2 ΠΑΟΚ");
  assert.equal(second.once, "abcdef0123-h2");
  assert.equal(ev({ event: "start", home: 0, away: 0 }).payload.title, "⚽ Ξεκίνησε: ΟΔΥΣΣΕΑΣ – ΠΑΟΚ");
  assert.equal(ev({ event: "disallowed", side: "away", home: 1, away: 1 }).once, "abcdef0123-x1-1");
  assert.ok(admin.parseEvent({ event: "goal", home: 1, away: 0 }).error);  // χωρίς ομάδα
  const wp = { ...m, section: "waterpolo-women", home: "ΠΑΟΚ", away: "ΝΟ ΛΑΡΙΣΗΣ", paokHome: true, live: { src: "koe" } };
  const p = (n, h, a) => admin.message(wp, admin.parseEvent({ event: "period", period: n, home: h, away: a }));
  assert.equal(p(2, 7, 4).payload.title, "🤽 Ημίχρονο: ΠΑΟΚ 7–4 ΝΟ ΛΑΡΙΣΗΣ");
  assert.equal(p(2, 7, 4).once, "abcdef0123-ht");
  assert.equal(p(3, 9, 6).payload.title, "🤽 Τέλος 3ης περιόδου: ΠΑΟΚ 9–6 ΝΟ ΛΑΡΙΣΗΣ");
  assert.equal(p(4, 9, 9).payload.title, "🤽 Ισοπαλία, πάμε στα πέναλτι: ΠΑΟΚ 9–9 ΝΟ ΛΑΡΙΣΗΣ");
  assert.deepEqual(p(3, 9, 6).topics, ["s:waterpolo-women:live", "m:abcdef0123:live"]);
  const vb = { ...wp, section: "volley-women" };
  const set = admin.message(vb, admin.parseEvent({ event: "period", period: 2, home: 2, away: 0, set: { home: 25, away: 21 } }));
  assert.equal(set.payload.title, "🏐 Τέλος 2ου σετ (25–21): ΠΑΟΚ 2–0 ΝΟ ΛΑΡΙΣΗΣ");
  assert.equal(set.once, "abcdef0123-set2");
  // Χωρίς event (παλιά μορφή): όπως πριν.
  assert.equal(admin.message(m, admin.parseEvent({ home: 2, away: 1, final: true })).payload.title, "⚽ Τελικό: ΟΔΥΣΣΕΑΣ 2–1 ΠΑΟΚ");
});

test("Διαχειριστής: γεγονότα ανά άθλημα και ελεύθερη ειδοποίηση", () => {
  const base = { nt: "abcdef0123", home: "ΠΑΟΚ", away: "ΑΡΗΣ", paokHome: true, live: null, competition: "Comp" };
  const ev = (section, body) => admin.message({ ...base, section }, admin.parseEvent(body));
  const t = (section, body) => ev(section, body).payload.title;
  assert.equal(t("basketball", { event: "goal", side: "home", points: 3, home: 45, away: 40 }), "🏀 ΤΡΙΠΟΝΤΟ ΤΟΥ ΠΑΟΚ! ΠΑΟΚ 45–40 ΑΡΗΣ");
  assert.equal(t("basketball", { event: "goal", side: "away", points: 2, home: 45, away: 42 }), "🏀 ΚΑΛΑΘΙ! ΠΑΟΚ 45–42 ΑΡΗΣ");
  assert.equal(t("basketball", { event: "goal", side: "home", points: 1, home: 46, away: 42 }), "🏀 ΒΟΛΗ ΤΟΥ ΠΑΟΚ! ΠΑΟΚ 46–42 ΑΡΗΣ");
  assert.equal(t("basketball", { event: "pstart", period: 3, home: 40, away: 38 }), "🏀 Ξεκίνησε η 3η περίοδος: ΠΑΟΚ 40–38 ΑΡΗΣ");
  assert.equal(t("basketball", { event: "pstart", period: 5, home: 80, away: 80 }), "🏀 Ξεκίνησε η παράταση: ΠΑΟΚ 80–80 ΑΡΗΣ");
  const pts = ev("volley-women", { event: "score", home: 1, away: 0, set: { home: 15, away: 12 } });
  assert.equal(pts.payload.title, "🏐 ΠΑΟΚ 1–0 ΑΡΗΣ (15–12 στο 2ο σετ)");
  assert.equal(pts.once, "abcdef0123-s1-0-p2-15-12");
  assert.notEqual(ev("volley-women", { event: "score", home: 1, away: 0, set: { home: 16, away: 12 } }).once, pts.once);
  // Με 3 σετ ο αγώνας τελείωσε: κανένα «4ο σετ».
  assert.equal(t("volley-women", { event: "score", home: 3, away: 0, set: { home: 0, away: 0 } }), "🏐 ΠΑΟΚ 3–0 ΑΡΗΣ");
  assert.equal(t("volley", { event: "pstart", period: 5, home: 2, away: 2 }), "🏐 Ξεκίνησε το τάι-μπρέικ: ΠΑΟΚ 2–2 ΑΡΗΣ");
  const red = ev("football", { event: "red", side: "away", minute: "60", scorer: "Παπαδόπουλος", home: 1, away: 0 });
  assert.equal(red.payload.title, "🟥 Κόκκινη κάρτα (ΑΡΗΣ): ΠΑΟΚ 1–0 ΑΡΗΣ");
  assert.equal(red.payload.body, "60' Παπαδόπουλος");
  assert.equal(t("football", { event: "pens", home: 1, away: 1 }), "⚽ Πάμε στα πέναλτι: ΠΑΟΚ 1–1 ΑΡΗΣ");
  const custom = ev("handball", { event: "custom", title: "Time out ΠΑΟΚ", body: "", home: 10, away: 9 });
  assert.equal(custom.payload.title, "🤾 Time out ΠΑΟΚ");
  assert.equal(custom.payload.body, "Comp");
  assert.equal(custom.once, undefined);
  assert.equal(t("handball", { event: "custom", home: 10, away: 9 }), "🤾 ΠΑΟΚ 10–9 ΑΡΗΣ");
  assert.ok(admin.parseEvent({ event: "pstart", home: 0, away: 0 }).error);
  assert.ok(admin.parseEvent({ event: "red", home: 0, away: 0 }).error);
});

test("Λάθος παράμετροι απορρίπτονται", async () => {
  assert.equal((await call(live, { src: "koe", cat: "../x" })).status, 400);
  assert.equal((await call(live, { src: "nope" })).status, 400);
});

test("api/data: μόνο τα γνωστά αρχεία", async () => {
  mockFetch([[/raw\.githubusercontent\.com/, "{}"]]);
  assert.equal((await call(data, { f: "matches.json" })).status, 200);
  assert.equal((await call(data, { f: "football-women-home.ics" })).status, 200);
  assert.equal((await call(data, { f: "../secret" })).status, 404);
  assert.equal((await call(data, { f: "package.json" })).status, 404);
});

test("subId: 32 δεκαεξαδικοί χαρακτήρες (το «crypto.crypto» έσπασε την εγγραφή συσκευών)", () => {
  assert.match(lib.subId("https://fcm.googleapis.com/fcm/send/x"), /^[0-9a-f]{32}$/);
});

test("validSubscription: μόνο υπηρεσίες push", () => {
  const keys = { p256dh: "a", auth: "b" };
  assert.ok(lib.validSubscription({ endpoint: "https://web.push.apple.com/abc", keys }));
  assert.ok(!lib.validSubscription({ endpoint: "https://evil.example.com/abc", keys }));
});

// ---- Στατιστικά παικτών (?box=1), στη μορφή που είδαμε σε πραγματικούς αγώνες (Νοέμβριος 2026)
const { koeBox, dpParse, ehfBox } = await import("../api/live.js");

test("ΚΟΕ: γκολ, πέναλτι και αποβολές από το startlist, με σύνολα", () => {
  const pl = (nn, name, sm, isout = 0) => ({ nn, cognNome: name, s_m: sm, isout });
  const d = { s1_s: [pl("2", "ΠΡΟΣΙΝΙΚΛΗΣ, Π.", ["", "", "3", "1", ""], 1), pl("9", "DELIC, M.", ["2", "1/1", "", "", ""])],
    s2_s: [pl("7", "ΑΛΛΟΣ, Α.", ["3", "0/1", "1", "", ""])] };
  const b = koeBox(d);
  assert.deepEqual(b.box.home.players.map((r) => [r.name, r.goals, r.pen, r.pf, r.mark]),
    [["ΠΡΟΣΙΝΙΚΛΗΣ Π.", 0, "", 3, "(3Φ)"], ["DELIC M.", 2, "1/1", 0, ""]]);
  assert.deepEqual(b.box.home.tot, { goals: 2, pen: "1/1", pf: 3 });
  assert.deepEqual(b.stats[0], { label: "Πέναλτι", home: "1/1", away: "0/1", bar: [1, 0] });
});

test("Data Project: πίνακες DataVolley, γηπεδούχοι πρώτοι, TOTALS και όσοι μπήκαν", () => {
  const row = (cls, f) => `<tr class="${cls}" id="x">` + Object.entries(f).map(([k, v]) => `<td><span id="${k}">${v}</span></td>`).join("") + "</tr>";
  const P = (no, name, set1, pts) => row("rgRow", { PlayerNumber: no, PlayerName: name, Set1: set1, Set2: "", PointsTot: pts,
    ServeAce: "1", ServeErr: "-", SpikeTot: "10", SpikeWin: "5", BlockWin: "-", RecPos: "40%" });
  const T = (pts) => row("Tabellino_Row_Totals", { PlayerNumber: "", PlayerName: "TOTALS", PointsTot: pts, ServeAce: "3", ServeErr: "5",
    SpikeTot: "80", SpikeWin: "36", BlockWin: "6", RecPos: "45%" });
  const html = "<h3>OTHER (Coach: A)</h3><table>" + P("2", "WHITE Monet", "3", "7") + P("6", "GKREKA Sofia", "*", "1") +
    P("8", "BENCH Anna", "", "") + T("40") + "</table><h3>P.A.O.K. (Coach: B)</h3><table>" + P("3", "ANDERSON Akasha", "1", "8") + T("50") + "</table>(Coach: C)";
  const b = dpParse(html, true);  // ο ΠΑΟΚ είναι γηπεδούχος σε εμάς, φιλοξενούμενος στη Data Project
  assert.deepEqual(b.box.home.players.map((r) => [r.name, r.pts, r.starter]), [["ANDERSON Akasha", 8, true]]);
  assert.deepEqual(b.box.away.players.map((r) => [r.name, r.starter]), [["WHITE Monet", true], ["GKREKA Sofia", false]]);
  assert.equal(b.box.away.tot.pts, 40);
  assert.equal(b.stats[0].away, "36/80 · 45%");
});

test("EHF: παίκτες από τα details, στατιστικά ομάδας από τα statistics", () => {
  const pl = (no, first, last, score, o = {}) => ({ shirtNumber: no, isPlayer: true, playingState: "P", person: { firstName: first, lastName: last }, score, ...o });
  const md = { details: {
    homeTeam: { players: [pl("9", "Nikola", "Trivunovic", { goals: 1, shots: 7, twoMinPenaltiesCount: 2, warningsCount: 1 })] },
    guestTeam: { players: [pl("1", "Petros", "Gk", { goalkeeperSaves: 10, goalkeeperRecievedShots: 36 }, { isGoalkeeper: true }),
      pl("5", "X", "Official", {}, { isTeamOfficial: true })] } },
    statistics: { homeStatistics: { totalGoals: 26, totalShots: 46 }, guestStatistics: { totalGoals: 19, totalShots: 45 } } };
  const b = ehfBox(md);
  assert.deepEqual(b.box.home.players.map((r) => [r.name, r.goals, r.sh, r.two, r.mark]), [["N. Trivunovic", 1, "1/7", 2, "🟨"]]);
  assert.deepEqual(b.box.away.players.map((r) => [r.name, r.sv]), [["P. Gk", "10/36"]]);
  assert.equal(b.stats[0].home, "26/46 · 57%");
});
