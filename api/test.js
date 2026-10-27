// Δοκιμαστική ειδοποίηση μόνο προς τη συσκευή που τη ζητά (το πολύ μία ανά λεπτό).
import { configured, pushTo, readBody, send, subId, subs, vapidKeys } from "./_lib.js";

export default async function handler(req, res) {
  if (!configured()) return send(res, 503, { error: "Οι ειδοποιήσεις δεν έχουν ρυθμιστεί ακόμα." });
  if (req.method !== "POST") return send(res, 405, { error: "Μόνο POST." });
  const body = await readBody(req);
  const endpoint = body.subscription && body.subscription.endpoint;
  if (typeof endpoint !== "string") return send(res, 400, { error: "Λείπει η συνδρομή." });
  const col = await subs();
  const id = subId(endpoint);
  const now = new Date();
  const doc = await col.findOneAndUpdate(
    { _id: id, $or: [{ lastTest: { $exists: false } }, { lastTest: { $lt: new Date(now - 60000) } }] },
    { $set: { lastTest: now } },
  );
  if (!doc) {
    const exists = await col.countDocuments({ _id: id }, { limit: 1 });
    return exists
      ? send(res, 429, { error: "Περίμενε ένα λεπτό πριν από νέα δοκιμή." })
      : send(res, 404, { error: "Η συσκευή δεν είναι γραμμένη. Ενεργοποίησε ξανά τις ειδοποιήσεις." });
  }
  const result = await pushTo(doc, {
    title: "PAOKalendar",
    body: "Οι ειδοποιήσεις δουλεύουν. Θα λαμβάνεις μόνο όσα διάλεξες.",
    url: "/#/notifications",
    tag: "test",
  }, await vapidKeys(), 300);
  if (result === "gone") await col.deleteOne({ _id: id });
  return send(res, result === "ok" ? 200 : 502, { result });
}
