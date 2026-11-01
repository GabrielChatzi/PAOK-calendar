// Μεταβιβάσεις εισιτηρίων διαρκείας (δοκιμαστική έκδοση): κάτοχοι που δεν πάνε σε έναν εντός έδρας
// αγώνα δίνουν δωρεάν τη θέση τους και άλλοι φίλαθλοι την παίρνουν. Η ίδια η μεταβίβαση γίνεται
// στο Gov.gr Wallet· εδώ γίνεται μόνο η συνεννόηση.
//
// Ένα endpoint, ενέργεια με ?a=<ενέργεια>. Ταυτότητα: ψευδώνυμο και κλειδί συσκευής
// (Authorization: Bearer <token>)· στη βάση κρατιέται μόνο το hash του κλειδιού.
//
// ΚΑΝΟΝΕΣ
// - Λίστα ανά αγώνα: δηλώνεις ΜΙΑ θύρα ή «οποιαδήποτε». Μια θέση δίνεται αυτόματα σε όποιον
//   δήλωσε ΠΡΩΤΟΣ από όσους τους ταιριάζει η θύρα της (ίδια θύρα ή «οποιαδήποτε»). Η σειρά δεν
//   φαίνεται. Μία θέση ανά άτομο ανά αγώνα. Χωρίς ποινές.
// - Βήματα με χρονόμετρο 3 «ενεργών» ωρών (παγώνει 00:00–08:00 ώρα Ελλάδας):
//     παραλήπτης στέλνει ΑΦΜ → κάτοχος κάνει τη μεταβίβαση → παραλήπτης πατά «Το πήρα».
//   Αν ο παραλήπτης δεν στείλει ΑΦΜ, η θέση πάει στον επόμενο. Αν ο κάτοχος αργήσει: ειδοποίηση
//   και άλλη 1 ώρα· μετά ο παραλήπτης μπαίνει ΠΡΩΤΟΣ για νέα θέση (η θέση του κατόχου μένει
//   διαθέσιμη ώσπου να βρεθεί άλλη· τότε πάει στον επόμενο). Ίδια «διάσωση» όταν ο κάτοχος
//   πατήσει «Τελικά θα πάω».
// - Στο Gov.gr Wallet η μεταβίβαση ισχύει για τον ΕΠΟΜΕΝΟ αγώνα του διαρκείας: για μεταγενέστερο
//   αγώνα η θέση κανονίζεται από πριν και ο ΑΦΜ ζητείται όταν τελειώσει ο προηγούμενος.
// - Η μεταβίβαση γίνεται έως 6 ώρες πριν τη σέντρα («κλείσιμο»): ο ΑΦΜ ως 1 ώρα πριν το κλείσιμο,
//   η μεταβίβαση ως το κλείσιμο, και καμία νέα παράδοση όταν μένουν < 45′.
// - Τελευταίες 24 ώρες: θέση που δεν πήρε κανείς προτείνεται σε όσους περιμένουν σε άλλη θύρα·
//   την παίρνει όποιος προλάβει.
// - Ο ΑΦΜ τον βλέπει μόνο ο κάτοχος, και σβήνεται στο «Το πήρα», σε κάθε ακύρωση και στο κλείσιμο.
//
// Συλλογές MongoDB (ίδια βάση με τις ειδοποιήσεις):
//   tx_users   {_id, nick, nickLower, tokenHash, created, prefs.<football|basketball>.gate ("" = οποιαδήποτε)}
//   tx_offers  {_id, matchId, section, matchStart, ownerId, gate, gateKey, block, row, seat, note, status,
//               recipientId, claimId, step, due, late, rescued, afm, altNotified[], sent{}, created, updated}
//              status: open → assigned → transferred → received → closed
//                      (ή withdrawn / reclaimed / expired); step: wait | afm | transfer | accept
//   tx_claims  {_id: "<user>:<match>", userId, matchId, section, matchStart, gate, gateKey, priority,
//               status, offerId, lateOfferId, rescued, created, updated}
//              status: waiting → assigned → done (ή cancelled / timedout / expired)
//   tx_push    {_id, userId, endpoint, keys, updated}: συσκευές με ειδοποιήσεις web push
//
// Οι χρονικές λειτουργίες (λήξεις, υπενθυμίσεις, τελευταίο 24ωρο, κλείσιμο) τρέχουν στο ?a=tick
// (κάθε 15' από το reminders.yml), μετά από κάθε ενέργεια και, στο παρασκήνιο, σε προβολές όταν
// έχει περάσει πάνω από ένα λεπτό.
//
// Στη δοκιμαστική φάση υπάρχουν χρήστες demo_* που απαντούν αυτόματα (?a=seed βάζει δοκιμαστικές
// θέσεις). Κλείνουν με TX_DEMO=0.
import crypto from "node:crypto";
import fs from "node:fs";
import { waitUntil } from "@vercel/functions";
import { SITE, configured, getDb, pushTo, readBody, send, subId, validSubscription, vapidKeys } from "./_lib.js";

const SECTIONS = new Set(["football", "basketball"]);
const MAX_OPEN_OFFERS_PER_MATCH = 4;
const MIN = 60 * 1000;
const HOUR = 60 * MIN;
const MATCH_LENGTH = 3 * HOUR;      // μετά από τόσο ο αγώνας θεωρείται τελειωμένος
const CUTOFF = 6 * HOUR;            // η μεταβίβαση γίνεται έως τόσο πριν τη σέντρα
const STEP = 3 * HOUR;              // ενεργός χρόνος ανά βήμα
const GRACE = HOUR;                 // επιπλέον χρόνος για τον κάτοχο
const AFM_BEFORE_CUTOFF = HOUR;     // ο ΑΦΜ ως τόσο πριν το κλείσιμο
const MIN_HANDOVER = 45 * MIN;      // καμία νέα παράδοση όταν μένει λιγότερο ως το κλείσιμο
const ALT_WINDOW = 24 * HOUR;       // «υπάρχει θέση σε άλλη θύρα» τόσο πριν τη σέντρα
const REMIND_BEFORE = HOUR;         // υπενθύμιση πριν λήξει ένα βήμα
const QUIET_FROM = 0;               // νύχτα: το χρονόμετρο παγώνει 00:00–08:00
const QUIET_TO = 8;
const TZ = "Europe/Athens";
const PAGE = "/metavivaseis/";
const DEMO = process.env.TX_DEMO !== "0";
const TEST_AFM = "123456783";
const DEMO_USERS = [
  { _id: "demo-1", nick: "demo_toumba" },
  { _id: "demo-2", nick: "demo_maria" },
  { _id: "demo-3", nick: "demo_vasilis" },
];
const DEMO_IDS = DEMO_USERS.map((u) => u._id);

// ---------- Ώρα Ελλάδας και ενεργός χρόνος ----------
const partsFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
});
function localParts(t) {
  const p = Object.fromEntries(partsFmt.formatToParts(new Date(t)).filter((x) => x.type !== "literal").map((x) => [x.type, Number(x.value)]));
  return p;
}
const tzOffset = (t) => { const p = localParts(t); return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second) - Math.floor(t / 1000) * 1000; };
// Ώρα Ελλάδας (y, μήνας 1–12, μέρα, ώρα) → ms
function athensTime(y, mo, d, h) {
  const guess = Date.UTC(y, mo - 1, d, h);
  let t = guess - tzOffset(guess);
  t = guess - tzOffset(t);
  return t;
}
export const isQuiet = (t) => { const h = localParts(t).hour; return h >= QUIET_FROM && h < QUIET_TO; };
function quietEnd(t) { const p = localParts(t); return athensTime(p.year, p.month, p.day, QUIET_TO); }
function nextMidnight(t) { const p = localParts(t); return athensTime(p.year, p.month, p.day + 1, 0); }
// t + ms, χωρίς να μετρά ο χρόνος 00:00–08:00.
export function addActive(t, ms) {
  let left = ms;
  for (let i = 0; i < 30 && left > 0; i++) {
    if (isQuiet(t)) { t = quietEnd(t); continue; }
    const span = Math.min(left, nextMidnight(t) - t);
    t += span; left -= span;
  }
  return t;
}
const cutoffOf = (start) => new Date(start).getTime() - CUTOFF;
function afmDue(now, start) {
  const cut = cutoffOf(start);
  let due = Math.min(addActive(now, STEP), cut - AFM_BEFORE_CUTOFF);
  if (due < now + 20 * MIN) due = Math.min(now + 20 * MIN, cut - 15 * MIN); // παράδοση της τελευταίας στιγμής
  return new Date(due);
}
const transferDue = (now, start) => new Date(Math.min(addActive(now, STEP), cutoffOf(start)));
const acceptDue = (now, start) => new Date(Math.min(addActive(now, STEP), new Date(start).getTime() - HOUR));

