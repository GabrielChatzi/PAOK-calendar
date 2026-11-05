// Κοινά εργαλεία για τις λειτουργίες ειδοποιήσεων (τα αρχεία με _ δεν γίνονται endpoints).
//
// Αποθήκευση: MongoDB (MONGODB_URI, βάση MONGODB_DB ή «paokalendar»). Συλλογές:
//   settings   {_id: "vapid", publicKey, privateKey}: δημιουργούνται μία φορά, όταν χρειαστούν
//   subs       {_id, endpoint, keys, topics, updated}: μία εγγραφή ανά συσκευή
import crypto from "node:crypto";
import { MongoClient } from "mongodb";
import webpush from "web-push";

export const SITE = "https://paokalendar.gr";

// Θέματα: s:<τμήμα>:<είδος> ή m:<αγώνας>:<είδος>
export const TOPIC_RE = /^(s:[a-z-]{2,30}|m:[0-9a-f]{10}):(pre|time|live|result)$/;
const PUSH_HOSTS = [
  "fcm.googleapis.com", "web.push.apple.com", "push.services.mozilla.com",
  "notify.windows.com", "push.apple.com",
];

export function configured() {
  return Boolean(process.env.MONGODB_URI);
}

// Ένας client ανά instance: οι λειτουργίες του Vercel ξαναχρησιμοποιούνται μεταξύ αιτημάτων.
let dbPromise = null;
async function connect() {
  const client = await new MongoClient(process.env.MONGODB_URI, {
    maxPoolSize: 5,
    serverSelectionTimeoutMS: 8000,
  }).connect();
  const db = client.db(process.env.MONGODB_DB || "paokalendar");
  await db.collection("subs").createIndex({ topics: 1 });
  // Ειδοποιήσεις που πρέπει να φύγουν μία φορά (βλ. api/push.js «once»): σβήνονται μόνες τους σε 3 μέρες.
  await db.collection("sent").createIndex({ at: 1 }, { expireAfterSeconds: 3 * 86400 });
  return db;
}
export async function getDb() {
  dbPromise ??= connect().catch((e) => {
    dbPromise = null; // νέα προσπάθεια στο επόμενο αίτημα
    throw e;
  });
  return dbPromise;
}

export async function vapidKeys() {
  const settings = (await getDb()).collection("settings");
  let doc = await settings.findOne({ _id: "vapid" });
  if (!doc) {
    // upsert με $setOnInsert: αν δύο αιτήματα έρθουν μαζί, κρατιέται μόνο το πρώτο ζευγάρι.
    const keys = webpush.generateVAPIDKeys();
    try {
      await settings.updateOne({ _id: "vapid" }, { $setOnInsert: keys }, { upsert: true });
    } catch (e) {
      if (e?.code !== 11000) throw e;
    }
    doc = await settings.findOne({ _id: "vapid" });
  }
  return { publicKey: doc.publicKey, privateKey: doc.privateKey };
}

export async function subs() {
  return (await getDb()).collection("subs");
}

export function subId(endpoint) {
  return crypto.createHash("sha256").update(endpoint).digest("hex").slice(0, 32);
}

export function validSubscription(sub) {
  if (!sub || typeof sub.endpoint !== "string" || sub.endpoint.length > 1000) return false;
  let url;
  try { url = new URL(sub.endpoint); } catch { return false; }
  if (url.protocol !== "https:") return false;
  if (!PUSH_HOSTS.some((h) => url.hostname === h || url.hostname.endsWith("." + h))) return false;
  const k = sub.keys || {};
  return typeof k.p256dh === "string" && typeof k.auth === "string" && k.p256dh.length < 200 && k.auth.length < 100;
}

export function send(res, status, body) {
  res.setHeader("Cache-Control", "no-store");
  res.status(status).json(body);
}

export async function readBody(req) {
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string") {
    try { return JSON.parse(req.body); } catch { return {}; }
  }
  return {};
}

// Τα σφάλματα της τελευταίας αποστολής, για να φαίνονται στα logs του GitHub (notify.py).
export const lastErrors = [];

