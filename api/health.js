// Κατάσταση των ειδοποιήσεων: αν είναι συνδεδεμένη η βάση και πόσες συσκευές είναι γραμμένες,
// ανά υπηρεσία (Apple, Google, Mozilla, Microsoft). Με ?topic=<θέμα> μετρά μόνο όσες το έχουν.
import { TOPIC_RE, configured, send, subs } from "./_lib.js";

function service(endpoint) {
  const host = new URL(endpoint).hostname;
  return host.includes("apple") ? "apple" : host.includes("google") ? "google"
    : host.includes("mozilla") ? "mozilla" : host.includes("windows") ? "microsoft" : "other";
}

export default async function handler(req, res) {
  if (!configured()) return send(res, 200, { configured: false });
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
