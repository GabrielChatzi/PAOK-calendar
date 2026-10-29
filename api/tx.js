// Μεταβιβάσεις εισιτηρίων διαρκείας (δοκιμαστική έκδοση): κάτοχοι που δεν πάνε σε έναν εντός έδρας
// αγώνα δίνουν δωρεάν τη θέση τους και άλλοι φίλαθλοι τη ζητούν. Η ίδια η μεταβίβαση γίνεται στο
// Gov.gr Wallet· εδώ γίνεται μόνο η συνεννόηση.
//
// Ένα endpoint, ενέργεια με ?a=<ενέργεια>. Ταυτότητα: ψευδώνυμο και κλειδί συσκευής
// (Authorization: Bearer <token>)· στη βάση κρατιέται μόνο το hash του κλειδιού.
//
// Συλλογές MongoDB (ίδια βάση με τις ειδοποιήσεις):
//   tx_users     {_id, nick, nickLower, tokenHash, created}
//   tx_offers    {_id, matchId, section, matchStart, ownerId, gate, row, seat, note, status,
//                 recipientId, requestId, afm, created, updated}
//                status: open → assigned → transferred → received → closed (ή withdrawn / expired)
//   tx_requests  {_id, offerId, matchId, userId, status, created, updated}
//                status: pending → chosen | declined | cancelled
//
// Ο ΑΦΜ του παραλήπτη τον βλέπει μόνο ο κάτοχος της θέσης, και σβήνεται μόλις ο παραλήπτης
// επιβεβαιώσει ότι πήρε το εισιτήριο, αν ακυρωθεί η μεταβίβαση ή αν περάσει ο αγώνας.
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { SITE, configured, getDb, readBody, send } from "./_lib.js";