// ---------- Αγώνες ----------
// Από τον κλάδο «data» του GitHub (εκεί τα γράφει το update.yml)· αλλιώς από τη δημόσια σελίδα.
// Στις δοκιμές από αρχείο (TX_MATCHES_FILE). Κρατιούνται 10 λεπτά.
let matchCache = null;
async function readMatches() {
  if (process.env.TX_MATCHES_FILE) return JSON.parse(fs.readFileSync(process.env.TX_MATCHES_FILE, "utf8"));
  const urls = [
    `https://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/data/matches.json?t=${Math.floor(Date.now() / 60000)}`,
    `${SITE}/matches.json`,
  ];
  let last;
  for (const url of urls) {
    try {
      const res = await fetch(url, { headers: { "Cache-Control": "no-cache" } });
      if (res.ok) return await res.json();
      last = new Error(`matches.json: HTTP ${res.status}`);
    } catch (e) { last = e; }
  }
  throw last;
}
async function matches() {
  if (matchCache && Date.now() - matchCache.at < 10 * MIN) return matchCache.byId;
  const data = await readMatches();
  const byId = new Map();
  for (const m of data.matches || []) {
    if (m.nt && m.paokHome && SECTIONS.has(m.section)) byId.set(m.nt, m);
  }
  matchCache = { at: Date.now(), byId };
  return byId;
}
const startOf = (m) => new Date(m.start).getTime();
const deadlineOf = (start) => new Date(cutoffOf(start));

// Ο επόμενος εντός έδρας αγώνας ενός τμήματος: ο πρώτος που δεν έχει τελειώσει.
async function nextFor(section) {
  const now = Date.now();
  let best = null;
  for (const m of (await matches()).values()) {
    if (m.section !== section) continue;
    const t = startOf(m);
    if (t + MATCH_LENGTH > now && (!best || t < startOf(best))) best = m;
  }
  return best;
}
// Μπορεί να γίνει τώρα η μεταβίβαση στο Wallet για αυτόν τον αγώνα; (επόμενος και πριν το κλείσιμο)
async function transferable(matchId, section) {
  const n = await nextFor(section);
  return Boolean(n && n.nt === matchId && Date.now() < cutoffOf(n.start));
}
// Αγώνας που δέχεται ακόμα θέσεις και δηλώσεις (πριν το κλείσιμο).
async function openMatch(id) {
  const m = (await matches()).get(String(id || ""));
  return m && Date.now() < cutoffOf(m.start) ? m : null;
}

// ---------- Βοηθητικά ----------
const newId = () => crypto.randomBytes(9).toString("base64url");
const hash = (t) => crypto.createHash("sha256").update(t).digest("hex");

class Fail extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
const fail = (status, message) => { throw new Fail(status, message); };

function str(v, max, { required = false, label = "Πεδίο" } = {}) {
  const s = typeof v === "string" ? v.trim().replace(/\s+/g, " ") : "";
  if (required && !s) fail(400, `${label}: υποχρεωτικό.`);
  if (s.length > max) fail(400, `${label}: έως ${max} χαρακτήρες.`);
  return s;
}

// Θύρα για σύγκριση: «Θύρα 4», «θ4», « 4 » → «4»· χωρίς τόνους, κεφαλαία.
export function gateKey(g) {
  return String(g || "").normalize("NFD").replace(/\p{M}/gu, "").toUpperCase()
    .replace(/^Θ(ΥΡΑ)?\.?\s*/, "").replace(/\s+/g, "");
}
// Θύρα από το σώμα αιτήματος: {any: true} ή {gate}.
function gateFrom(body) {
  if (body.any === true) return { gate: "", gateKey: "" };
  const gate = str(body.gate, 10, { required: true, label: "Θύρα" });
  const key = gateKey(gate);
  if (!key) fail(400, "Θύρα: υποχρεωτικό.");
  return { gate, gateKey: key };
}

// Έλεγχος ΑΦΜ με το ψηφίο ελέγχου.
export function validAfm(afm) {
  if (!/^\d{9}$/.test(afm) || afm === "000000000") return false;
  let sum = 0;
  for (let i = 0; i < 8; i++) sum += Number(afm[i]) * 2 ** (8 - i);
  return (sum % 11) % 10 === Number(afm[8]);
}

const fmtWhen = (d) => new Intl.DateTimeFormat("el-GR", {
  timeZone: TZ, weekday: "short", day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
}).format(new Date(d));
const fmtTime = (d) => new Intl.DateTimeFormat("el-GR", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date(d));
// «ως τις 14:30» σήμερα, αλλιώς «ως Κυρ 2/11, 14:30»
function fmtDue(d) {
  const a = localParts(Date.now()); const b = localParts(new Date(d).getTime());
  return a.year === b.year && a.month === b.month && a.day === b.day ? `ως τις ${fmtTime(d)}` : `ως ${fmtWhen(d)}`;
}
const titleOf = (m) => (m ? `${m.home} – ${m.away}` : "Αγώνας");
const gateLabel = (g) => (g ? `Θύρα ${g}` : "οποιαδήποτε θύρα");
function seatLine(o) {
  return [`Θύρα ${o.gate}`, o.block && `Τμήμα ${o.block}`, o.row && `Σειρά ${o.row}`, o.seat && `Θέση ${o.seat}`].filter(Boolean).join(" · ");
}

let indexesReady = null;
async function cols() {
  const db = await getDb();
  const c = {
    users: db.collection("tx_users"),
    offers: db.collection("tx_offers"),
    claims: db.collection("tx_claims"),
    push: db.collection("tx_push"),
  };
  indexesReady ??= Promise.all([
    c.users.createIndex({ nickLower: 1 }, { unique: true }),
    c.users.createIndex({ tokenHash: 1 }, { unique: true }),
    c.offers.createIndex({ matchId: 1, status: 1 }),
    c.offers.createIndex({ ownerId: 1 }),
    c.offers.createIndex({ recipientId: 1 }),
    c.offers.createIndex({ status: 1, due: 1 }),
    c.claims.createIndex({ matchId: 1, status: 1, priority: 1 }),
    c.claims.createIndex({ userId: 1 }),
    c.push.createIndex({ userId: 1 }),
  ]).catch((e) => { indexesReady = null; throw e; });
  await indexesReady;
  return c;
}

async function currentUser(req, c, { required = true } = {}) {
  const m = /^Bearer ([A-Za-z0-9_-]{20,100})$/.exec(req.headers.authorization || "");
  const user = m ? await c.users.findOne({ tokenHash: hash(m[1]) }) : null;
  if (!user && required) fail(401, "Χρειάζεται ψευδώνυμο για αυτή την ενέργεια.");
  return user;
}
// Προεπιλεγμένη θύρα ανά τμήμα ("" = οποιαδήποτε, null = δεν έχει οριστεί).
function prefGate(user, section) {
  const p = user?.prefs?.[section];
  if (!p) return null;
  if (typeof p.gate === "string") return p.gate;
  if (Array.isArray(p.gates)) return p.gates[0] || null; // παλιά μορφή
  return null;
}
async function nickOf(c, id) {
  return (await c.users.findOne({ _id: id }, { projection: { nick: 1 } }))?.nick || "—";
}

// ---------- Ειδοποιήσεις web push ----------
let keysPromise = null;
async function notify(c, userIds, { title, body, tag, url }) {
  const ids = [...new Set(userIds.filter((id) => id && !DEMO_IDS.includes(id)))];
  if (!ids.length) return 0;
  const devices = await c.push.find({ userId: { $in: ids } }).toArray();
  if (!devices.length) return 0;
  keysPromise ??= vapidKeys().catch((e) => { keysPromise = null; throw e; });
  const keys = await keysPromise;
  const payload = { title: title.slice(0, 120), body: String(body || "").slice(0, 300), url: url || `${PAGE}#/mine`, tag };
  const results = await Promise.all(devices.map((d) => pushTo(d, payload, keys, 6 * 3600)));
  const gone = devices.filter((_, i) => results[i] === "gone").map((d) => d._id);
  if (gone.length) await c.push.deleteMany({ _id: { $in: gone } });
  return results.filter((r) => r === "ok").length;
}

