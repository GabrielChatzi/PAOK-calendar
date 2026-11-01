// Έλεγχοι για τις functions της Vercel (τρέχουν στο tests.yml):  node --test tests/
// Οι πηγές αντικαθίστανται με ψεύτικες απαντήσεις, στη μορφή που είδαμε σε πραγματικούς αγώνες.
import assert from "node:assert/strict";
import { test } from "node:test";

process.env.MONGODB_URI = process.env.MONGODB_URI || "";
const live = (await import("../api/live.js")).default;
const data = (await import("../api/data.js")).default;
const lib = await import("../api/_lib.js");

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
