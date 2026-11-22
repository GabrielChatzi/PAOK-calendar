// Τα δεδομένα της σελίδας (πρόγραμμα, βαθμολογίες, κατάσταση, ημερολόγια .ics) από τον κλάδο «data»
// του GitHub, όπου τα γράφει το workflow update.yml. Έτσι οι ενημερώσεις δεν χρειάζονται νέα έκδοση
// της Vercel (το δωρεάν πακέτο έχει όριο 100 εκδόσεις την ημέρα). Οι διευθύνσεις μένουν ίδιες
// (/matches.json, /football-home.ics κ.λπ., βλ. rewrites στο vercel.json). Το CDN κρατά την απάντηση
// 1 λεπτό· αν το GitHub δεν απαντήσει, συνεχίζει να δίνει την τελευταία για 1 ώρα.
const RAW = "https://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/data/";
const FILE = /^(?:(?:matches|standings|status|events|trophies)\.json|[a-z]+(?:-women)?-(?:home|away)\.ics|[a-z]+-events\.ics|archive\/(?:index|\d{4}-\d{2})\.json|crests\/[0-9a-f]{16}\.(?:png|jpg|gif|webp|svg))$/;
// Σήματα αντιπάλων των ακαδημιών (crests.py): το όνομα βγαίνει από την αρχική διεύθυνση, άρα δεν αλλάζει ποτέ.
const IMAGE = { png: "image/png", jpg: "image/jpeg", gif: "image/gif", webp: "image/webp", svg: "image/svg+xml" };

export default async function handler(req, res) {
  const f = String(req.query?.f || "");
  if (!FILE.test(f)) {
    res.setHeader("Cache-Control", "no-store");
    return res.status(404).json({ error: "άγνωστο αρχείο" });
  }
  try {
    // Το ?t= αλλάζει κάθε λεπτό, ώστε να μη μας δίνει το GitHub παλιό αντίγραφο (κρατά 5 λεπτά).
    const r = await fetch(`${RAW}${f}?t=${Math.floor(Date.now() / 60000)}`, {
      headers: { "User-Agent": "PAOKalendar (+https://paokalendar.gr)" },
    });
    if (!r.ok) throw new Error(`GitHub ${r.status}`);
    const body = Buffer.from(await r.arrayBuffer());
    const ext = f.split(".").pop();
    if (f.startsWith("crests/")) {
      res.setHeader("Content-Type", IMAGE[ext]);
      res.setHeader("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; sandbox");
      res.setHeader("Cache-Control", "public, max-age=604800, s-maxage=31536000, immutable");
      return res.status(200).send(body);
    }
    res.setHeader("Content-Type", f.endsWith(".ics") ? "text/calendar; charset=utf-8" : "application/json; charset=utf-8");
    res.setHeader("Cache-Control", "public, max-age=0, s-maxage=60, stale-while-revalidate=60, stale-if-error=3600");
    return res.status(200).send(body);
  } catch (e) {
    res.setHeader("Cache-Control", "no-store");
    return res.status(502).json({ error: e.message });
  }
}