// ---------- Ανάθεση: πρώτος στη λίστα, πρώτος παίρνει ----------
const OFFER_RESET = { recipientId: "", claimId: "", step: "", due: "", late: "", rescued: "", afm: "" };

// Δίνει τις ελεύθερες θέσεις ενός αγώνα σε όσους περιμένουν, με τη σειρά δήλωσης.
async function allocate(c, matchId) {
  const m = (await matches()).get(matchId);
  if (!m || Date.now() >= cutoffOf(m.start) - MIN_HANDOVER) return 0;
  let given = 0;
  const offers = await c.offers.find({ matchId, status: "open" }).sort({ created: 1 }).toArray();
  for (const o of offers) {
    for (let tries = 0; tries < 5; tries++) {
      const cl = await c.claims.find({ matchId, status: "waiting", userId: { $ne: o.ownerId }, gateKey: { $in: [o.gateKey, ""] } })
        .sort({ priority: 1 }).limit(1).next();
      if (!cl) break;
      const r = await assign(c, o, cl, m);
      if (r) { given++; break; }
      if (r === null) break; // η θέση δεν είναι πια ελεύθερη
    }
  }
  return given;
}

// Μία θέση σε έναν: true αν έγινε, false αν η δήλωση άλλαξε στο μεταξύ, null αν η θέση πιάστηκε.
async function assign(c, o, cl, m) {
  const now = new Date();
  const claim = await c.claims.findOneAndUpdate({ _id: cl._id, status: "waiting" }, { $set: { status: "assigned", offerId: o._id, updated: now } });
  if (!claim) return false;
  const canNow = await transferable(o.matchId, o.section);
  const step = canNow ? "afm" : "wait";
  const due = canNow ? afmDue(now.getTime(), o.matchStart) : null;
  const res = await c.offers.findOneAndUpdate({ _id: o._id, status: "open" }, {
    $set: { status: "assigned", recipientId: claim.userId, claimId: claim._id, step, due, late: false, rescued: false, sent: {}, updated: now },
    $unset: { afm: "" },
  });
  if (!res) {
    await c.claims.updateOne({ _id: claim._id, offerId: o._id }, { $set: { status: "waiting" }, $unset: { offerId: "" } });
    return null;
  }
  // Ο παραλήπτης περίμενε θέση από κάτοχο που άργησε: εκείνη η θέση πάει πια στον επόμενο.
  if (claim.lateOfferId) {
    await c.claims.updateOne({ _id: claim._id }, { $unset: { lateOfferId: "" }, $set: { rescued: false } });
    await releaseLate(c, claim.lateOfferId, claim._id);
  }
  const owner = await nickOf(c, o.ownerId);
  const recipient = await nickOf(c, claim.userId);
  const n = canNow ? null : await nextFor(o.section);
  await notify(c, [claim.userId], {
    title: "Σου βρέθηκε θέση!",
    body: `${titleOf(m)} · ${seatLine(o)} από @${owner}. ` + (canNow
      ? `Στείλε τον ΑΦΜ σου ${fmtDue(due)}.`
      : `Θα σου ζητηθεί ο ΑΦΜ μετά το ${titleOf(n)}.`),
    tag: `seat-${o._id}`,
  });
  await notify(c, [o.ownerId], {
    title: `Βρέθηκε παραλήπτης: @${recipient}`,
    body: `${titleOf(m)} · ${seatLine(o)}. ` + (canNow ? `Θα σου στείλει τον ΑΦΜ του ${fmtDue(due)}.` : "Ο ΑΦΜ θα σταλεί όταν ανοίξει η μεταβίβαση."),
    tag: `seat-${o._id}`,
  });
  return true;
}

// Θέση κατόχου που είχε αργήσει: ο παραλήπτης βρήκε άλλη, οπότε αυτή ξαναγίνεται ελεύθερη.
async function releaseLate(c, offerId, claimId) {
  const o = await c.offers.findOneAndUpdate(
    { _id: offerId, claimId, status: "assigned", rescued: true },
    { $set: { status: "open", sent: {}, updated: new Date() }, $unset: OFFER_RESET },
  );
  if (!o) return;
  const m = (await matches()).get(o.matchId);
  await notify(c, [o.ownerId], {
    title: "Η θέση σου πάει σε άλλον",
    body: `Ο παραλήπτης βρήκε άλλη θέση. Η δική σου (${seatLine(o)}, ${titleOf(m)}) πάει στον επόμενο της λίστας.`,
    tag: `seat-${o._id}`,
  });
  await allocate(c, o.matchId);
}

// Ο παραλήπτης έμεινε χωρίς εισιτήριο (ο κάτοχος άργησε ή θα πάει τελικά): μπαίνει πρώτος.
async function rescue(c, claimId, { lateOfferId = null } = {}) {
  const now = new Date();
  const $set = { status: "waiting", rescued: true, priority: new Date(now.getTime() - 50 * 365 * 24 * HOUR), updated: now };
  if (lateOfferId) $set.lateOfferId = lateOfferId;
  const cl = await c.claims.findOneAndUpdate({ _id: claimId }, { $set, $unset: { offerId: "" } });
  return cl;
}

// Η θέση ξαναγίνεται ελεύθερη (ο παραλήπτης δεν απάντησε/αποχώρησε) και πάει στον επόμενο.
async function reopen(c, o) {
  await c.offers.updateOne({ _id: o._id }, { $set: { status: "open", sent: {}, updated: new Date() }, $unset: OFFER_RESET });
  await allocate(c, o.matchId);
}

// ---------- Βήματα (κοινά για χρήστες και demo) ----------
async function doAfm(c, o, afm) {
  const now = Date.now();
  const due = transferDue(now, o.matchStart);
  const r = await c.offers.updateOne({ _id: o._id, status: "assigned", step: "afm" },
    { $set: { afm, step: "transfer", due, late: false, sent: {}, updated: new Date(now) } });
  if (!r.modifiedCount) return false;
  await notify(c, [o.ownerId], {
    title: `Ο @${await nickOf(c, o.recipientId)} έστειλε τον ΑΦΜ του`,
    body: `Κάνε τη μεταβίβαση στο Gov.gr Wallet ${fmtDue(due)}.`,
    tag: `seat-${o._id}`,
  });
  return true;
}
async function doTransfer(c, o) {
  const now = Date.now();
  // Αν ο παραλήπτης είχε μπει στη λίστα για άλλη θέση (ο κάτοχος άργησε), επιστρέφει σε αυτή.
  if (o.rescued) {
    const back = await c.claims.updateOne({ _id: o.claimId, status: "waiting", lateOfferId: o._id },
      { $set: { status: "assigned", offerId: o._id, rescued: false, updated: new Date(now) }, $unset: { lateOfferId: "" } });
    if (!back.modifiedCount) return false;
  }
  const due = acceptDue(now, o.matchStart);
  const r = await c.offers.updateOne({ _id: o._id, status: "assigned", step: "transfer", afm: { $exists: true } },
    { $set: { status: "transferred", step: "accept", due, late: false, rescued: false, sent: {}, updated: new Date(now) } });
  if (!r.modifiedCount) return false;
  await notify(c, [o.recipientId], {
    title: "Έγινε η μεταβίβαση!",
    body: "Θα σου έρθει email από το Gov.gr Wallet. Αποδέξου το εισιτήριο και πάτα «Το πήρα».",
    tag: `seat-${o._id}`,
  });
  return true;
}
async function doReceive(c, o) {
  const r = await c.offers.updateOne({ _id: o._id, status: "transferred" },
    { $set: { status: "received", updated: new Date() }, $unset: { afm: "", step: "", due: "" } });
  if (!r.modifiedCount) return false;
  await c.claims.updateOne({ _id: o.claimId }, { $set: { status: "done", updated: new Date() } });
  await notify(c, [o.ownerId], { title: `Ο @${await nickOf(c, o.recipientId)} πήρε το εισιτήριο`, body: "Ευχαριστούμε που έδωσες τη θέση σου!", tag: `seat-${o._id}` });
  return true;
}

// ---------- Χρονικά γεγονότα ----------
async function once(c, offerId, key) {
  const r = await c.offers.updateOne({ _id: offerId, [`sent.${key}`]: { $ne: true } }, { $set: { [`sent.${key}`]: true } });
  return r.modifiedCount === 1;
}

