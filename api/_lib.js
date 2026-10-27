// Κοινά εργαλεία για τις λειτουργίες ειδοποιήσεων (τα αρχεία με _ δεν γίνονται endpoints).
//
// Αποθήκευση: MongoDB (MONGODB_URI, βάση MONGODB_DB ή «paokalendar»). Συλλογές:
//   settings   {_id: "vapid", publicKey, privateKey}: δημιουργούνται μία φορά, όταν χρειαστούν
//   subs       {_id, endpoint, keys, topics, updated}: μία εγγραφή ανά συσκευή
import crypto from "node:crypto";
import { MongoClient } from "mongodb";
import webpush from "web-push";

export const SITE = "https://paokalendar.vercel.app";

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

// Στέλνει σε μία συσκευή. Επιστρέφει "ok", "gone" (η συνδρομή δεν ισχύει πια) ή "error".
export async function pushTo(sub, payload, keys, ttl = 6 * 3600) {
  try {
    await webpush.sendNotification(
      { endpoint: sub.endpoint, keys: sub.keys },
      JSON.stringify(payload),
      {
        TTL: ttl,
        urgency: "high",
        topic: payload.tag ? payload.tag.replace(/[^A-Za-z0-9_-]/g, "").slice(0, 32) : undefined,
        vapidDetails: { subject: SITE, publicKey: keys.publicKey, privateKey: keys.privateKey },
      },
    );
    return "ok";
  } catch (e) {
    if (e.statusCode === 404 || e.statusCode === 410) return "gone";
    console.error("push", e.statusCode, e.body || e.message);
    return "error";
  }
}
