// Μεταβιβάσεις εισιτηρίων διαρκείας (δοκιμαστική έκδοση): κάτοχοι που δεν πάνε σε έναν εντός έδρας
// αγώνα δίνουν δωρεάν τη θέση τους και άλλοι φίλαθλοι τη ζητούν. Η ίδια η μεταβίβαση γίνεται στο
// Gov.gr Wallet· εδώ γίνεται μόνο η συνεννόηση.
//
// Ένα endpoint, ενέργεια με ?a=<ενέργεια>. Ταυτότητα: ψευδώνυμο και κλειδί συσκευής
// (Authorization: Bearer <token>)· στη βάση κρατιέται μόνο το hash του κλειδιού.
//
// Συλλογές MongoDB (ίδια βάση με τις ειδοποιήσεις):
//   tx_users     {_id, nick, nickLower, tokenHash, created, prefs}
//                prefs.<football|basketball> = {gates: ["4"], others, alerts}
//   tx_offers    {_id, matchId, section, matchStart, ownerId, gate, gateKey, block, row, seat, note,
//                 status, recipientId, requestId, afm, priorityUntil, sent: {…}, created, updated}
//                status: open → assigned → transferred → received → closed (ή withdrawn / expired)
//   tx_requests  {_id, offerId, matchId, userId, status, created, updated}
//                status: pending → chosen | declined | cancelled
//   tx_waits     {_id: "<user>:<match>", userId, matchId, section, created}: «ειδοποίησέ με για θέση»
//   tx_push      {_id, userId, endpoint, keys, updated}: συσκευές με ειδοποιήσεις web push
//
// Κανόνες του Gov.gr Wallet:
// - Η μεταβίβαση ισχύει για τον ΕΠΟΜΕΝΟ αγώνα του διαρκείας και μετά το εισιτήριο επιστρέφει. Θέση
//   δίνεται και για μεταγενέστερο αγώνα, αλλά ΑΦΜ και μεταβίβαση ανοίγουν όταν ο αγώνας γίνει ο
//   επόμενος εντός έδρας του τμήματος (δηλαδή τελειώσει ο προηγούμενος).
// - Η μεταβίβαση γίνεται έως 6 ώρες πριν την έναρξη. Τότε κλείνουν και οι ανοιχτές θέσεις.
//
// Προτεραιότητα ανά θύρα: μια νέα θέση τη ζητούν πρώτα όσοι έχουν δηλώσει την ίδια θύρα, για
// PRIORITY_MS (λιγότερο αν πλησιάζει η προθεσμία). Μετά ανοίγει σε όλους.
//
// Ο ΑΦΜ του παραλήπτη τον βλέπει μόνο ο κάτοχος της θέσης, και σβήνεται μόλις ο παραλήπτης
// επιβεβαιώσει ότι πήρε το εισιτήριο, αν ακυρωθεί η μεταβίβαση ή όταν περάσει η προθεσμία.
//
// Οι χρονικές ειδοποιήσεις (τέλος προτεραιότητας, άνοιγμα μεταβίβασης, υπενθύμιση προθεσμίας)
// στέλνονται σε κάθε κλήση και από το ?a=tick, που το καλεί κάθε 15' το reminders.yml.
//
// Στη δοκιμαστική φάση υπάρχουν χρήστες demo_* που απαντούν αυτόματα, ώστε η ροή να δοκιμάζεται
// και από έναν άνθρωπο (?a=seed βάζει δοκιμαστικές θέσεις). Κλείνουν με TX_DEMO=0.
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { SITE, configured, getDb, pushTo, readBody, send, subId, validSubscription, vapidKeys } from "./_lib.js";

const SECTIONS = new Set(["football", "basketball"]);
const MAX_OPEN_OFFERS_PER_MATCH = 4;
const MAX_ACTIVE_REQUESTS_PER_MATCH = 3;
const MAX_GATES = 2;
const HOUR = 3600 * 1000;
// Πόσο μετά την έναρξη θεωρούμε ότι τελείωσε ένας αγώνας (για να «ανοίξει» ο επόμενος).
const MATCH_LENGTH = 3 * HOUR;
// Η μεταβίβαση στο Wallet γίνεται έως τόσο πριν την έναρξη.
const CUTOFF = 6 * HOUR;
// Πόση ώρα έχουν προτεραιότητα όσοι είναι στην ίδια θύρα.
const PRIORITY_MS = 2 * HOUR;
// Υπενθύμιση τόσο πριν λήξει η προθεσμία μεταβίβασης.
const REMIND_BEFORE = 2 * HOUR;
const PAGE = "/metavivaseis/";
// Όσο η σελίδα είναι δοκιμαστική, οι demo χρήστες είναι ενεργοί παντού. Για πραγματική χρήση:
// μεταβλητή TX_DEMO=0 στο Vercel (χωρίς αλλαγή κώδικα).
const DEMO = process.env.TX_DEMO !== "0";
const TEST_AFM = "123456783";
const DEMO_USERS = [
  { _id: "demo-1", nick: "demo_toumba" },
  { _id: "demo-2", nick: "demo_maria" },
  { _id: "demo-3", nick: "demo_vasilis" },
];
const DEMO_IDS = DEMO_USERS.map((u) => u._id);