async function runTimers(c) {
  const now = Date.now();
  const nowD = new Date(now);
  const touched = new Set();

  // 1. Άνοιξε η μεταβίβαση για αγώνα που περίμενε: ο παραλήπτης στέλνει ΑΦΜ.
  for (const o of await c.offers.find({ status: "assigned", step: "wait" }).limit(200).toArray()) {
    if (!(await transferable(o.matchId, o.section))) continue;
    const due = afmDue(now, o.matchStart);
    const r = await c.offers.updateOne({ _id: o._id, step: "wait" }, { $set: { step: "afm", due, sent: {}, updated: nowD } });
    if (r.modifiedCount) {
      const m = (await matches()).get(o.matchId);
      await notify(c, [o.recipientId], { title: "Στείλε τον ΑΦΜ σου", body: `Άνοιξε η μεταβίβαση για ${titleOf(m)}. Στείλε τον ΑΦΜ σου ${fmtDue(due)}.`, tag: `seat-${o._id}` });
    }
  }

  // 2. Υπενθυμίσεις μία ώρα πριν λήξει ένα βήμα (όχι τη νύχτα).
  if (!isQuiet(now)) {
    const soon = await c.offers.find({ status: { $in: ["assigned", "transferred"] }, step: { $in: ["afm", "transfer", "accept"] }, due: { $gt: nowD, $lte: new Date(now + REMIND_BEFORE) }, late: { $ne: true } }).limit(200).toArray();
    for (const o of soon) {
      if (!(await once(c, o._id, `remind_${o.step}`))) continue;
      if (o.step === "afm") await notify(c, [o.recipientId], { title: "Μην ξεχάσεις τον ΑΦΜ", body: `Στείλε τον ΑΦΜ σου ${fmtDue(o.due)}, αλλιώς η θέση πάει στον επόμενο.`, tag: `seat-${o._id}` });
      if (o.step === "transfer") await notify(c, [o.ownerId], { title: "Μην ξεχάσεις τη μεταβίβαση", body: `Κάνε τη μεταβίβαση στο Gov.gr Wallet ${fmtDue(o.due)}.`, tag: `seat-${o._id}` });
      if (o.step === "accept") await notify(c, [o.recipientId], { title: "Αποδέξου το εισιτήριο", body: "Άνοιξε το Gov.gr Wallet, αποδέξου το εισιτήριο και πάτα «Το πήρα».", tag: `seat-${o._id}` });
    }
  }

  // 3. Λήξεις.
  const expired = await c.offers.find({ status: { $in: ["assigned", "transferred"] }, step: { $in: ["afm", "transfer", "accept"] }, due: { $lte: nowD } }).limit(200).toArray();
  for (const o of expired) {
    const m = (await matches()).get(o.matchId);
    if (now >= cutoffOf(o.matchStart) && o.step !== "accept") continue; // το κλείσιμο τα χειρίζεται παρακάτω

    if (o.step === "afm") {
      // Ο παραλήπτης δεν έστειλε ΑΦΜ: η θέση πάει στον επόμενο.
      const r = await c.offers.updateOne({ _id: o._id, step: "afm", due: o.due }, { $set: { status: "open", sent: {}, updated: nowD }, $unset: OFFER_RESET });
      if (!r.modifiedCount) continue;
      await c.claims.updateOne({ _id: o.claimId }, { $set: { status: "timedout", updated: nowD }, $unset: { offerId: "" } });
      await notify(c, [o.recipientId], { title: "Η θέση πήγε στον επόμενο", body: `Δεν στάλθηκε ο ΑΦΜ εγκαίρως για ${titleOf(m)}. Αν θες ακόμα θέση, ξαναμπές στη λίστα.`, tag: `seat-${o._id}`, url: `${PAGE}#/m/${o.matchId}` });
      await notify(c, [o.ownerId], { title: "Ψάχνουμε άλλον παραλήπτη", body: `Ο @${await nickOf(c, o.recipientId)} δεν απάντησε εγκαίρως. Η θέση σου πάει στον επόμενο της λίστας.`, tag: `seat-${o._id}` });
      touched.add(o.matchId);
    } else if (o.step === "transfer" && !o.late) {
      // Ο κάτοχος άργησε: ειδοποίηση και άλλη 1 ώρα (ως το κλείσιμο).
      const grace = new Date(Math.min(now + GRACE, cutoffOf(o.matchStart)));
      const r = await c.offers.updateOne({ _id: o._id, step: "transfer", late: { $ne: true } }, { $set: { late: true, due: grace, updated: nowD } });
      if (!r.modifiedCount) continue;
      await notify(c, [o.ownerId], { title: "Έληξε ο χρόνος για τη μεταβίβαση", body: `Έχεις άλλη 1 ώρα, ως τις ${fmtTime(grace)}, να κάνεις τη μεταβίβαση για ${titleOf(m)}. Μετά θα ψάξουμε άλλη θέση για τον @${await nickOf(c, o.recipientId)}.`, tag: `seat-${o._id}` });
      await notify(c, [o.recipientId], { title: "Ο κάτοχος αργεί λίγο", body: `Έχει ως τις ${fmtTime(grace)} να κάνει τη μεταβίβαση. Αλλιώς θα σου βρούμε άλλη θέση.`, tag: `seat-${o._id}` });
    } else if (o.step === "transfer" && o.late && !o.rescued) {
      // Ούτε στην επιπλέον ώρα: ο παραλήπτης μπαίνει πρώτος για νέα θέση· η θέση του κατόχου
      // μένει διαθέσιμη μέχρι να βρεθεί άλλη.
      const r = await c.offers.updateOne({ _id: o._id, step: "transfer", late: true, rescued: { $ne: true } }, { $set: { rescued: true, updated: nowD } });
      if (!r.modifiedCount) continue;
      await rescue(c, o.claimId, { lateOfferId: o._id });
      await notify(c, [o.recipientId], { title: "Σου ψάχνουμε άλλη θέση", body: `Ο κάτοχος δεν έκανε ακόμα τη μεταβίβαση για ${titleOf(m)}. Είσαι πρώτος για την επόμενη θέση που θα βγει.`, tag: `seat-${o._id}` });
      await notify(c, [o.ownerId], { title: "Ψάχνουμε άλλη θέση για τον παραλήπτη", body: "Αν προλαβαίνεις, κάνε τη μεταβίβαση τώρα. Αλλιώς η θέση σου θα δοθεί στον επόμενο μόλις του βρεθεί άλλη.", tag: `seat-${o._id}` });
      touched.add(o.matchId);
    } else if (o.step === "accept" && !o.sent?.acceptDue) {
      // Ο παραλήπτης δεν πάτησε «Το πήρα»: υπενθύμιση· ο κάτοχος μπορεί να δηλώσει ότι δεν το αποδέχτηκε.
      if (!(await once(c, o._id, "acceptDue"))) continue;
      await notify(c, [o.recipientId], { title: "Πήρες το εισιτήριο;", body: "Αν το αποδέχτηκες στο Gov.gr Wallet, πάτα «Το πήρα».", tag: `seat-${o._id}` });
      await notify(c, [o.ownerId], { title: "Δεν έχει επιβεβαιώσει ακόμα", body: `Ο @${await nickOf(c, o.recipientId)} δεν πάτησε «Το πήρα». Δες στο Wallet αν το αποδέχτηκε.`, tag: `seat-${o._id}` });
    }
  }

  // 4. Τελευταίες 24 ώρες: θέση που δεν πήρε κανείς → σε όσους περιμένουν σε άλλη θύρα (όχι τη νύχτα).
  if (!isQuiet(now)) {
    const lastDay = await c.offers.find({ status: "open", matchStart: { $lte: new Date(now + ALT_WINDOW), $gt: new Date(now + CUTOFF + MIN_HANDOVER) } }).limit(100).toArray();
    for (const o of lastDay) {
      const waiting = await c.claims.find({ matchId: o.matchId, status: "waiting", gateKey: { $nin: ["", o.gateKey] }, userId: { $ne: o.ownerId } }).toArray();
      const fresh = waiting.filter((w) => !(o.altNotified || []).includes(w.userId));
      if (!fresh.length) continue;
      await c.offers.updateOne({ _id: o._id }, { $addToSet: { altNotified: { $each: fresh.map((w) => w.userId) } } });
      const m = (await matches()).get(o.matchId);
      for (const w of fresh) {
        await notify(c, [w.userId], {
          title: `Υπάρχει θέση στη Θύρα ${o.gate}`,
          body: `Δεν βρέθηκε ακόμα στη ${gateLabel(w.gate)} για ${titleOf(m)}. Υπάρχει ελεύθερη στη Θύρα ${o.gate}, αν τη θες. Την παίρνει όποιος προλάβει.`,
          tag: `alt-${o._id}`, url: `${PAGE}#/m/${o.matchId}`,
        });
      }
    }
  }

  for (const id of touched) await allocate(c, id);
}

