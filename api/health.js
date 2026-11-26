// Κατάσταση των ειδοποιήσεων: αν είναι συνδεδεμένη η βάση και πόσες συσκευές είναι γραμμένες,
// ανά υπηρεσία (Apple, Google, Mozilla, Microsoft). Με ?topic=<θέμα> μετρά μόνο όσες το έχουν.
// Με ?selftest=1 δοκιμάζει όλη τη διαδρομή χωρίς να στείλει τίποτα (βλ. selftest), για τον watchdog.
//
// POST {action: "ping", device, platform}: η εγκατεστημένη εφαρμογή (αρχική οθόνη) λέει «είμαι εδώ», το
// πολύ μία φορά τη μέρα. device: τυχαίο ανώνυμο αναγνωριστικό της συσκευής (local storage), platform:
// ios | android | desktop | other. Συλλογή «devices» {_id: device, platform, first, last}· σβήνεται
// μόνη της 180 ημέρες μετά το τελευταίο άνοιγμα. Μετρά εγκαταστάσεις, τίποτα άλλο (βλ. Απόρρητο).
// Προαιρετικά: usage {καρτέλα: φορές} από την προηγούμενη μέρα και follow {set, n}: πόσα ακολουθεί η συσκευή.
// Η χρήση μπαίνει μόνο ως άθροισμα ανά μέρα (συλλογή «usage», _id ημερομηνία), όχι ανά συσκευή.
import webpush from "web-push";
import { TOPIC_RE, configured, getDb, readBody, send, subId, subs, validSubscription, vapidKeys } from "./_lib.js";

const PLATFORMS = ["ios", "android", "desktop", "other"];
export const USAGE_TABS = ["home", "program", "sports", "history", "profile"];
let devicesIndexed = false;

export function parsePing(body) {
  const device = String(body?.device || "");
  if (!/^[0-9a-f]{16,32}$/.test(device)) return null;
  const platform = PLATFORMS.includes(body?.platform) ? body.platform : "other";
  const out = { device, platform };
  if (body?.usage && typeof body.usage === "object") {
    const usage = {};
    for (const t of USAGE_TABS) {
      const n = Math.floor(Number(body.usage[t]));
      if (n > 0) usage[t] = Math.min(n, 999);
    }
    if (Object.keys(usage).length) out.usage = usage;
  }
  if (body?.follow && typeof body.follow === "object") {
    out.follow = { set: body.follow.set === true, n: Math.max(0, Math.min(200, Math.floor(Number(body.follow.n) || 0))) };
  }
  return out;
}

async function ping(req, res) {
  let body;
  try { body = await readBody(req); } catch (e) { return send(res, 400, { error: "Λάθος αίτημα." }); }
  const p = parsePing(body);
  if (!p) return send(res, 400, { error: "Λάθος αίτημα." });
  const col = (await getDb()).collection("devices");
  if (!devicesIndexed) {
    await col.createIndex({ last: 1 }, { expireAfterSeconds: 180 * 86400 }).catch(() => {});
    devicesIndexed = true;
  }
  const now = new Date();
  const set = { platform: p.platform, last: now };
  if (p.follow) { set.followSet = p.follow.set; set.follows = p.follow.n; }
  await col.updateOne({ _id: p.device }, { $set: set, $setOnInsert: { first: now } }, { upsert: true });
  if (p.usage) {
    const inc = { devices: 1 };
    for (const [t, n] of Object.entries(p.usage)) inc["tabs." + t] = n;
    await (await getDb()).collection("usage").updateOne({ _id: now.toISOString().slice(0, 10) },
      { $inc: inc, $set: { at: now } }, { upsert: true }).catch(() => {});
  }
  return send(res, 200, { ok: true });
}

// Ό,τι χρησιμοποιούν η εγγραφή και η αποστολή: αναγνωριστικό συσκευής, έλεγχος συνδρομής, εγγραφή και
// σβήσιμο στη βάση, κλειδιά VAPID και κρυπτογράφηση μιας ειδοποίησης (χωρίς να σταλεί).
async function selftest() {
  const checks = {};
  async function step(name, fn) {
    try { await fn(); checks[name] = "ok"; } catch (e) { checks[name] = String(e.message || e).slice(0, 160); }
  }
  const sample = webpush.generateVAPIDKeys();  // ένα έγκυρο δημόσιο κλειδί P-256 για «συσκευή»
  const sub = { endpoint: "https://fcm.googleapis.com/fcm/send/paokalendar-selftest",
    keys: { p256dh: sample.publicKey, auth: "c2VsZnRlc3Qtc2VsZnRlcw" } };
  await step("subId", () => { if (!/^[0-9a-f]{32}$/.test(subId(sub.endpoint))) throw new Error("λάθος μορφή"); });
  await step("validSubscription", () => { if (!validSubscription(sub)) throw new Error("απορρίφθηκε"); });
  await step("db", async () => {
    const col = (await getDb()).collection("selftest");
    await col.updateOne({ _id: "selftest" }, { $set: { at: new Date() } }, { upsert: true });
    await col.deleteOne({ _id: "selftest" });
  });
  await step("push", async () => {
    const keys = await vapidKeys();
    webpush.generateRequestDetails(sub, JSON.stringify({ title: "selftest", tag: "x-result" }), {
      TTL: 60, topic: "selftest",
      vapidDetails: { subject: "https://paokalendar.gr", publicKey: keys.publicKey, privateKey: keys.privateKey },
    });
  });
  return { ok: Object.values(checks).every((v) => v === "ok"), checks };
}

export function service(endpoint) {
  const host = new URL(endpoint).hostname;
  return host.includes("apple") ? "apple" : host.includes("google") ? "google"
    : host.includes("mozilla") ? "mozilla" : host.includes("windows") ? "microsoft" : "other";
}

export default async function handler(req, res) {
  if (!configured()) return send(res, 200, { configured: false });
  if (req.query?.selftest) return send(res, 200, await selftest());
  if (req.method === "POST") {
    try { return await ping(req, res); } catch (e) { return send(res, 500, { error: "Δεν αποθηκεύτηκε." }); }
  }
  try {
    const col = await subs();
    const topic = String(req.query?.topic || "");
    const filter = TOPIC_RE.test(topic) ? { topics: topic } : {};
    const docs = await col.find(filter, { projection: { endpoint: 1 } }).toArray();
    const byService = {};
    docs.forEach((d) => { const s = service(d.endpoint); byService[s] = (byService[s] || 0) + 1; });
    return send(res, 200, { configured: true, db: true, subscribers: await col.estimatedDocumentCount(),
      ...(filter.topics ? { topic, matching: docs.length } : {}), byService });
  } catch (e) {
    return send(res, 200, { configured: true, db: false, error: e.message });
  }
}