// ---------- Αγώνες ----------
// Από το docs/matches.json που συνοδεύει τη λειτουργία· αν δεν βρεθεί (π.χ. σε preview), από τη
// δημόσια σελίδα. Κρατιούνται 10 λεπτά.
let matchCache = null;
async function readMatches() {
  const candidates = [
    new URL("../docs/matches.json", import.meta.url),
    path.join(process.cwd(), "docs", "matches.json"),
  ];
  for (const file of candidates) {
    try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { /* επόμενο */ }
  }
  const res = await fetch(`${SITE}/matches.json`, { headers: { "Cache-Control": "no-cache" } });
  if (!res.ok) throw new Error(`matches.json: HTTP ${res.status}`);
  return res.json();
}
async function matches() {
  if (matchCache && Date.now() - matchCache.at < 10 * 60 * 1000) return matchCache.byId;
  const data = await readMatches();
  const byId = new Map();
  for (const m of data.matches || []) {
    if (m.nt && m.paokHome && SECTIONS.has(m.section)) byId.set(m.nt, m);
  }
  matchCache = { at: Date.now(), byId };
  return byId;
}
const startOf = (m) => new Date(m.start).getTime();
const deadlineOf = (start) => new Date(new Date(start).getTime() - CUTOFF);

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
// Μπορεί να γίνει τώρα η μεταβίβαση στο Wallet για αυτόν τον αγώνα; (επόμενος και πριν την προθεσμία)
async function transferable(matchId, section) {
  const n = await nextFor(section);
  return Boolean(n && n.nt === matchId && Date.now() < deadlineOf(n.start).getTime());
}
// Αγώνας για τον οποίο δέχεται ακόμα θέσεις και αιτήματα (πριν την προθεσμία μεταβίβασης).
async function openMatch(id) {
  const m = (await matches()).get(String(id || ""));
  return m && Date.now() < deadlineOf(m.start).getTime() ? m : null;
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

// Έλεγχος ΑΦΜ με το ψηφίο ελέγχου.
export function validAfm(afm) {
  if (!/^\d{9}$/.test(afm) || afm === "000000000") return false;
  let sum = 0;
  for (let i = 0; i < 8; i++) sum += Number(afm[i]) * 2 ** (8 - i);
  return (sum % 11) % 10 === Number(afm[8]);
}

const TZ = "Europe/Athens";
const fmtWhen = (d) => new Intl.DateTimeFormat("el-GR", {
  timeZone: TZ, weekday: "short", day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
}).format(new Date(d));
const fmtTime = (d) => new Intl.DateTimeFormat("el-GR", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date(d));
const titleOf = (m) => (m ? `${m.home} – ${m.away}` : "Αγώνας");
function seatLine(o) {
  return [`Θύρα ${o.gate}`, o.block && `Τμήμα ${o.block}`, o.row && `Σειρά ${o.row}`, o.seat && `Θέση ${o.seat}`].filter(Boolean).join(" · ");
}

let indexesReady = null;
async function cols() {
  const db = await getDb();
  const c = {
    users: db.collection("tx_users"),
    offers: db.collection("tx_offers"),
    requests: db.collection("tx_requests"),
    waits: db.collection("tx_waits"),
    push: db.collection("tx_push"),
  };
  indexesReady ??= Promise.all([
    c.users.createIndex({ nickLower: 1 }, { unique: true }),
    c.users.createIndex({ tokenHash: 1 }, { unique: true }),
    c.offers.createIndex({ matchId: 1, status: 1 }),
    c.offers.createIndex({ ownerId: 1 }),
    c.offers.createIndex({ recipientId: 1 }),
    c.requests.createIndex({ offerId: 1, userId: 1 }, { unique: true }),
    c.requests.createIndex({ userId: 1 }),
    c.waits.createIndex({ matchId: 1 }),
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

const prefsOf = (user, section) => {
  const p = user?.prefs?.[section] || {};
  return { gates: Array.isArray(p.gates) ? p.gates : [], others: p.others !== false, alerts: Boolean(p.alerts) };
};
const inGate = (user, offer) => prefsOf(user, offer.section).gates.some((g) => gateKey(g) === offer.gateKey);
const inPriority = (offer, now = Date.now()) => offer.priorityUntil && new Date(offer.priorityUntil).getTime() > now;

// ---------- Ειδοποιήσεις web push ----------
let keysPromise = null;
async function notify(c, userIds, { title, body, tag }) {
  const ids = [...new Set(userIds.filter((id) => id && !DEMO_IDS.includes(id)))];
  if (!ids.length) return 0;
  const devices = await c.push.find({ userId: { $in: ids } }).toArray();
  if (!devices.length) return 0;
  keysPromise ??= vapidKeys().catch((e) => { keysPromise = null; throw e; });
  const keys = await keysPromise;
  const payload = { title: title.slice(0, 120), body: String(body || "").slice(0, 300), url: `${PAGE}#/mine`, tag };
  const results = await Promise.all(devices.map((d) => pushTo(d, payload, keys, 6 * 3600)));
  const gone = devices.filter((_, i) => results[i] === "gone").map((d) => d._id);
  if (gone.length) await c.push.deleteMany({ _id: { $in: gone } });
  return results.filter((r) => r === "ok").length;
}

// Ποιοι θέλουν ειδοποίηση για νέα θέση: όσοι περιμένουν σε αυτόν τον αγώνα ή έχουν ζητήσει
// ειδοποίηση για κάθε αγώνα του τμήματος.
async function seekers(c, offer) {
  const waits = await c.waits.find({ matchId: offer.matchId }).toArray();
  const ids = new Set(waits.map((w) => w.userId));
  const alerting = await c.users.find({ [`prefs.${offer.section}.alerts`]: true }, { projection: { _id: 1 } }).toArray();
  alerting.forEach((u) => ids.add(u._id));
  ids.delete(offer.ownerId);
  if (!ids.size) return [];
  return c.users.find({ _id: { $in: [...ids] } }).toArray();
}

// Νέα θέση: ειδοποίηση πρώτα σε όσους είναι στην ίδια θύρα· στους υπόλοιπους όταν λήξει η
// προτεραιότητα (ή αμέσως, αν δεν υπάρχει).
async function announceOffer(c, offer, phase) {
  const m = (await matches()).get(offer.matchId);
  const people = await seekers(c, offer);
  if (phase === "priority") {
    const ids = people.filter((u) => inGate(u, offer)).map((u) => u._id);
    return notify(c, ids, {
      title: `Θέση στη Θύρα ${offer.gate}: ${titleOf(m)}`,
      body: `${seatLine(offer)}. Έχεις προτεραιότητα ως τις ${fmtTime(offer.priorityUntil)}.`,
      tag: `offer-${offer._id}`,
    });
  }
  const ids = people.filter((u) => !inGate(u, offer) && prefsOf(u, offer.section).others).map((u) => u._id);
  return notify(c, ids, {
    title: `Νέα θέση: ${titleOf(m)}`,
    body: `${seatLine(offer)} · δωρεάν από @${(await nickOf(c, offer.ownerId))}.`,
    tag: `offer-${offer._id}`,
  });
}

async function nickOf(c, id) {
  return (await c.users.findOne({ _id: id }, { projection: { nick: 1 } }))?.nick || "—";
}

// Μία φορά ανά γεγονός: «κλειδώνει» τη σημαία sent.<key> και επιστρέφει true μόνο στον πρώτο.
async function once(c, offerId, key) {
  const r = await c.offers.updateOne({ _id: offerId, [`sent.${key}`]: { $ne: true } }, { $set: { [`sent.${key}`]: true } });
  return r.modifiedCount === 1;
}

// Χρονικά γεγονότα: τέλος προτεραιότητας, άνοιγμα μεταβίβασης, υπενθύμιση προθεσμίας.
async function timedNotifications(c) {
  const now = new Date();
  // Τέλος προτεραιότητας θύρας → ειδοποίηση στους υπόλοιπους.
  const ended = await c.offers.find({ status: "open", priorityUntil: { $lte: now }, "sent.openAll": { $ne: true } }).limit(50).toArray();
  for (const o of ended) if (await once(c, o._id, "openAll")) await announceOffer(c, o, "all");

  const active = await c.offers.find({ status: "assigned", matchStart: { $gt: now } }).limit(200).toArray();
  for (const o of active) {
    if (!(await transferable(o.matchId, o.section))) continue;
    const m = (await matches()).get(o.matchId);
    const deadline = deadlineOf(o.matchStart);
    // Άνοιξε η μεταβίβαση: ο παραλήπτης στέλνει ΑΦΜ.
    if (!o.afm && (await once(c, o._id, "transferOpen"))) {
      await notify(c, [o.recipientId], {
        title: "Στείλε τον ΑΦΜ σου",
        body: `Άνοιξε η μεταβίβαση για ${titleOf(m)}. Στείλε τον ΑΦΜ σου ως ${fmtWhen(deadline)}.`,
        tag: `afm-${o._id}`,
      });
    }
    // Υπενθύμιση πριν λήξει η προθεσμία.
    if (deadline.getTime() - now.getTime() <= REMIND_BEFORE && (await once(c, o._id, "deadline"))) {
      if (!o.afm) {
        await notify(c, [o.recipientId], {
          title: "Λήγει η προθεσμία",
          body: `Στείλε τον ΑΦΜ σου για ${titleOf(m)} ως τις ${fmtTime(deadline)}, αλλιώς η θέση χάνεται.`,
          tag: `afm-${o._id}`,
        });
      } else {
        await notify(c, [o.ownerId], {
          title: "Λήγει η προθεσμία μεταβίβασης",
          body: `Κάνε τη μεταβίβαση στο Gov.gr Wallet για ${titleOf(m)} ως τις ${fmtTime(deadline)}.`,
          tag: `tx-${o._id}`,
        });
      }
    }
  }
}

// Κλείνει θέσεις μετά την προθεσμία, σβήνει ΑΦΜ, ολοκληρώνει όσες τελείωσαν, στέλνει χρονικές
// ειδοποιήσεις και (στη δοκιμαστική φάση) κινεί τους demo χρήστες.
async function housekeeping(c) {
  const now = new Date();
  const cutoff = new Date(now.getTime() + CUTOFF); // αγώνες που αρχίζουν πριν από αυτό έχουν κλείσει
  const ended = new Date(now.getTime() - MATCH_LENGTH);
  await c.offers.updateMany({ matchStart: { $lt: cutoff }, afm: { $exists: true } }, { $unset: { afm: "" } });
  await c.offers.updateMany({ matchStart: { $lt: cutoff }, status: { $in: ["open", "assigned"] } }, { $set: { status: "expired", updated: now } });
  await c.offers.updateMany({ matchStart: { $lt: ended }, status: { $in: ["transferred", "received"] } }, { $set: { status: "closed", updated: now } });
  await c.waits.deleteMany({ matchStart: { $lt: cutoff } });
  if (DEMO) await demoBots(c);
  await timedNotifications(c);
}

// Ο κάτοχος διαλέγει ένα αίτημα: η θέση πάει σε αυτόν, τα υπόλοιπα αιτήματα απορρίπτονται.
async function chooseRequest(c, ownerId, r) {
  const now = new Date();
  const o = await c.offers.findOneAndUpdate(
    { _id: r.offerId, ownerId, status: "open" },
    { $set: { status: "assigned", recipientId: r.userId, requestId: r._id, updated: now } },
  );
  if (!o) return null;
  await c.requests.updateOne({ _id: r._id }, { $set: { status: "chosen", updated: now } });
  const others = await c.requests.find({ offerId: o._id, _id: { $ne: r._id }, status: "pending" }).toArray();
  await c.requests.updateMany({ offerId: o._id, _id: { $ne: r._id }, status: "pending" }, { $set: { status: "declined", updated: now } });

  const m = (await matches()).get(o.matchId);
  const owner = await nickOf(c, ownerId);
  const canNow = await transferable(o.matchId, o.section);
  if (canNow) await once(c, o._id, "transferOpen"); // η ειδοποίηση επιλογής λέει ήδη «στείλε ΑΦΜ»
  const n = canNow ? null : await nextFor(o.section);
  await notify(c, [r.userId], {
    title: `Σε επέλεξε ο @${owner}!`,
    body: canNow
      ? `${titleOf(m)} · ${seatLine(o)}. Στείλε τον ΑΦΜ σου ως ${fmtWhen(deadlineOf(o.matchStart))}.`
      : `${titleOf(m)} · ${seatLine(o)}. Θα σου ζητηθεί ο ΑΦΜ μετά το ${titleOf(n)}.`,
    tag: `chosen-${o._id}`,
  });
  await notify(c, others.map((x) => x.userId), {
    title: "Η θέση δόθηκε σε άλλον",
    body: `${titleOf(m)} · ${seatLine(o)}. Δες αν υπάρχουν άλλες θέσεις.`,
    tag: `declined-${o._id}`,
  });
  return o;
}

// ---------- Δοκιμαστικοί χρήστες (μόνο στη δοκιμαστική φάση) ----------
async function ensureDemoUsers(c) {
  for (const u of DEMO_USERS) {
    await c.users.updateOne({ _id: u._id }, {
      $setOnInsert: { nick: u.nick, nickLower: u.nick, demo: true, tokenHash: hash(crypto.randomBytes(24).toString("hex")), created: new Date() },
    }, { upsert: true });
  }
}

// Οι demo χρήστες κάνουν μόνοι τους το επόμενο βήμα, σε κάθε ρόλο.
async function demoBots(c) {
  const now = new Date();
  // Ζητούν τις θέσεις των αληθινών χρηστών (μία φορά ανά θέση).
  const openReal = await c.offers.find({ status: "open", ownerId: { $nin: DEMO_IDS }, matchStart: { $gt: now } }).limit(50).toArray();
  for (const o of openReal) {
    if (await c.requests.findOne({ offerId: o._id, userId: { $in: DEMO_IDS } })) continue;
    const uid = DEMO_IDS[o._id.charCodeAt(0) % DEMO_IDS.length];
    await ensureDemoUsers(c);
    const res = await c.requests.updateOne({ offerId: o._id, userId: uid },
      { $setOnInsert: { _id: newId(), matchId: o.matchId, status: "pending", created: now, updated: now } }, { upsert: true });
    if (res.upsertedCount) {
      await notify(c, [o.ownerId], { title: "Νέο αίτημα για τη θέση σου", body: `@${await nickOf(c, uid)} · ${seatLine(o)}`, tag: `req-${o._id}` });
    }
  }
  // Ως κάτοχοι διαλέγουν το πρώτο αίτημα.
  for (const o of await c.offers.find({ status: "open", ownerId: { $in: DEMO_IDS } }).toArray()) {
    const r = await c.requests.find({ offerId: o._id, status: "pending" }).sort({ created: 1 }).limit(1).next();
    if (r) await chooseRequest(c, o.ownerId, r);
  }
  // Ως κάτοχοι κάνουν τη μεταβίβαση μόλις έχουν ΑΦΜ και είναι η σειρά του αγώνα.
  for (const o of await c.offers.find({ status: "assigned", ownerId: { $in: DEMO_IDS }, afm: { $exists: true } }).toArray()) {
    if (await transferable(o.matchId, o.section)) {
      const r = await c.offers.updateOne({ _id: o._id, status: "assigned" }, { $set: { status: "transferred", updated: now } });
      if (r.modifiedCount) {
        await notify(c, [o.recipientId], { title: "Έγινε η μεταβίβαση", body: "Αποδέξου το εισιτήριο στο Gov.gr Wallet και πάτα «Το πήρα».", tag: `tx-${o._id}` });
      }
    }
  }
  // Ως παραλήπτες στέλνουν τον δοκιμαστικό ΑΦΜ όταν ανοίξει η μεταβίβαση…
  for (const o of await c.offers.find({ status: "assigned", recipientId: { $in: DEMO_IDS }, afm: { $exists: false } }).toArray()) {
    if (await transferable(o.matchId, o.section)) {
      const r = await c.offers.updateOne({ _id: o._id, status: "assigned" }, { $set: { afm: TEST_AFM, updated: now } });
      if (r.modifiedCount) {
        await notify(c, [o.ownerId], { title: `Ο @${await nickOf(c, o.recipientId)} έστειλε ΑΦΜ`, body: `Κάνε τη μεταβίβαση στο Gov.gr Wallet ως ${fmtWhen(deadlineOf(o.matchStart))}.`, tag: `tx-${o._id}` });
      }
    }
  }
  // …και επιβεβαιώνουν ότι το πήραν.
  for (const o of await c.offers.find({ status: "transferred", recipientId: { $in: DEMO_IDS } }).toArray()) {
    const r = await c.offers.updateOne({ _id: o._id, status: "transferred" }, { $set: { status: "received", updated: now }, $unset: { afm: "" } });
    if (r.modifiedCount) await notify(c, [o.ownerId], { title: `Ο @${await nickOf(c, o.recipientId)} πήρε το εισιτήριο`, body: "Ευχαριστούμε που έδωσες τη θέση σου!", tag: `tx-${o._id}` });
  }
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
  const rows = await c.users.find({ _id: { $in: uniq } }, { projection: { nick: 1, prefs: 1 } }).toArray();
  return Object.fromEntries(rows.map((u) => [u._id, u]));
}

// block = «Τμήμα» (μόνο στο μπάσκετ: Θύρα · Τμήμα · Σειρά · Θέση).
const seatOf = (o) => ({ gate: o.gate, block: o.block || "", row: o.row || "", seat: o.seat || "" });
const publicPrefs = (user) => ({ football: prefsOf(user, "football"), basketball: prefsOf(user, "basketball") });

// ---------- Ενέργειες ----------
const actions = {
  // GET: σύνοψη ανά αγώνα (ανοιχτές θέσεις, πόσοι ψάχνουν). Δημόσιο.
  async summary(req, c) {
    const now = new Date();
    const open = await c.offers.find({ status: "open", matchStart: { $gt: now } }, { projection: { matchId: 1 } }).toArray();
    const reqs = await c.requests.find({ status: "pending" }, { projection: { matchId: 1, userId: 1 } }).toArray();
    const waits = await c.waits.find({}, { projection: { matchId: 1, userId: 1 } }).toArray();
    const out = {};
    const slot = (id) => (out[id] ??= { offers: 0, seekers: new Set() });
    for (const o of open) slot(o.matchId).offers++;
    for (const r of [...reqs, ...waits]) slot(r.matchId).seekers.add(r.userId);
    for (const v of Object.values(out)) v.seekers = v.seekers.size;
    return { matches: out, demo: DEMO, cutoffHours: CUTOFF / HOUR };
  },

  // POST: χρονικές ειδοποιήσεις και καθαριότητα (το καλεί το reminders.yml κάθε 15').
  async tick() {
    return { ok: true };
  },

  // POST: δοκιμαστικές θέσεις από τους demo χρήστες στους 2 επόμενους εντός έδρας αγώνες
  // ποδοσφαίρου και στον επόμενο του μπάσκετ. Δεν ξαναβάζει σε αγώνα που έχει ήδη.
  async seed(req, c) {
    if (!DEMO) fail(403, "Μόνο στη δοκιμαστική έκδοση.");
    await ensureDemoUsers(c);
    const now = Date.now();
    const all = [...(await matches()).values()];
    const pick = (section, n) => all.filter((m) => m.section === section && deadlineOf(m.start).getTime() > now)
      .sort((a, b) => a.start.localeCompare(b.start)).slice(0, n);
    const targets = [...pick("football", 2), ...pick("basketball", 1)];
    const seats = {
      football: [{ gate: "4", row: "12", seat: "8" }, { gate: "1", row: "", seat: "" }, { gate: "7", row: "30", seat: "15" }],
      basketball: [{ gate: "2", block: "Β", row: "6", seat: "11" }, { gate: "4", block: "Δ", row: "", seat: "" }],
    };
    let created = 0;
    for (const m of targets) {
      if (await c.offers.findOne({ matchId: m.nt, ownerId: { $in: DEMO_IDS }, status: "open" })) continue;
      const list = seats[m.section];
      for (let i = 0; i < list.length; i++) {
        const t = new Date();
        await c.offers.insertOne({
          _id: newId(), matchId: m.nt, section: m.section, matchStart: new Date(m.start), ownerId: DEMO_IDS[i % DEMO_IDS.length],
          block: "", ...list[i], gateKey: gateKey(list[i].gate), note: i === 0 ? "Δοκιμαστική θέση" : "",
          status: "open", priorityUntil: t, sent: { openAll: true }, created: t, updated: t,
        });
        created++;
      }
    }
    return { created };
  },

  // GET ?id=<αγώνας>: οι ανοιχτές θέσεις ενός αγώνα, τι έχω ζητήσει και αν περιμένω.
  async match(req, c) {
    const id = String(req.query?.id || "");
    const m = (await matches()).get(id);
    if (!m) fail(404, "Ο αγώνας δεν βρέθηκε.");
    const me = await currentUser(req, c, { required: false });
    const offers = await c.offers.find({ matchId: id, status: "open" }).sort({ created: 1 }).toArray();
    const owners = offers.map((o) => o.ownerId);
    const [people, given] = await Promise.all([nicks(c, owners), givenCounts(c, owners)]);
    let mine = {};
    let waiting = false;
    if (me) {
      const rs = await c.requests.find({ matchId: id, userId: me._id, status: { $in: ["pending", "chosen"] } }).toArray();
      mine = Object.fromEntries(rs.map((r) => [r.offerId, { requestId: r._id, status: r.status }]));
      waiting = Boolean(await c.waits.findOne({ _id: `${me._id}:${id}` }));
    }
    const now = Date.now();
    return {
      deadline: deadlineOf(m.start),
      transferable: await transferable(id, m.section),
      waiting,
      prefs: me ? prefsOf(me, m.section) : null,
      offers: offers.map((o) => ({
        id: o._id, ...seatOf(o), note: o.note || "", created: o.created,
        owner: people[o.ownerId]?.nick || "—", given: given[o.ownerId] || 0,
        isMine: me ? o.ownerId === me._id : false,
        myGate: me ? inGate(me, o) : false,
        priorityUntil: inPriority(o, now) ? o.priorityUntil : null,
        myRequest: mine[o._id] || null,
      })),
    };
  },

  // GET: όλα όσα με αφορούν, ως κάτοχο και ως παραλήπτη, και οι ρυθμίσεις μου.
  async mine(req, c) {
    const me = await currentUser(req, c);
    const offers = await c.offers.find({ ownerId: me._id, status: { $nin: ["withdrawn"] } })
      .sort({ matchStart: 1 }).limit(100).toArray();
    const offerIds = offers.map((o) => o._id);
    const reqsOnMine = await c.requests.find({ offerId: { $in: offerIds }, status: { $in: ["pending", "chosen"] } })
      .sort({ created: 1 }).toArray();
    const myReqs = await c.requests.find({ userId: me._id }).sort({ created: -1 }).limit(100).toArray();
    const theirOffers = await c.offers.find({ _id: { $in: myReqs.map((r) => r.offerId) } }).toArray();
    const offerById = Object.fromEntries(theirOffers.map((o) => [o._id, o]));
    const waits = await c.waits.find({ userId: me._id }).toArray();

    const ids = [...reqsOnMine.map((r) => r.userId), ...offers.map((o) => o.recipientId), ...theirOffers.map((o) => o.ownerId)];
    const [people, given] = await Promise.all([nicks(c, ids), givenCounts(c, reqsOnMine.map((r) => r.userId))]);
    const canTransfer = {};
    for (const o of [...offers, ...theirOffers]) canTransfer[o._id] = await transferable(o.matchId, o.section);

    return {
      user: { nick: me.nick, prefs: publicPrefs(me), devices: await c.push.countDocuments({ userId: me._id }) },
      waits: waits.map((w) => w.matchId),
      offers: offers.map((o) => ({
        id: o._id, matchId: o.matchId, ...seatOf(o), note: o.note || "", status: o.status,
        deadline: deadlineOf(o.matchStart),
        recipient: o.recipientId ? people[o.recipientId]?.nick || "—" : null,
        afm: o.status === "assigned" ? o.afm || null : null, // μόνο στον κάτοχο, μόνο πριν τη μεταβίβαση
        afmSent: Boolean(o.afm),
        transferable: canTransfer[o._id],
        priorityUntil: o.status === "open" && inPriority(o) ? o.priorityUntil : null,
        requests: o.status === "open"
          ? reqsOnMine.filter((r) => r.offerId === o._id && r.status === "pending").map((r) => ({
              id: r._id, nick: people[r.userId]?.nick || "—", given: given[r.userId] || 0, created: r.created,
              sameGate: people[r.userId] ? inGate(people[r.userId], o) : false,
            })).sort((a, b) => Number(b.sameGate) - Number(a.sameGate))
          : [],
      })),
      requests: myReqs.filter((r) => offerById[r.offerId]).map((r) => {
        const o = offerById[r.offerId];
        return {
          id: r._id, status: r.status, offerId: o._id, matchId: o.matchId, ...seatOf(o),
          deadline: deadlineOf(o.matchStart),
          owner: people[o.ownerId]?.nick || "—", offerStatus: o.recipientId === me._id ? o.status : (o.status === "open" ? "open" : "taken"),
          afmSent: o.recipientId === me._id ? Boolean(o.afm) : false,
          transferable: canTransfer[o._id],
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

  // POST {section, gates[], others, alerts}: οι θύρες μου και τι ειδοποιήσεις θέλω.
  async prefs(req, c, body) {
    const me = await currentUser(req, c);
    if (!SECTIONS.has(body.section)) fail(400, "Άγνωστο τμήμα.");
    const gates = (Array.isArray(body.gates) ? body.gates : [])
      .map((g) => str(g, 10, { label: "Θύρα" })).filter(Boolean);
    const uniq = [...new Map(gates.map((g) => [gateKey(g), g])).values()];
    if (uniq.length > MAX_GATES) fail(400, `Έως ${MAX_GATES} θύρες.`);
    await c.users.updateOne({ _id: me._id }, {
      $set: { [`prefs.${body.section}`]: { gates: uniq, others: body.others !== false, alerts: Boolean(body.alerts) } },
    });
    return { ok: true };
  },

  // POST {matchId, on}: «ειδοποίησέ με όταν βγει θέση σε αυτόν τον αγώνα».
  async wait(req, c, body) {
    const me = await currentUser(req, c);
    const _id = `${me._id}:${String(body.matchId || "")}`;
    if (body.on === false) {
      await c.waits.deleteOne({ _id });
      return { ok: true, waiting: false };
    }
    const m = await openMatch(body.matchId);
    if (!m) fail(400, "Ο αγώνας δεν δέχεται πια αιτήματα.");
    await c.waits.updateOne({ _id }, { $setOnInsert: { userId: me._id, matchId: m.nt, section: m.section, matchStart: new Date(m.start), created: new Date() } }, { upsert: true });
    return { ok: true, waiting: true };
  },

  // POST {subscription}: αυτή η συσκευή παίρνει ειδοποιήσεις για τις μεταβιβάσεις μου.
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
    if (!m) fail(400, `Ο αγώνας δεν δέχεται πια θέσεις (η μεταβίβαση γίνεται έως ${CUTOFF / HOUR} ώρες πριν).`);
    if (body.free !== true) fail(400, "Οι θέσεις δίνονται μόνο δωρεάν.");
    const gate = str(body.gate, 10, { required: true, label: "Θύρα" });
    const block = m.section === "basketball" ? str(body.block, 6, { label: "Τμήμα" }) : "";
    const row = str(body.row, 6, { label: "Σειρά" });
    const seat = str(body.seat, 6, { label: "Θέση" });
    const note = str(body.note, 140, { label: "Σημείωση" });
    const open = await c.offers.countDocuments({ ownerId: me._id, matchId: m.nt, status: { $in: ["open", "assigned", "transferred"] } });
    if (open >= MAX_OPEN_OFFERS_PER_MATCH) fail(429, `Έως ${MAX_OPEN_OFFERS_PER_MATCH} θέσεις ανά αγώνα.`);
    const now = new Date();
    // Προτεραιότητα θύρας: 2 ώρες, αλλά όχι πάνω από το μισό του χρόνου ως την προθεσμία.
    const left = deadlineOf(m.start).getTime() - now.getTime();
    const priorityUntil = new Date(now.getTime() + Math.min(PRIORITY_MS, Math.max(0, left / 2)));
    const doc = {
      _id: newId(), matchId: m.nt, section: m.section, matchStart: new Date(m.start), ownerId: me._id,
      gate, gateKey: gateKey(gate), block, row, seat, note, status: "open", priorityUntil, sent: {}, created: now, updated: now,
    };
    await c.offers.insertOne(doc);
    await announceOffer(c, doc, "priority");
    return { id: doc._id, priorityUntil };
  },

  // POST {offerId}: αποσύρω τη θέση μου (μόνο πριν γίνει η μεταβίβαση).
  async withdraw(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOneAndUpdate(
      { _id: String(body.offerId || ""), ownerId: me._id, status: { $in: ["open", "assigned"] } },
      { $set: { status: "withdrawn", updated: new Date() }, $unset: { afm: "" } },
    );
    if (!o) fail(409, "Η θέση δεν μπορεί να αποσυρθεί τώρα.");
    const affected = await c.requests.find({ offerId: o._id, status: { $in: ["pending", "chosen"] } }).toArray();
    await c.requests.updateMany({ offerId: o._id, status: { $in: ["pending", "chosen"] } }, { $set: { status: "declined", updated: new Date() } });
    const m = (await matches()).get(o.matchId);
    await notify(c, affected.map((r) => r.userId), {
      title: "Η θέση αποσύρθηκε", body: `${titleOf(m)} · ${seatLine(o)}. Δες αν υπάρχουν άλλες θέσεις.`, tag: `declined-${o._id}`,
    });
    return { ok: true };
  },

  // POST {offerId}: ζητάω μια θέση. Όσο κρατά η προτεραιότητα, μόνο όσοι είναι στην ίδια θύρα.
  async request(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOne({ _id: String(body.offerId || ""), status: "open" });
    if (!o) fail(409, "Η θέση δεν είναι πια διαθέσιμη.");
    if (o.ownerId === me._id) fail(400, "Δεν μπορείς να ζητήσεις τη δική σου θέση.");
    if (!(await openMatch(o.matchId))) fail(409, "Έληξε η προθεσμία για αυτόν τον αγώνα.");
    if (inPriority(o) && !inGate(me, o)) {
      fail(409, `Ως τις ${fmtTime(o.priorityUntil)} προτεραιότητα έχουν όσοι είναι στη Θύρα ${o.gate}.`);
    }
    const active = await c.requests.countDocuments({ userId: me._id, matchId: o.matchId, status: { $in: ["pending", "chosen"] } });
    if (active >= MAX_ACTIVE_REQUESTS_PER_MATCH) fail(429, `Έως ${MAX_ACTIVE_REQUESTS_PER_MATCH} ενεργά αιτήματα ανά αγώνα.`);
    const now = new Date();
    const prev = await c.requests.findOne({ offerId: o._id, userId: me._id });
    await c.requests.updateOne(
      { offerId: o._id, userId: me._id },
      { $set: { status: "pending", matchId: o.matchId, updated: now }, $setOnInsert: { _id: newId(), created: now } },
      { upsert: true },
    );
    if (prev?.status !== "pending") {
      await notify(c, [o.ownerId], {
        title: "Νέο αίτημα για τη θέση σου",
        body: `@${me.nick}${inGate(me, o) ? ` (Θύρα ${o.gate})` : ""} · ${seatLine(o)}`,
        tag: `req-${o._id}`,
      });
    }
    return { ok: true };
  },

  // POST {requestId}: ακυρώνω αίτημά μου που δεν έχει επιλεγεί ακόμα.
  async cancel(req, c, body) {
    const me = await currentUser(req, c);
    const r = await c.requests.findOneAndUpdate(
      { _id: String(body.requestId || ""), userId: me._id, status: "pending" },
      { $set: { status: "cancelled", updated: new Date() } },
    );
    if (!r) fail(409, "Το αίτημα δεν μπορεί να ακυρωθεί.");
    return { ok: true };
  },

  // POST {requestId}: ο κάτοχος διαλέγει παραλήπτη.
  async choose(req, c, body) {
    const me = await currentUser(req, c);
    const r = await c.requests.findOne({ _id: String(body.requestId || ""), status: "pending" });
    if (!r) fail(409, "Το αίτημα δεν ισχύει πια.");
    if (!(await chooseRequest(c, me._id, r))) fail(409, "Η θέση δεν είναι πια ανοιχτή.");
    return { ok: true };
  },

  // POST {offerId, afm}: ο παραλήπτης στέλνει τον ΑΦΜ του στον κάτοχο — μόνο όταν μπορεί να γίνει
  // η μεταβίβαση (ο αγώνας είναι ο επόμενος και πριν την προθεσμία).
  async afm(req, c, body) {
    const me = await currentUser(req, c);
    const afm = String(body.afm || "").replace(/\s/g, "");
    if (!validAfm(afm)) fail(400, "Ο ΑΦΜ δεν είναι έγκυρος.");
    const o = await c.offers.findOne({ _id: String(body.offerId || ""), recipientId: me._id, status: "assigned" });
    if (!o) fail(409, "Δεν μπορεί να σταλεί ΑΦΜ για αυτή τη θέση τώρα.");
    if (!(await transferable(o.matchId, o.section))) fail(409, "Η μεταβίβαση ανοίγει όταν τελειώσει ο προηγούμενος εντός έδρας αγώνας.");
    await c.offers.updateOne({ _id: o._id, status: "assigned" }, { $set: { afm, updated: new Date() } });
    await notify(c, [o.ownerId], {
      title: `Ο @${me.nick} έστειλε τον ΑΦΜ του`,
      body: `Κάνε τη μεταβίβαση στο Gov.gr Wallet ως ${fmtWhen(deadlineOf(o.matchStart))}.`,
      tag: `tx-${o._id}`,
    });
    return { ok: true };
  },

  // POST {offerId}: ο κάτοχος έκανε τη μεταβίβαση στο Gov.gr Wallet.
  async transferred(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOne({ _id: String(body.offerId || ""), ownerId: me._id, status: "assigned", afm: { $exists: true } });
    if (!o) fail(409, "Χρειάζεται πρώτα ο ΑΦΜ του παραλήπτη.");
    if (!(await transferable(o.matchId, o.section))) fail(409, "Η μεταβίβαση δεν είναι ανοιχτή για αυτόν τον αγώνα.");
    await c.offers.updateOne({ _id: o._id, status: "assigned" }, { $set: { status: "transferred", updated: new Date() } });
    await notify(c, [o.recipientId], {
      title: "Έγινε η μεταβίβαση!",
      body: "Θα σου έρθει email από το Gov.gr Wallet. Αποδέξου το εισιτήριο και πάτα «Το πήρα».",
      tag: `tx-${o._id}`,
    });
    return { ok: true };
  },

  // POST {offerId}: ο παραλήπτης το αποδέχτηκε στο Wallet. Ο ΑΦΜ σβήνεται.
  async received(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOneAndUpdate(
      { _id: String(body.offerId || ""), recipientId: me._id, status: "transferred" },
      { $set: { status: "received", updated: new Date() }, $unset: { afm: "" } },
    );
    if (!o) fail(409, "Ο κάτοχος δεν έχει δηλώσει ακόμα ότι έκανε τη μεταβίβαση.");
    await notify(c, [o.ownerId], { title: `Ο @${me.nick} πήρε το εισιτήριο`, body: "Ευχαριστούμε που έδωσες τη θέση σου!", tag: `tx-${o._id}` });
    return { ok: true };
  },

  // POST {offerId}: ο παραλήπτης δεν μπορεί τελικά (μόνο πριν τη μεταβίβαση). Η θέση ξανανοίγει.
  async backout(req, c, body) {
    const me = await currentUser(req, c);
    const now = new Date();
    const o = await c.offers.findOneAndUpdate(
      { _id: String(body.offerId || ""), recipientId: me._id, status: "assigned" },
      { $set: { status: "open", updated: now, "sent.transferOpen": false, "sent.deadline": false }, $unset: { afm: "", recipientId: "", requestId: "" } },
    );
    if (!o) fail(409, "Η μεταβίβαση έχει ήδη γίνει· ζήτα από τον κάτοχο να κάνει ανάκληση.");
    await c.requests.updateOne({ _id: o.requestId }, { $set: { status: "cancelled", updated: now } });
    await notify(c, [o.ownerId], { title: `Ο @${me.nick} δεν μπορεί τελικά`, body: `Η θέση σου (${seatLine(o)}) ξανάνοιξε για άλλα αιτήματα.`, tag: `req-${o._id}` });
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
    await housekeeping(c);
    const out = await fn(req, c, wantGet ? {} : await readBody(req));
    return send(res, 200, out);
  } catch (e) {
    if (e instanceof Fail) return send(res, e.status, { error: e.message });
    console.error("tx", a, e);
    // Μόνο ο κωδικός του σφάλματος (όχι το μήνυμα), για να φαίνεται τι έφταιξε στη δοκιμή.
    return send(res, 500, { error: "Κάτι πήγε στραβά. Δοκίμασε ξανά.", detail: String(e?.code || e?.name || "unknown").slice(0, 40) });
  }
}
