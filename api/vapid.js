// Το δημόσιο κλειδί VAPID, που χρειάζεται η σελίδα για να γραφτεί στις ειδοποιήσεις.
import { configured, send, vapidKeys } from "./_lib.js";

export default async function handler(req, res) {
  if (!configured()) return send(res, 503, { error: "Οι ειδοποιήσεις δεν έχουν ρυθμιστεί ακόμα." });
  const { publicKey } = await vapidKeys();
  res.setHeader("Cache-Control", "public, max-age=3600");
  res.status(200).json({ publicKey });
}