const SECTIONS = new Set(["football", "basketball"]);
const MAX_OPEN_OFFERS_PER_MATCH = 4;
const MAX_ACTIVE_REQUESTS_PER_MATCH = 3;
const DAY = 24 * 3600 * 1000;

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
async function upcomingMatch(id) {
  const m = (await matches()).get(String(id || ""));
  if (!m) return null;
  // Δεκτός μέχρι να αρχίσει ο αγώνας.
  return new Date(m.start).getTime() > Date.now() ? m : null;
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

// Έλεγχος ΑΦΜ με το ψηφίο ελέγχου.
export function validAfm(afm) {
  if (!/^\d{9}$/.test(afm) || afm === "000000000") return false;
  let sum = 0;
  for (let i = 0; i < 8; i++) sum += Number(afm[i]) * 2 ** (8 - i);
  return (sum % 11) % 10 === Number(afm[8]);
}

let indexesReady = null;
async function cols() {
  const db = await getDb();
  const c = {
    users: db.collection("tx_users"),
    offers: db.collection("tx_offers"),
    requests: db.collection("tx_requests"),
  };
  indexesReady ??= Promise.all([
    c.users.createIndex({ nickLower: 1 }, { unique: true }),
    c.users.createIndex({ tokenHash: 1 }, { unique: true }),
    c.offers.createIndex({ matchId: 1, status: 1 }),
    c.offers.createIndex({ ownerId: 1 }),
    c.offers.createIndex({ recipientId: 1 }),
    c.requests.createIndex({ offerId: 1, userId: 1 }, { unique: true }),
    c.requests.createIndex({ userId: 1 }),
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

// Σβήνει ΑΦΜ και κλείνει ανοιχτές θέσεις για αγώνες που άρχισαν.
async function housekeeping(c) {
  const now = new Date();
  await c.offers.updateMany({ matchStart: { $lt: now }, afm: { $exists: true } }, { $unset: { afm: "" } });
  await c.offers.updateMany({ matchStart: { $lt: now }, status: "open" }, { $set: { status: "expired", updated: now } });
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

const seatOf = (o) => ({ gate: o.gate, row: o.row || "", seat: o.seat || "" });

// ---------- Ενέργειες ----------
const actions = {
  // GET: σύνοψη ανά αγώνα (ανοιχτές θέσεις, πόσοι ζητούν). Δημόσιο.
  async summary(req, c) {
    const now = new Date();
    const open = await c.offers.aggregate([
      { $match: { status: "open", matchStart: { $gt: now } } },
      { $group: { _id: "$matchId", offers: { $sum: 1 } } },
    ]).toArray();
    const reqs = await c.requests.aggregate([
      { $match: { status: "pending" } },
      { $group: { _id: { m: "$matchId", u: "$userId" } } },
      { $group: { _id: "$_id.m", users: { $sum: 1 } } },
    ]).toArray();
    const out = {};
    for (const r of open) out[r._id] = { offers: r.offers, seekers: 0 };
    for (const r of reqs) (out[r._id] ??= { offers: 0, seekers: 0 }).seekers = r.users;
    return { matches: out };
  },

  // GET ?id=<αγώνας>: οι ανοιχτές θέσεις ενός αγώνα και τι έχω ζητήσει εγώ.
  async match(req, c) {
    const id = String(req.query?.id || "");
    if (!(await matches()).has(id)) fail(404, "Ο αγώνας δεν βρέθηκε.");
    const me = await currentUser(req, c, { required: false });
    const offers = await c.offers.find({ matchId: id, status: "open" }).sort({ created: 1 }).toArray();
    const owners = offers.map((o) => o.ownerId);
    const [names, given] = await Promise.all([nicks(c, owners), givenCounts(c, owners)]);
    let mine = {};
    if (me) {
      const rs = await c.requests.find({ matchId: id, userId: me._id, status: { $in: ["pending", "chosen"] } }).toArray();
      mine = Object.fromEntries(rs.map((r) => [r.offerId, { requestId: r._id, status: r.status }]));
    }
    return {
      offers: offers.map((o) => ({
        id: o._id, ...seatOf(o), note: o.note || "", created: o.created,
        owner: names[o.ownerId] || "—", given: given[o.ownerId] || 0,
        isMine: me ? o.ownerId === me._id : false,
        myRequest: mine[o._id] || null,
      })),
    };
  },

  // GET: όλα όσα με αφορούν, ως κάτοχο και ως παραλήπτη.
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

    const people = [...reqsOnMine.map((r) => r.userId), ...offers.map((o) => o.recipientId), ...theirOffers.map((o) => o.ownerId)];
    const [names, given] = await Promise.all([nicks(c, people), givenCounts(c, reqsOnMine.map((r) => r.userId))]);

    return {
      user: { nick: me.nick },
      offers: offers.map((o) => ({
        id: o._id, matchId: o.matchId, ...seatOf(o), note: o.note || "", status: o.status,
        recipient: o.recipientId ? names[o.recipientId] || "—" : null,
        afm: o.status === "assigned" ? o.afm || null : null, // μόνο στον κάτοχο, μόνο πριν τη μεταβίβαση
        afmSent: Boolean(o.afm),
        requests: o.status === "open"
          ? reqsOnMine.filter((r) => r.offerId === o._id && r.status === "pending").map((r) => ({
              id: r._id, nick: names[r.userId] || "—", given: given[r.userId] || 0, created: r.created,
            }))
          : [],
      })),
      requests: myReqs.filter((r) => offerById[r.offerId]).map((r) => {
        const o = offerById[r.offerId];
        return {
          id: r._id, status: r.status, offerId: o._id, matchId: o.matchId, ...seatOf(o),
          owner: names[o.ownerId] || "—", offerStatus: o.recipientId === me._id ? o.status : (o.status === "open" ? "open" : "taken"),
          afmSent: o.recipientId === me._id ? Boolean(o.afm) : false,
        };
      }),
    };
  },

  // POST {nick}: νέο ψευδώνυμο σε αυτή τη συσκευή.
  async register(req, c, body) {
    const nick = str(body.nick, 20, { required: true, label: "Ψευδώνυμο" });
    if (!/^[\p{L}\p{N}._-]{3,20}$/u.test(nick)) fail(400, "Ψευδώνυμο: 3–20 γράμματα, αριθμοί, τελεία, παύλα ή κάτω παύλα.");
    const token = crypto.randomBytes(24).toString("base64url");
    try {
      await c.users.insertOne({ _id: newId(), nick, nickLower: nick.toLocaleLowerCase("el"), tokenHash: hash(token), created: new Date() });
    } catch (e) {
      if (e?.code === 11000) fail(409, "Το ψευδώνυμο το έχει ήδη κάποιος άλλος.");
      throw e;
    }
    return { token, nick };
  },

  // POST {matchId, gate, row, seat, note, free}: δίνω τη θέση μου.
  async offer(req, c, body) {
    const me = await currentUser(req, c);
    const m = await upcomingMatch(body.matchId);
    if (!m) fail(400, "Ο αγώνας δεν είναι επερχόμενος εντός έδρας ποδοσφαίρου ή μπάσκετ.");
    if (body.free !== true) fail(400, "Οι θέσεις δίνονται μόνο δωρεάν.");
    const gate = str(body.gate, 10, { required: true, label: "Θύρα" });
    const row = str(body.row, 6, { label: "Σειρά" });
    const seat = str(body.seat, 6, { label: "Θέση" });
    const note = str(body.note, 140, { label: "Σημείωση" });
    const open = await c.offers.countDocuments({ ownerId: me._id, matchId: m.nt, status: { $in: ["open", "assigned", "transferred"] } });
    if (open >= MAX_OPEN_OFFERS_PER_MATCH) fail(429, `Έως ${MAX_OPEN_OFFERS_PER_MATCH} θέσεις ανά αγώνα.`);
    const now = new Date();
    const doc = {
      _id: newId(), matchId: m.nt, section: m.section, matchStart: new Date(m.start), ownerId: me._id,
      gate, row, seat, note, status: "open", created: now, updated: now,
    };
    await c.offers.insertOne(doc);
    return { id: doc._id };
  },

  // POST {offerId}: αποσύρω τη θέση μου (μόνο πριν γίνει η μεταβίβαση).
  async withdraw(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOneAndUpdate(
      { _id: String(body.offerId || ""), ownerId: me._id, status: { $in: ["open", "assigned"] } },
      { $set: { status: "withdrawn", updated: new Date() }, $unset: { afm: "" } },
    );
    if (!o) fail(409, "Η θέση δεν μπορεί να αποσυρθεί τώρα.");
    await c.requests.updateMany({ offerId: o._id, status: { $in: ["pending", "chosen"] } }, { $set: { status: "declined", updated: new Date() } });
    return { ok: true };
  },

  // POST {offerId}: ζητάω μια θέση.
  async request(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOne({ _id: String(body.offerId || ""), status: "open" });
    if (!o) fail(409, "Η θέση δεν είναι πια διαθέσιμη.");
    if (o.ownerId === me._id) fail(400, "Δεν μπορείς να ζητήσεις τη δική σου θέση.");
    if (o.matchStart < new Date()) fail(409, "Ο αγώνας έχει αρχίσει.");
    const active = await c.requests.countDocuments({ userId: me._id, matchId: o.matchId, status: { $in: ["pending", "chosen"] } });
    if (active >= MAX_ACTIVE_REQUESTS_PER_MATCH) fail(429, `Έως ${MAX_ACTIVE_REQUESTS_PER_MATCH} ενεργά αιτήματα ανά αγώνα.`);
    const now = new Date();
    await c.requests.updateOne(
      { offerId: o._id, userId: me._id },
      { $set: { status: "pending", matchId: o.matchId, updated: now }, $setOnInsert: { _id: newId(), created: now } },
      { upsert: true },
    );
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
    const now = new Date();
    const o = await c.offers.findOneAndUpdate(
      { _id: r.offerId, ownerId: me._id, status: "open" },
      { $set: { status: "assigned", recipientId: r.userId, requestId: r._id, updated: now } },
    );
    if (!o) fail(409, "Η θέση δεν είναι πια ανοιχτή.");
    await c.requests.updateOne({ _id: r._id }, { $set: { status: "chosen", updated: now } });
    await c.requests.updateMany({ offerId: o._id, _id: { $ne: r._id }, status: "pending" }, { $set: { status: "declined", updated: now } });
    return { ok: true };
  },

  // POST {offerId, afm}: ο παραλήπτης στέλνει τον ΑΦΜ του στον κάτοχο.
  async afm(req, c, body) {
    const me = await currentUser(req, c);
    const afm = String(body.afm || "").replace(/\s/g, "");
    if (!validAfm(afm)) fail(400, "Ο ΑΦΜ δεν είναι έγκυρος.");
    const o = await c.offers.findOneAndUpdate(
      { _id: String(body.offerId || ""), recipientId: me._id, status: "assigned", matchStart: { $gt: new Date() } },
      { $set: { afm, updated: new Date() } },
    );
    if (!o) fail(409, "Δεν μπορεί να σταλεί ΑΦΜ για αυτή τη θέση τώρα.");
    return { ok: true };
  },

  // POST {offerId}: ο κάτοχος έκανε τη μεταβίβαση στο Gov.gr Wallet.
  async transferred(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOneAndUpdate(
      { _id: String(body.offerId || ""), ownerId: me._id, status: "assigned", afm: { $exists: true } },
      { $set: { status: "transferred", updated: new Date() } },
    );
    if (!o) fail(409, "Χρειάζεται πρώτα ο ΑΦΜ του παραλήπτη.");
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
    return { ok: true };
  },

  // POST {offerId}: ο παραλήπτης δεν μπορεί τελικά (μόνο πριν τη μεταβίβαση). Η θέση ξανανοίγει.
  async backout(req, c, body) {
    const me = await currentUser(req, c);
    const now = new Date();
    const o = await c.offers.findOneAndUpdate(
      { _id: String(body.offerId || ""), recipientId: me._id, status: "assigned" },
      { $set: { status: "open", updated: now }, $unset: { afm: "", recipientId: "", requestId: "" } },
    );
    if (!o) fail(409, "Η μεταβίβαση έχει ήδη γίνει· ζήτα από τον κάτοχο να κάνει ανάκληση.");
    await c.requests.updateOne({ _id: o.requestId }, { $set: { status: "cancelled", updated: now } });
    return { ok: true };
  },

  // POST {offerId}: ο κάτοχος έκανε ανάκληση στο Wallet. Τέλος.
  async revoked(req, c, body) {
    const me = await currentUser(req, c);
    const o = await c.offers.findOneAndUpdate(
      { _id: String(body.offerId || ""), ownerId: me._id, status: { $in: ["transferred", "received"] } },
      { $set: { status: "closed", updated: new Date() }, $unset: { afm: "" } },
    );
    if (!o) fail(409, "Δεν υπάρχει μεταβίβαση για ανάκληση.");
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
