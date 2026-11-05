// Το manifest της εφαρμογής με τον κωδικό μεταφοράς στη διεύθυνση έναρξης (start_url): στο iPhone η
// εφαρμογή στην αρχική οθόνη έχει άλλη μνήμη από το Safari, οπότε ο κωδικός πρέπει να ανοίγει μαζί της.
export default async function handler(req, res) {
  const code = String(req.query?.import || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 6);
  let manifest;
  try {
    const r = await fetch(`https://${req.headers.host || "paokalendar.gr"}/manifest.webmanifest`);
    manifest = await r.json();
  } catch {
    return res.status(502).json({ error: "manifest" });
  }
  if (code.length === 6) manifest.start_url = `./?import=${code}`;
  res.setHeader("Content-Type", "application/manifest+json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  return res.status(200).send(JSON.stringify(manifest));
}
