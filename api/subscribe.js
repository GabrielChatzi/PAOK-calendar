// Η συνδρομή μιας συσκευής για ειδοποιήσεις:
//   POST {subscription, topics}            αποθηκεύει τα θέματα που διάλεξε (απαντά με όσα κράτησε)
//   POST {subscription, action: "check"}   τι έχει αποθηκευτεί για αυτή τη συσκευή (για έλεγχο από τη σελίδα)
//   POST {subscription, action: "test"}    στέλνει μία δοκιμαστική ειδοποίηση μόνο σε αυτή τη συσκευή
//   DELETE {subscription}                  τη σβήνει
import { TOPIC_RE, configured, pushTo, readBody, send, subId, subs, validSubscription, vapidKeys } from "./_lib.js";

const TEST_EVERY = 30 * 1000;  // μία δοκιμαστική ανά 30'' ανά συσκευή

export default async function handler(req, res) {
  if (!configured()) return send(res, 503, { error: "Οι ειδοποιήσεις δεν έχουν ρυθμιστεί ακόμα." });
  try {
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

    if (body.action === "check") {
      const doc = await col.findOne({ _id: id }, { projection: { topics: 1, updated: 1, gone: 1 } });
      return send(res, 200, { ok: true, found: !!doc, gone: !!doc?.gone, topics: doc ? doc.topics || [] : [], updated: doc?.updated || null });
    }

    if (body.action === "test") {
      const doc = await col.findOne({ _id: id }, { projection: { endpoint: 1, keys: 1, lastTest: 1 } });
      if (!doc) return send(res, 404, { error: "Η συσκευή δεν είναι γραμμένη στον server." });
      if (doc.lastTest && Date.now() - new Date(doc.lastTest).getTime() < TEST_EVERY) {
        return send(res, 429, { error: "Περίμενε λίγα δευτερόλεπτα και ξαναδοκίμασε." });
      }
      await col.updateOne({ _id: id }, { $set: { lastTest: new Date() } });
      const result = await pushTo(doc, {
        title: "🔔 Δοκιμαστική ειδοποίηση",
        body: "Οι ειδοποιήσεις του PAOKalendar φτάνουν σε αυτή τη συσκευή.",
        url: "/#/notifications", tag: "test",
      }, await vapidKeys(), 600);
      if (result === "gone") await col.updateOne({ _id: id }, { $set: { gone: true, goneAt: new Date() } });
      return send(res, result === "ok" ? 200 : 502, { ok: result === "ok", result });
    }

    const topics = Array.isArray(body.topics)
      ? [...new Set(body.topics.filter((t) => typeof t === "string" && TOPIC_RE.test(t)))].slice(0, 400)
      : [];
    await col.updateOne({ _id: id }, {
      $set: {
        endpoint: sub.endpoint,
        keys: { p256dh: sub.keys.p256dh, auth: sub.keys.auth },
        topics,
        updated: new Date(),
        gone: false,
      },
    }, { upsert: true });
    return send(res, 200, { ok: true, topics: topics.length, saved: topics });
  } catch (e) {
    console.error("subscribe", e);
    return send(res, 500, { error: "Σφάλμα του server.", detail: String(e.message || e).slice(0, 200) });
  }
}
