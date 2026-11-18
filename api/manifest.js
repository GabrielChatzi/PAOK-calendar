// Το manifest της εφαρμογής με τον κωδικό μεταφοράς στη διεύθυνση έναρξης (start_url): στο iPhone η
// εφαρμογή στην αρχική οθόνη έχει άλλη μνήμη από το Safari, οπότε ο κωδικός πρέπει να ανοίγει μαζί της.
// Με ?app=admin: δεύτερο εικονίδιο «PAOK Admin» για τον διαχειριστή (άλλο όνομα, εικονίδιο και διεύθυνση
// έναρξης). Στο iPhone κάθε εικονίδιο της αρχικής οθόνης έχει δική του μνήμη, οπότε το ένα μένει απλός
// χρήστης και το άλλο ανοίγει πάντα σε λειτουργία διαχειριστή (βλ. docs/index.html, «Εικονίδιο διαχειριστή»).
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
  if (req.query?.app === "admin") Object.assign(manifest, adminManifest());
  res.setHeader("Content-Type", "application/manifest+json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  return res.status(200).send(JSON.stringify(manifest));
}

export function adminManifest() {
  return {
    name: "PAOKalendar – Διαχειριστής", short_name: "PAOK Admin", id: "./?app=admin", start_url: "./?app=admin#/admin",
    icons: [
      { src: "icons/icon-admin-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "icons/icon-admin-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
    ],
    shortcuts: [],
  };
}
