// Αποστολή ειδοποίησης σε όσους έχουν γραφτεί σε κάποιο από τα θέματα.
//
// Το καλεί μόνο το GitHub Actions του repo: η ταυτότητα ελέγχεται με το OIDC token του GitHub
// (υπογεγραμμένο από το GitHub, χωρίς κοινό μυστικό), για το repo και το main.
import { createRemoteJWKSet, jwtVerify } from "jose";
import { TOPIC_RE, configured, lastErrors, pushTo, readBody, send, subs, vapidKeys } from "./_lib.js";

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
  const wanted = new Set((body.topics || []).filter((t) => typeof t === "string" && TOPIC_RE.test(t)));
  if (!wanted.size || !body.title) return send(res, 400, { error: "Λείπουν θέματα ή τίτλος." });
  const payload = {
    title: String(body.title).slice(0, 120),
    body: String(body.body || "").slice(0, 300),
    url: String(body.url || "/").slice(0, 200),
    tag: body.tag ? String(body.tag).slice(0, 64) : undefined,
    // quiet: αν υπάρχει ήδη ειδοποίηση με το ίδιο tag, την αντικαθιστά χωρίς νέο ήχο.
    quiet: body.quiet ? true : undefined,
  };

  const col = await subs();
  const targets = await col.find({ topics: { $in: [...wanted] } }, { projection: { endpoint: 1, keys: 1 } }).toArray();
  const keys = await vapidKeys();
  const ttl = [...wanted].some((t) => t.endsWith(":live")) ? 2 * 3600 : 12 * 3600;
  lastErrors.length = 0;
  const results = await Promise.all(targets.map((s) => pushTo(s, payload, keys, ttl)));
  const gone = targets.filter((_, i) => results[i] === "gone").map((s) => s._id);
  if (gone.length) await col.deleteMany({ _id: { $in: gone } });
  const count = (x) => results.filter((r) => r === x).length;
  return send(res, 200, { matched: targets.length, sent: count("ok"), removed: count("gone"), failed: count("error"),
    errors: lastErrors.slice(0, 5) });
}