// Στέλνει σε μία συσκευή. Επιστρέφει "ok", "gone" (η συνδρομή δεν ισχύει πια) ή "error".
// Σε προσωρινό σφάλμα της υπηρεσίας (429, 5xx, δίκτυο) ξαναδοκιμάζει μία φορά μετά από 1''.
export async function pushTo(sub, payload, keys, ttl = 6 * 3600, retry = true) {
  try {
    await webpush.sendNotification(
      { endpoint: sub.endpoint, keys: sub.keys },
      JSON.stringify(payload),
      {
        TTL: ttl,
        urgency: "high",
        // Topic: η υπηρεσία κρατά μόνο την τελευταία αναμονή με το ίδιο topic. Η Apple το θέλει έγκυρο
        // base64url (μήκος όχι 4ν+1: το «<id>-result» απορριπτόταν με BadWebPushTopic), οπότε στέλνουμε
        // ένα hash του tag σε 32 χαρακτήρες.
        topic: payload.tag ? crypto.createHash("sha256").update(payload.tag).digest("base64url").slice(0, 32) : undefined,
        vapidDetails: { subject: SITE, publicKey: keys.publicKey, privateKey: keys.privateKey },
      },
    );
    return "ok";
  } catch (e) {
    if (e.statusCode === 404 || e.statusCode === 410) return "gone";
    if (retry && (!e.statusCode || e.statusCode === 429 || e.statusCode >= 500)) {
      await new Promise((r) => setTimeout(r, 1000));
      return pushTo(sub, payload, keys, ttl, false);
    }
    console.error("push", e.statusCode, e.body || e.message);
    lastErrors.push(`${new URL(sub.endpoint).host} ${e.statusCode || ""} ${String(e.body || e.message).slice(0, 120)}`.trim());
    return "error";
  }
}

// Αποστολή σε όσες συσκευές έχουν κάποιο από τα θέματα (μία φορά στην καθεμία). Την καλούν το
// /api/push (GitHub Actions) και το /api/admin (καταχωρίσεις του διαχειριστή).
//   once: κλειδί· όσες συσκευές πήραν ήδη ειδοποίηση με αυτό το κλειδί παραλείπονται.
export async function deliver(topics, payload, opts = {}) {
  const col = await subs();
  let targets = await col.find({ topics: { $in: topics }, gone: { $ne: true } }, { projection: { endpoint: 1, keys: 1 } }).toArray();
  // once: κλειδί για ειδοποίηση που πρέπει να φτάσει μία φορά σε κάθε συσκευή, όποιος κι αν τη στείλει
  // (π.χ. το τελικό έρχεται και από το live και από την ενημέρωση του προγράμματος, σε άλλα θέματα).
  // Οι συσκευές που την πήραν ήδη παραλείπονται.
  const once = opts.once ? String(opts.once).slice(0, 80) : "";
  const sentCol = once ? (await getDb()).collection("sent") : null;
  let skipped = 0;
  if (sentCol) {
    const prior = await sentCol.findOne({ _id: once }, { projection: { subs: 1 } });
    const had = new Set(prior?.subs || []);
    skipped = targets.filter((s) => had.has(s._id)).length;
    targets = targets.filter((s) => !had.has(s._id));
  }
  const keys = await vapidKeys();
  const ttl = topics.some((t) => t.endsWith(":live")) ? 2 * 3600 : 12 * 3600;
  lastErrors.length = 0;
  const results = await Promise.all(targets.map((s) => pushTo(s, payload, keys, ttl)));
  const gone = targets.filter((_, i) => results[i] === "gone").map((s) => s._id);
  // Συνδρομές που ακύρωσε η συσκευή (404/410): δεν σβήνονται, σημειώνονται, ώστε η εφαρμογή να το
  // καταλάβει στον επόμενο έλεγχο και να ζητήσει να ξαναενεργοποιηθούν οι ειδοποιήσεις.
  if (gone.length) await col.updateMany({ _id: { $in: gone } }, { $set: { gone: true, goneAt: new Date() } });
  const count = (x) => results.filter((r) => r === x).length;
  const reached = targets.filter((_, i) => results[i] === "ok").map((s) => s._id);
  if (sentCol && reached.length) {
    await sentCol.updateOne({ _id: once }, { $addToSet: { subs: { $each: reached } }, $set: { at: new Date() } }, { upsert: true });
  }
  return { matched: targets.length, sent: count("ok"), removed: count("gone"), failed: count("error"),
    skipped, errors: lastErrors.slice(0, 5) };
}