// Το κλείσιμο (6 ώρες πριν) και όσα τελείωσαν.
async function closeOut(c) {
  const now = new Date();
  const closed = new Date(now.getTime() + CUTOFF); // αγώνες που αρχίζουν πριν από αυτό έχουν κλείσει
  const ended = new Date(now.getTime() - MATCH_LENGTH);

  // Δηλώσεις που δεν βρήκαν θέση.
  const lost = await c.claims.find({ status: "waiting", matchStart: { $lt: closed } }).limit(500).toArray();
  if (lost.length) {
    await c.claims.updateMany({ _id: { $in: lost.map((x) => x._id) }, status: "waiting" }, { $set: { status: "expired", updated: now } });
    const all = await matches();
    for (const cl of lost) {
      await notify(c, [cl.userId], { title: "Δεν βρέθηκε θέση", body: `Δυστυχώς δεν βρέθηκε θέση για ${titleOf(all.get(cl.matchId))}. Έκλεισαν οι μεταβιβάσεις.`, tag: `claim-${cl._id}` });
    }
  }
  // Θέσεις που δεν πρόλαβαν να μεταβιβαστούν.
  const missed = await c.offers.find({ status: "assigned", matchStart: { $lt: closed } }).limit(500).toArray();
  for (const o of missed) {
    const r = await c.offers.updateOne({ _id: o._id, status: "assigned" }, { $set: { status: "expired", updated: now }, $unset: { afm: "", step: "", due: "" } });
    if (!r.modifiedCount) continue;
    await c.claims.updateOne({ _id: o.claimId, status: { $in: ["assigned", "waiting"] } }, { $set: { status: "expired", updated: now } });
    if (!o.rescued) {
      await notify(c, [o.recipientId, o.ownerId], { title: "Έκλεισαν οι μεταβιβάσεις", body: `Η μεταβίβαση για ${seatLine(o)} δεν ολοκληρώθηκε πριν το κλείσιμο.`, tag: `seat-${o._id}` });
    }
  }
  await Promise.all([
    c.offers.updateMany({ status: "open", matchStart: { $lt: closed } }, { $set: { status: "expired", updated: now } }),
    c.offers.updateMany({ status: { $in: ["transferred", "received"] }, matchStart: { $lt: ended } }, { $set: { status: "closed", updated: now }, $unset: { step: "", due: "" } }),
  ]);
  await c.offers.updateMany({ afm: { $exists: true }, $or: [{ matchStart: { $lt: closed } }, { status: { $nin: ["assigned", "transferred"] } }] }, { $unset: { afm: "" } });
}

// Συντήρηση: κλείσιμο, χρονόμετρα, demo χρήστες.
const MAINTENANCE_EVERY = MIN;
let lastMaintenance = 0;
let maintaining = null;
// fresh: περιμένει όποια συντήρηση τρέχει ήδη και κάνει ΝΕΟ πέρασμα (το tick δεν πρέπει να
// «πατάει» πάνω σε πέρασμα που ξεκίνησε πριν από αλλαγές).
async function housekeeping(c, { fresh = false } = {}) {
  if (fresh && maintaining) await maintaining.catch(() => {});
  maintaining ??= (async () => {
    lastMaintenance = Date.now();
    await migrate(c);
    await closeOut(c);
    await runTimers(c);
    if (DEMO) await demoBots(c);
  })().finally(() => { maintaining = null; });
  return maintaining;
}

// Παλιά δεδομένα από την προηγούμενη έκδοση (αιτήματα αντί για λίστα): ανοίγουν ξανά.
let migrated = false;
async function migrate(c) {
  if (migrated) return;
  await c.offers.updateMany({ status: "assigned", claimId: { $exists: false } }, { $set: { status: "open", sent: {} }, $unset: OFFER_RESET });
  migrated = true;
}

// ---------- Δοκιμαστικοί χρήστες ----------
async function ensureDemoUsers(c) {
  for (const u of DEMO_USERS) {
    await c.users.updateOne({ _id: u._id }, {
      $setOnInsert: { nick: u.nick, nickLower: u.nick, demo: true, tokenHash: hash(crypto.randomBytes(24).toString("hex")), created: new Date() },
    }, { upsert: true });
  }
}
async function demoBots(c) {
  const now = new Date();
  // Μπαίνουν στη λίστα για θέσεις αληθινών χρηστών που δεν πήρε κανείς.
  const open = await c.offers.find({ status: "open", ownerId: { $nin: DEMO_IDS } }).limit(50).toArray();
  const touched = new Set();
  for (const o of open) {
    if (!(await openMatch(o.matchId))) continue;
    const busy = await c.claims.find({ matchId: o.matchId, userId: { $in: DEMO_IDS }, status: { $in: ["waiting", "assigned"] } }).toArray();
    const free = DEMO_IDS.find((id) => !busy.some((b) => b.userId === id));
    if (!free) continue;
    await ensureDemoUsers(c);
    const m = (await matches()).get(o.matchId);
    await c.claims.updateOne({ _id: `${free}:${o.matchId}` }, {
      $set: { userId: free, matchId: o.matchId, section: o.section, matchStart: new Date(m.start), gate: o.gate, gateKey: o.gateKey, status: "waiting", priority: now, rescued: false, updated: now },
      $setOnInsert: { created: now }, $unset: { offerId: "", lateOfferId: "" },
    }, { upsert: true });
    touched.add(o.matchId);
  }
  for (const id of touched) await allocate(c, id);
  for (const o of await c.offers.find({ status: "assigned", step: "afm", recipientId: { $in: DEMO_IDS } }).toArray()) await doAfm(c, o, TEST_AFM);
  for (const o of await c.offers.find({ status: "assigned", step: "transfer", ownerId: { $in: DEMO_IDS }, afm: { $exists: true } }).toArray()) await doTransfer(c, o);
  for (const o of await c.offers.find({ status: "transferred", recipientId: { $in: DEMO_IDS } }).toArray()) await doReceive(c, o);
}

// Πόσες θέσεις έχει δώσει ο καθένας (ολοκληρωμένες μεταβιβάσεις).
async function givenCounts(c, ids) {
  if (!ids.length) return {};
  const rows = await c.offers.aggregate([
    { $match: { ownerId: { $in: ids }, status: { $in: ["received", "closed"] } } },
    { $group: { _id: "$ownerId", n: { $sum: 1 } } },
  ]).toArray();
  return Object.fromEntries(rows.map((r) => [r._id, r.n]));
}
async function nicks(c, ids) {
  const uniq = [...new Set(ids.filter(Boolean))];
  if (!uniq.length) return {};
  const rows = await c.users.find({ _id: { $in: uniq } }, { projection: { nick: 1 } }).toArray();
  return Object.fromEntries(rows.map((u) => [u._id, u.nick]));
}

// block = «Τμήμα» (μόνο στο μπάσκετ).
const seatOf = (o) => ({ gate: o.gate, block: o.block || "", row: o.row || "", seat: o.seat || "" });
const isOpenOffer = (o) => o.status === "open" && Date.now() < cutoffOf(o.matchStart);
// Η κατάσταση όπως είναι ΤΩΡΑ, ακόμα κι αν η συντήρηση δεν έχει τρέξει.
function effective(o) {
  const now = Date.now();
  const start = new Date(o.matchStart).getTime();
  if (["open", "assigned"].includes(o.status) && now >= start - CUTOFF) return { ...o, status: "expired", afm: undefined };
  if (["transferred", "received"].includes(o.status) && now >= start + MATCH_LENGTH) return { ...o, status: "closed", afm: undefined };
  return o;
}

