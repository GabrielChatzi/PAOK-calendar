// Αποστολή ειδοποίησης σε όσους έχουν γραφτεί σε κάποιο από τα θέματα.
//
// Το καλεί μόνο το GitHub Actions του repo: η ταυτότητα ελέγχεται με το OIDC token του GitHub
// (υπογεγραμμένο από το GitHub, χωρίς κοινό μυστικό), για το repo και το main.
import { createRemoteJWKSet, jwtVerify } from "jose";
import { TOPIC_RE, configured, deliver, getDb, readBody, send } from "./_lib.js";

const ISSUER = "https://token.actions.githubusercontent.com";
const JWKS = createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`));
const REPOSITORY = "gabrielchatzi/paok-calendar";

async function authorized(req) {
  const token = String(req.headers.authorization || "").replace(/^Bearer\s+/i, "");
  if (!token) return false;
  try {
    const { payload } = await jwtVerify(token, JWKS, { issuer: ISSUER, audience: "paokalendar" });
    return String(payload.repository || "").toLowerCase() === REPOSITORY && payload.ref === "refs/heads/main";
  } catch {
    return false;
  }
}

export default async function handler(req, res) {
  if (!configured()) return send(res, 503, { error: "Οι ειδοποιήσεις δεν έχουν ρυθμιστεί ακόμα." });
  if (req.method !== "POST") return send(res, 405, { error: "Μόνο POST." });
  if (!(await authorized(req))) return send(res, 401, { error: "Μη εξουσιοδοτημένο." });

  const body = await readBody(req);
  // Το τελικό από το live.py: κρατιέται ώστε το πρόγραμμα (και οι εικόνες των social) να το έχουν
  // αμέσως, πριν το φέρει η επίσημη πηγή (βλ. apply_live_finals στο build_calendars.py).
  const fin = body.result;
  if (fin && /^[0-9a-f]{10}$/.test(String(fin.nt)) && [fin.home, fin.away].every((x) => Number.isInteger(x) && x >= 0 && x <= 300)) {
    await (await getDb()).collection("livefinals").updateOne({ _id: fin.nt },
      { $set: { nt: fin.nt, home: fin.home, away: fin.away, at: new Date() } }, { upsert: true });
  }
  const wanted = new Set((body.topics || []).filter((t) => typeof t === "string" && TOPIC_RE.test(t)));
  if (!wanted.size || !body.title) return send(res, 400, { error: "Λείπουν θέματα ή τίτλος." });
  const payload = {
    title: String(body.title).slice(0, 120),
    body: String(body.body || "").slice(0, 300),
    url: String(body.url || "/").slice(0, 200),
    tag: body.tag ? String(body.tag).slice(0, 64) : undefined,
    // quiet: αν υπάρχει ήδη ειδοποίηση με το ίδιο tag, την αντικαθιστά χωρίς νέο ήχο.
    quiet: body.quiet ? true : undefined,
    // Η ώρα έναρξης (ISO), για να γράψει το κινητό την ώρα στη δική του ζώνη (docs/sw.js).
    start: typeof body.start === "string" && /^\d{4}-\d\d-\d\dT\d\d:\d\d/.test(body.start) ? body.start.slice(0, 32) : undefined,
  };

  const r = await deliver([...wanted], payload, { once: body.once });
  return send(res, 200, r);
}
