// Κατάσταση των ειδοποιήσεων: αν είναι συνδεδεμένη η βάση και πόσες συσκευές είναι γραμμένες,
// ανά υπηρεσία (Apple, Google, Mozilla, Microsoft). Με ?topic=<θέμα> μετρά μόνο όσες το έχουν.
// Με ?selftest=1 δοκιμάζει όλη τη διαδρομή χωρίς να στείλει τίποτα (βλ. selftest), για τον watchdog.
import webpush from "web-push";
import { TOPIC_RE, configured, getDb, send, subId, subs, validSubscription, vapidKeys } from "./_lib.js";

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

function service(endpoint) {
  const host = new URL(endpoint).hostname;
  return host.includes("apple") ? "apple" : host.includes("google") ? "google"
    : host.includes("mozilla") ? "mozilla" : host.includes("windows") ? "microsoft" : "other";
}

export default async function handler(req, res) {
  if (!configured()) return send(res, 200, { configured: false });
  if (req.query?.selftest) return send(res, 200, await selftest());
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