// Μπαίνει (ή αλλάζει θύρα) στη λίστα ενός αγώνα. Κρατά τη σειρά του αν ήταν ήδη στη λίστα.
async function joinList(c, me, m, { gate, gateKey: key }) {
  const _id = `${me._id}:${m.nt}`;
  const cur = await c.claims.findOne({ _id });
  if (cur?.status === "assigned") fail(409, "Έχεις ήδη θέση για αυτόν τον αγώνα.");
  if (cur?.status === "done") fail(409, "Έχεις ήδη πάρει θέση για αυτόν τον αγώνα.");
  if (await c.offers.findOne({ matchId: m.nt, ownerId: me._id, status: { $in: ["open", "assigned", "transferred", "received"] } })) {
    fail(409, "Δίνεις θέση σε αυτόν τον αγώνα, οπότε δεν μπορείς να μπεις και στη λίστα.");
  }
  const now = new Date();
  const keep = cur?.status === "waiting";
  await c.claims.updateOne({ _id }, {
    $set: {
      userId: me._id, matchId: m.nt, section: m.section, matchStart: new Date(m.start), gate, gateKey: key, status: "waiting",
      priority: keep ? cur.priority : now, rescued: keep ? Boolean(cur.rescued) : false, updated: now,
    },
    $setOnInsert: { created: now },
    ...(keep ? {} : { $unset: { offerId: "", lateOfferId: "" } }),
  }, { upsert: true });
  await allocate(c, m.nt);
  return c.claims.findOne({ _id });
}

