// Η συνδρομή μιας συσκευής για ειδοποιήσεις:
//   POST {subscription, topics}            αποθηκεύει τα θέματα που διάλεξε (απαντά με όσα κράτησε)
//   POST {subscription, action: "check"}   τι έχει αποθηκευτεί για αυτή τη συσκευή (για έλεγχο από τη σελίδα)
//   POST {subscription, action: "test"}    στέλνει μία δοκιμαστική ειδοποίηση μόνο σε αυτή τη συσκευή
//   DELETE {subscription}                  τη σβήνει
import crypto from "node:crypto";
import { TOPIC_RE, configured, getDb, pushTo, readBody, send, subId, subs, validSubscription, vapidKeys } from "./_lib.js";

const TEST_EVERY = 30 * 1000;  // μία δοκιμαστική ανά 30'' ανά συσκευή

export default async function handler(req, res) {
  if (!configured()) return send(res, 503, { error: "Οι ειδοποιήσεις δεν έχουν ρυθμιστεί ακόμα." });
  try {
    const body = await readBody(req);
    // Μεταφορά από την παλιά διεύθυνση (paokalendar.vercel.app) στο paokalendar.gr: η άδεια για ειδοποιήσεις
    // είναι ανά διεύθυνση, οπότε η νέα εφαρμογή κάνει νέα συνδρομή· παίρνει τις επιλογές της παλιάς με έναν
    // κωδικό και η παλιά σβήνεται, ώστε να μην έρχονται διπλές ειδοποιήσεις.
    if (req.method === "POST" && /^move-(info|in)$/.test(body.action || "")) {
      const moves = (await getDb()).collection("moves");
      const code = String(body.code || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
      const mv = code.length === 6 ? await moves.findOne({ _id: code }) : null;
      if (!mv) return send(res, 404, { error: "Ο κωδικός μεταφοράς δεν βρέθηκε ή έληξε." });
      if (body.action === "move-info") return send(res, 200, { ok: true, count: mv.topics.length, prefs: mv.prefs || {} });
      const sub = body.subscription;
      if (!validSubscription(sub)) return send(res, 400, { error: "Μη έγκυρη συνδρομή." });
      const col = await subs();
      await col.updateOne({ _id: subId(sub.endpoint) }, {
        $set: { endpoint: sub.endpoint, keys: { p256dh: sub.keys.p256dh, auth: sub.keys.auth },
          topics: mv.topics, updated: new Date(), gone: false, movedFrom: mv.oldId },
      }, { upsert: true });
      if (mv.oldId !== subId(sub.endpoint)) await col.deleteOne({ _id: mv.oldId });
      await moves.updateOne({ _id: code }, { $set: { usedAt: new Date() } });
      return send(res, 200, { ok: true, topics: mv.topics, prefs: mv.prefs || {} });
    }
    const sub = body.subscription;
    if (!validSubscription(sub)) return send(res, 400, { error: "Μη έγκυρη συνδρομή." });
    const id = subId(sub.endpoint);
    const col = await subs();

    if (req.method === "DELETE") {
      await col.deleteOne({ _id: id });
      return send(res, 200, { ok: true });
    }
    if (req.method !== "POST") return send(res, 405, { error: "Μόνο POST ή DELETE." });

    if (body.action === "move-out") {
      const doc = await col.findOne({ _id: id }, { projection: { topics: 1 } });
      const moves = (await getDb()).collection("moves");
      const prefs = body.prefs && typeof body.prefs === "object" ? JSON.parse(JSON.stringify(body.prefs).slice(0, 2000)) : {};
      const prior = await moves.findOne({ oldId: id, usedAt: { $exists: false } });
      const ABC = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";  // χωρίς 0/O, 1/I για να γράφεται εύκολα
      const code = prior?._id || Array.from(crypto.randomBytes(6), (b) => ABC[b % ABC.length]).join("");
      await moves.updateOne({ _id: code }, { $set: { oldId: id, topics: doc?.topics || [], prefs, at: new Date() } }, { upsert: true });
      return send(res, 200, { ok: true, code, count: (doc?.topics || []).length });
    }

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
