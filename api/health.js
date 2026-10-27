// Κατάσταση των ειδοποιήσεων: αν είναι συνδεδεμένη η βάση και πόσες συσκευές είναι γραμμένες.
import { configured, send, subs } from "./_lib.js";

export default async function handler(req, res) {
  if (!configured()) return send(res, 200, { configured: false });
  try {
    const count = await (await subs()).estimatedDocumentCount();
    return send(res, 200, { configured: true, db: true, subscribers: count });
  } catch (e) {
    return send(res, 200, { configured: true, db: false, error: e.message });
  }
}