// ---------- Ενέργειες ----------
const actions = {
  // GET: σύνοψη ανά αγώνα (ελεύθερες θέσεις, πόσοι είναι στη λίστα). Δημόσιο.
  async summary(req, c) {
    const open = new Date(Date.now() + CUTOFF);
    const [offers, claims] = await Promise.all([
      c.offers.find({ status: "open", matchStart: { $gt: open } }, { projection: { matchId: 1 } }).toArray(),
      c.claims.find({ status: "waiting", matchStart: { $gt: open } }, { projection: { matchId: 1 } }).toArray(),
    ]);
    const out = {};
    const slot = (id) => (out[id] ??= { offers: 0, seekers: 0 });
    for (const o of offers) slot(o.matchId).offers++;
    for (const w of claims) slot(w.matchId).seekers++;
    return { matches: out, demo: DEMO, cutoffHours: CUTOFF / HOUR };
  },

  // POST: συντήρηση (το καλεί το reminders.yml κάθε 15').
  async tick() {
    return { ok: true };
  },

  // POST: δοκιμαστικές θέσεις από τους demo χρήστες στους 2 επόμενους εντός έδρας του ποδοσφαίρου
  // και στον επόμενο του μπάσκετ. Δεν ξαναβάζει σε αγώνα που έχει ήδη.
  async seed(req, c) {
    if (!DEMO) fail(403, "Μόνο στη δοκιμαστική έκδοση.");
    await ensureDemoUsers(c);
    const now = Date.now();
    const all = [...(await matches()).values()];
    const pick = (section, n) => all.filter((m) => m.section === section && cutoffOf(m.start) - MIN_HANDOVER > now)
      .sort((a, b) => a.start.localeCompare(b.start)).slice(0, n);
    const targets = [...pick("football", 2), ...pick("basketball", 1)];
    const seats = {
      football: [{ gate: "4", row: "12", seat: "8" }, { gate: "1", row: "", seat: "" }, { gate: "7", row: "30", seat: "15" }],
      basketball: [{ gate: "2", block: "Β", row: "6", seat: "11" }, { gate: "4", block: "Δ", row: "", seat: "" }],
    };
    let created = 0;
    for (const m of targets) {
      if (await c.offers.findOne({ matchId: m.nt, ownerId: { $in: DEMO_IDS }, status: { $in: ["open", "assigned", "transferred"] } })) continue;
      const list = seats[m.section];
      for (let i = 0; i < list.length; i++) {
        const t = new Date(Date.now() + i);
        await c.offers.insertOne({
          _id: newId(), matchId: m.nt, section: m.section, matchStart: new Date(m.start), ownerId: DEMO_IDS[i % DEMO_IDS.length],
          block: "", ...list[i], gateKey: gateKey(list[i].gate), note: i === 0 ? "Δοκιμαστική θέση" : "",
          status: "open", sent: {}, created: t, updated: t,
        });
        created++;
      }
      await allocate(c, m.nt);
    }
    return { created };
  },

  // GET ?id=<αγώνας>: οι ελεύθερες θέσεις ενός αγώνα και η δική μου δήλωση.
  async match(req, c) {
    const id = String(req.query?.id || "");
    const [all, me] = await Promise.all([matches(), currentUser(req, c, { required: false })]);
    const m = all.get(id);
    if (!m) fail(404, "Ο αγώνας δεν βρέθηκε.");
    const isOpen = Date.now() < cutoffOf(m.start);
    const [offers, claim, seekers, mineActive] = await Promise.all([
      isOpen ? c.offers.find({ matchId: id, status: "open" }).sort({ created: 1 }).toArray() : [],
      me ? c.claims.findOne({ _id: `${me._id}:${id}` }) : null,
      c.claims.countDocuments({ matchId: id, status: "waiting" }),
      me ? c.offers.countDocuments({ matchId: id, ownerId: me._id, status: { $in: ["open", "assigned", "transferred", "received"] } }) : 0,
    ]);
    const owners = offers.map((o) => o.ownerId);
    const [people, given] = await Promise.all([nicks(c, owners), givenCounts(c, owners)]);
    return {
      deadline: deadlineOf(m.start),
      transferable: await transferable(id, m.section),
      seekers,
      giving: mineActive > 0,
      prefGate: me ? prefGate(me, m.section) : null,
      claim: claim ? { status: claim.status === "waiting" && !isOpen ? "expired" : claim.status, gate: claim.gate, rescued: Boolean(claim.rescued) } : null,
      offers: offers.map((o) => ({
        id: o._id, ...seatOf(o), note: o.note || "", created: o.created,
        owner: people[o.ownerId] || "—", given: given[o.ownerId] || 0,
        isMine: me ? o.ownerId === me._id : false,
      })),
    };
  },

  // GET: όλα όσα με αφορούν, ως κάτοχο και ως παραλήπτη, και οι ρυθμίσεις μου.
  async mine(req, c) {
    const me = await currentUser(req, c);
    const [offersRaw, claims, devices] = await Promise.all([
      c.offers.find({ ownerId: me._id, status: { $nin: ["withdrawn"] } }).sort({ matchStart: 1 }).limit(100).toArray(),
      c.claims.find({ userId: me._id, status: { $ne: "cancelled" } }).sort({ matchStart: 1 }).limit(100).toArray(),
      c.push.countDocuments({ userId: me._id }),
    ]);
    const now = Date.now();
    const lastDayMatches = claims.filter((cl) => cl.status === "waiting" && cl.gateKey && new Date(cl.matchStart).getTime() - now <= ALT_WINDOW).map((cl) => cl.matchId);
    const [theirRaw, altRaw] = await Promise.all([
      c.offers.find({ _id: { $in: claims.map((cl) => cl.offerId || cl.lateOfferId).filter(Boolean) } }).toArray(),
      lastDayMatches.length ? c.offers.find({ matchId: { $in: lastDayMatches }, status: "open" }).sort({ created: 1 }).toArray() : [],
    ]);
    const offers = offersRaw.map(effective);
    const theirById = Object.fromEntries(theirRaw.map(effective).map((o) => [o._id, o]));
    const people = await nicks(c, [...offers.map((o) => o.recipientId), ...theirRaw.map((o) => o.ownerId), ...altRaw.map((o) => o.ownerId)]);
    const canTransfer = {};
    for (const o of [...offers, ...Object.values(theirById)]) canTransfer[o._id] = await transferable(o.matchId, o.section);
    const stepOf = (o) => ({ step: o.step || null, due: o.due || null, late: Boolean(o.late), rescued: Boolean(o.rescued) });

    return {
      user: { nick: me.nick, prefs: { football: prefGate(me, "football"), basketball: prefGate(me, "basketball") }, devices },
      offers: offers.map((o) => ({
        id: o._id, matchId: o.matchId, ...seatOf(o), note: o.note || "", status: o.status, ...stepOf(o),
        deadline: deadlineOf(o.matchStart),
        recipient: o.recipientId ? people[o.recipientId] || "—" : null,
        // ΑΦΜ μόνο στον κάτοχο, μόνο στο βήμα της μεταβίβασης και πριν το κλείσιμο.
        afm: o.status === "assigned" && o.step === "transfer" && canTransfer[o._id] ? o.afm || null : null,
        transferable: canTransfer[o._id],
        canNotAccepted: o.status === "transferred" && o.step === "accept" && o.due && new Date(o.due).getTime() <= now,
      })),
      claims: claims.map((cl) => {
        const eff = cl.status === "waiting" && now >= cutoffOf(cl.matchStart) ? "expired" : cl.status;
        const o = theirById[cl.offerId];
        const late = cl.lateOfferId ? theirById[cl.lateOfferId] : null;
        return {
          id: cl._id, matchId: cl.matchId, status: eff, gate: cl.gate, rescued: Boolean(cl.rescued),
          offer: o && o.recipientId === me._id ? {
            id: o._id, ...seatOf(o), owner: people[o.ownerId] || "—", status: o.status, ...stepOf(o),
            afmSent: Boolean(o.afm) || ["transfer", "accept"].includes(o.step), transferable: canTransfer[o._id], deadline: deadlineOf(o.matchStart),
          } : null,
          lateOffer: late && late.status === "assigned" ? { owner: people[late.ownerId] || "—", due: late.due } : null,
          alts: eff === "waiting" && cl.gateKey && lastDayMatches.includes(cl.matchId)
            ? altRaw.filter((a) => a.matchId === cl.matchId && a.gateKey !== cl.gateKey && a.ownerId !== me._id && isOpenOffer(a))
              .map((a) => ({ id: a._id, ...seatOf(a), owner: people[a.ownerId] || "—" }))
            : [],
        };
      }),
    };
  },

  // POST {nick}: νέο ψευδώνυμο σε αυτή τη συσκευή.
  async register(req, c, body) {
    const nick = str(body.nick, 20, { required: true, label: "Ψευδώνυμο" });
    if (!/^[\p{L}\p{N}._-]{3,20}$/u.test(nick)) fail(400, "Ψευδώνυμο: 3–20 γράμματα, αριθμοί, τελεία, παύλα ή κάτω παύλα.");
    if (/^demo[_.-]/i.test(nick)) fail(400, "Τα ψευδώνυμα demo_ είναι για τους δοκιμαστικούς χρήστες.");
    const token = crypto.randomBytes(24).toString("base64url");
    try {
      await c.users.insertOne({ _id: newId(), nick, nickLower: nick.toLocaleLowerCase("el"), tokenHash: hash(token), created: new Date() });
    } catch (e) {
      if (e?.code === 11000) fail(409, "Το ψευδώνυμο το έχει ήδη κάποιος άλλος.");
      throw e;
    }
    return { token, nick };
  },

  // POST {section, gate | any}: η προεπιλεγμένη θύρα μου.
  async prefs(req, c, body) {
    const me = await currentUser(req, c);
    if (!SECTIONS.has(body.section)) fail(400, "Άγνωστο τμήμα.");
    const { gate } = gateFrom(body);
    await c.users.updateOne({ _id: me._id }, { $set: { [`prefs.${body.section}`]: { gate } } });
    return { ok: true };
  },

  // POST {matchId, gate | any}: μπαίνω στη λίστα (ή αλλάζω θύρα, κρατώντας τη σειρά μου).
  async join(req, c, body) {
    const me = await currentUser(req, c);
    const m = await openMatch(body.matchId);
    if (!m) fail(400, "Έκλεισαν οι μεταβιβάσεις για αυτόν τον αγώνα.");
    const cl = await joinList(c, me, m, gateFrom(body));
    return { status: cl.status };
  },

  // POST {matchId}: βγαίνω από τη λίστα.
  async leave(req, c, body) {
    const me = await currentUser(req, c);
    const cl = await c.claims.findOneAndUpdate({ _id: `${me._id}:${String(body.matchId || "")}`, status: "waiting" },
      { $set: { status: "cancelled", updated: new Date() } });
    if (!cl) fail(409, "Δεν είσαι στη λίστα αυτού του αγώνα.");
    if (cl.lateOfferId) await releaseLate(c, cl.lateOfferId, cl._id);
    return { ok: true };
  },

  // POST {offerId}: «Τη θέλω» σε συγκεκριμένη ελεύθερη θέση (π.χ. σε άλλη θύρα την τελευταία μέρα).
  async take(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOne({ _id: String(body.offerId || "") });
    if (!o || !isOpenOffer(o)) fail(409, "Τη θέση την πήρε ήδη κάποιος άλλος.");
    if (o.ownerId === me._id) fail(400, "Είναι δική σου θέση.");
    const m = await openMatch(o.matchId);
    const prev = await c.claims.findOne({ _id: `${me._id}:${o.matchId}` });
    const cl = await joinList(c, me, m, { gate: o.gate, gateKey: o.gateKey });
    if (cl.status === "assigned") return { status: "assigned", same: cl.offerId === o._id };
    // Δεν την πήρε (την πρόλαβε άλλος): η δήλωσή του γυρνά όπως ήταν.
    if (prev?.status === "waiting") {
      await c.claims.updateOne({ _id: prev._id, status: "waiting" }, { $set: { gate: prev.gate, gateKey: prev.gateKey } });
    }
    fail(409, "Τη θέση την πρόλαβε κάποιος άλλος. Παραμένεις στη λίστα.");
  },

  // POST {subscription}: αυτή η συσκευή παίρνει ειδοποιήσεις.
  async pushsub(req, c, body) {
    const me = await currentUser(req, c);
    const sub = body.subscription;
    if (!validSubscription(sub)) fail(400, "Μη έγκυρη συνδρομή.");
    await c.push.updateOne({ _id: subId(sub.endpoint) }, {
      $set: { userId: me._id, endpoint: sub.endpoint, keys: { p256dh: sub.keys.p256dh, auth: sub.keys.auth }, updated: new Date() },
    }, { upsert: true });
    return { ok: true };
  },

  // POST {endpoint}: αυτή η συσκευή δεν θέλει πια ειδοποιήσεις.
  async pushunsub(req, c, body) {
    const me = await currentUser(req, c);
    await c.push.deleteOne({ _id: subId(String(body.endpoint || "")), userId: me._id });
    return { ok: true };
  },

  // POST {matchId, gate, block, row, seat, note, free}: δίνω τη θέση μου (block μόνο στο μπάσκετ).
  async offer(req, c, body) {
    const me = await currentUser(req, c);
    const m = await openMatch(body.matchId);
    if (!m) fail(400, `Έκλεισαν οι μεταβιβάσεις για αυτόν τον αγώνα (γίνονται έως ${CUTOFF / HOUR} ώρες πριν).`);
    if (body.free !== true) fail(400, "Οι θέσεις δίνονται μόνο δωρεάν.");
    const gate = str(body.gate, 10, { required: true, label: "Θύρα" });
    if (!gateKey(gate)) fail(400, "Θύρα: υποχρεωτικό.");
    const block = m.section === "basketball" ? str(body.block, 6, { label: "Τμήμα" }) : "";
    const row = str(body.row, 6, { label: "Σειρά" });
    const seat = str(body.seat, 6, { label: "Θέση" });
    const note = str(body.note, 140, { label: "Σημείωση" });
    const mineOpen = await c.offers.countDocuments({ ownerId: me._id, matchId: m.nt, status: { $in: ["open", "assigned", "transferred"] } });
    if (mineOpen >= MAX_OPEN_OFFERS_PER_MATCH) fail(429, `Έως ${MAX_OPEN_OFFERS_PER_MATCH} θέσεις ανά αγώνα.`);
    // Όποιος δίνει θέση δεν περιμένει στη λίστα του ίδιου αγώνα.
    const own = await c.claims.findOneAndUpdate({ _id: `${me._id}:${m.nt}`, status: "waiting" }, { $set: { status: "cancelled", updated: new Date() } });
    if (own?.lateOfferId) await releaseLate(c, own.lateOfferId, own._id);
    const now = new Date();
    const doc = {
      _id: newId(), matchId: m.nt, section: m.section, matchStart: new Date(m.start), ownerId: me._id,
      gate, gateKey: gateKey(gate), block, row, seat, note, status: "open", sent: {}, created: now, updated: now,
    };
    await c.offers.insertOne(doc);
    await allocate(c, m.nt);
    const after = await c.offers.findOne({ _id: doc._id }, { projection: { status: 1 } });
    return { id: doc._id, assigned: after.status === "assigned" };
  },

  // POST {offerId}: «Τελικά θα πάω». Αν υπήρχε παραλήπτης, μπαίνει πρώτος για άλλη θέση.
  async reclaim(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOne({ _id: String(body.offerId || ""), ownerId: me._id, status: { $in: ["open", "assigned", "transferred", "received"] } });
    if (!o) fail(409, "Η θέση δεν είναι πια ενεργή.");
    const now = new Date();
    const r = await c.offers.updateOne({ _id: o._id, status: o.status },
      { $set: { status: o.status === "open" ? "withdrawn" : "reclaimed", updated: now }, $unset: { afm: "", step: "", due: "" } });
    if (!r.modifiedCount) fail(409, "Η θέση άλλαξε στο μεταξύ. Δοκίμασε ξανά.");
    if (o.status === "open") return { ok: true, revoke: false };
    const m = (await matches()).get(o.matchId);
    const cl = await c.claims.findOne({ _id: o.claimId });
    // Ο παραλήπτης που είχε ήδη βρει άλλη θέση (ή είχε γυρίσει σε αυτή) δεν επηρεάζεται.
    if (cl && (cl.offerId === o._id || cl.lateOfferId === o._id)) {
      await rescue(c, cl._id);
      await c.claims.updateOne({ _id: cl._id }, { $unset: { lateOfferId: "" } });
      await notify(c, [o.recipientId], {
        title: "Ο κάτοχος θα πάει τελικά",
        body: `Σου ψάχνουμε άλλη θέση για ${titleOf(m)} και είσαι πρώτος στη λίστα.` + (o.status !== "assigned" ? " Το εισιτήριο θα ανακληθεί από το Wallet σου." : ""),
        tag: `seat-${o._id}`,
      });
      await allocate(c, o.matchId);
    }
    return { ok: true, revoke: o.status !== "assigned" };
  },

  // POST {offerId, afm}: ο παραλήπτης στέλνει τον ΑΦΜ του στον κάτοχο.
  async afm(req, c, body) {
    const me = await currentUser(req, c);
    const afm = String(body.afm || "").replace(/\s/g, "");
    if (!validAfm(afm)) fail(400, "Ο ΑΦΜ δεν είναι έγκυρος.");
    const o = await c.offers.findOne({ _id: String(body.offerId || ""), recipientId: me._id, status: "assigned" });
    if (!o) fail(409, "Δεν μπορεί να σταλεί ΑΦΜ για αυτή τη θέση τώρα.");
    if (o.step === "wait") fail(409, "Η μεταβίβαση ανοίγει όταν τελειώσει ο προηγούμενος εντός έδρας αγώνας.");
    if (o.step !== "afm" || !(await transferable(o.matchId, o.section))) fail(409, "Δεν μπορεί να σταλεί ΑΦΜ για αυτή τη θέση τώρα.");
    if (!(await doAfm(c, o, afm))) fail(409, "Η θέση άλλαξε στο μεταξύ.");
    return { ok: true };
  },

  // POST {offerId}: ο κάτοχος έκανε τη μεταβίβαση στο Gov.gr Wallet.
  async transferred(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOne({ _id: String(body.offerId || ""), ownerId: me._id, status: "assigned", step: "transfer", afm: { $exists: true } });
    if (!o) fail(409, "Χρειάζεται πρώτα ο ΑΦΜ του παραλήπτη.");
    if (!(await transferable(o.matchId, o.section))) fail(409, "Έκλεισαν οι μεταβιβάσεις για αυτόν τον αγώνα.");
    if (!(await doTransfer(c, o))) fail(409, "Ο παραλήπτης βρήκε στο μεταξύ άλλη θέση. Αν έκανες ήδη μεταβίβαση, κάνε ανάκληση στο Wallet.");
    return { ok: true };
  },

  // POST {offerId}: ο παραλήπτης το αποδέχτηκε στο Wallet. Ο ΑΦΜ σβήνεται.
  async received(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOne({ _id: String(body.offerId || ""), recipientId: me._id, status: "transferred" });
    if (!o) fail(409, "Ο κάτοχος δεν έχει δηλώσει ακόμα ότι έκανε τη μεταβίβαση.");
    await doReceive(c, o);
    return { ok: true };
  },

  // POST {offerId}: ο παραλήπτης δεν μπορεί τελικά (πριν τη μεταβίβαση). Η θέση πάει στον επόμενο.
  async backout(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOne({ _id: String(body.offerId || ""), recipientId: me._id, status: "assigned" });
    if (!o) fail(409, "Η μεταβίβαση έχει ήδη γίνει· ζήτα από τον κάτοχο να κάνει ανάκληση.");
    const r = await c.offers.updateOne({ _id: o._id, status: "assigned", recipientId: me._id }, { $set: { status: "open", sent: {}, updated: new Date() }, $unset: OFFER_RESET });
    if (!r.modifiedCount) fail(409, "Η θέση άλλαξε στο μεταξύ.");
    await c.claims.updateOne({ _id: o.claimId }, { $set: { status: "cancelled", updated: new Date() }, $unset: { offerId: "", lateOfferId: "" } });
    await notify(c, [o.ownerId], { title: `Ο @${me.nick} δεν μπορεί τελικά`, body: `Η θέση σου (${seatLine(o)}) πάει στον επόμενο της λίστας.`, tag: `seat-${o._id}` });
    await allocate(c, o.matchId);
    return { ok: true };
  },

  // POST {offerId}: ο κάτοχος δηλώνει ότι ο παραλήπτης δεν αποδέχτηκε το εισιτήριο (αφού έληξε ο χρόνος).
  async notaccepted(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOne({ _id: String(body.offerId || ""), ownerId: me._id, status: "transferred", step: "accept" });
    if (!o || !o.due || new Date(o.due) > new Date()) fail(409, "Περίμενε να λήξει ο χρόνος του παραλήπτη.");
    const r = await c.offers.updateOne({ _id: o._id, status: "transferred" }, { $set: { status: "open", sent: {}, updated: new Date() }, $unset: OFFER_RESET });
    if (!r.modifiedCount) fail(409, "Η θέση άλλαξε στο μεταξύ.");
    await c.claims.updateOne({ _id: o.claimId }, { $set: { status: "timedout", updated: new Date() }, $unset: { offerId: "" } });
    const m = (await matches()).get(o.matchId);
    await notify(c, [o.recipientId], { title: "Η θέση πήγε στον επόμενο", body: `Δεν επιβεβαίωσες εγκαίρως για ${titleOf(m)}. Αν θες ακόμα θέση, ξαναμπές στη λίστα.`, tag: `seat-${o._id}`, url: `${PAGE}#/m/${o.matchId}` });
    await allocate(c, o.matchId);
    return { ok: true };
  },
};

