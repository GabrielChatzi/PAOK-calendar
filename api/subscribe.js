// Αποθηκεύει (POST) ή σβήνει (DELETE) τη συνδρομή μιας συσκευής και τα θέματα που διάλεξε.
import { TOPIC_RE, configured, readBody, send, subId, subs, validSubscription } from "./_lib.js";

export default async function handler(req, res) {
  if (!configured()) return send(res, 503, { error: "Οι ειδοποιήσεις δεν έχουν ρυθμιστεί ακόμα." });
  const body = await readBody(req);
  const sub = body.subscription;
  if (!validSubscription(sub)) return send(res, 400, { error: "Μη έγκυρη συνδρομή." });
  const id = subId(sub.endpoint);
  const col = await subs();

  if (req.method === "DELETE") {
    await col.deleteOne({ _id: id });
    return send(res, 200, { ok: true });
  }
  if (req.method !== "POST") return send(res, 405, { error: "Μόνο POST ή DELETE." });

  const topics = Array.isArray(body.topics)
    ? [...new Set(body.topics.filter((t) => typeof t === "string" && TOPIC_RE.test(t)))].slice(0, 400)
    : [];
  await col.updateOne({ _id: id }, {
    $set: {
      endpoint: sub.endpoint,
      keys: { p256dh: sub.keys.p256dh, auth: sub.keys.auth },
      topics,
      updated: new Date(),
    },
  }, { upsert: true });
  return send(res, 200, { ok: true, topics: topics.length });
}