const GET_ACTIONS = new Set(["summary", "match", "mine"]);

export default async function handler(req, res) {
  if (!configured()) return send(res, 503, { error: "Η βάση δεν έχει ρυθμιστεί." });
  const a = String(req.query?.a || "");
  const fn = Object.hasOwn(actions, a) ? actions[a] : null;
  if (!fn) return send(res, 404, { error: "Άγνωστη ενέργεια." });
  const wantGet = GET_ACTIONS.has(a);
  if (req.method !== (wantGet ? "GET" : "POST")) return send(res, 405, { error: wantGet ? "Μόνο GET." : "Μόνο POST." });
  try {
    const c = await cols();
    if (a === "tick") await housekeeping(c, { fresh: true });
    const out = await fn(req, c, wantGet ? {} : await readBody(req));
    // Οι demo χρήστες απαντούν αμέσως μετά από κάθε ενέργεια, ώστε να φαίνεται στην επόμενη οθόνη.
    if (!wantGet && a !== "tick" && DEMO) await demoBots(c);
    send(res, 200, out);
    // Η συντήρηση τρέχει στο παρασκήνιο, το πολύ μία φορά το λεπτό, για να μην καθυστερεί κανέναν.
    if (a !== "tick" && Date.now() - lastMaintenance > MAINTENANCE_EVERY) {
      waitUntil(housekeeping(c).catch((e) => console.error("tx housekeeping", e)));
    }
  } catch (e) {
    if (e instanceof Fail) return send(res, e.status, { error: e.message });
    console.error("tx", a, e);
    return send(res, 500, { error: "Κάτι πήγε στραβά. Δοκίμασε ξανά.", detail: String(e?.code || e?.name || "unknown").slice(0, 40) });
  }
}
