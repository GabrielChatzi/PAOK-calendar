// Καταχωρίσεις του διαχειριστή από τη σελίδα του αγώνα: σκορ (σε εξέλιξη ή τελικό), με ειδοποίηση.
//
//   GET                                             οι καταχωρίσεις των τελευταίων ημερών (δημόσιες:
//                                                   τις διαβάζουν η σελίδα και το build_calendars.py)
//   POST {password, action: "check"}                έλεγχος κωδικού
//   POST {password, action: "score", nt, home, away, final, note}
//                                                   αποθήκευση και ειδοποίηση
//   POST {password, action: "clear", nt}            σβήσιμο (χωρίς ειδοποίηση)
//
// Ο κωδικός είναι η μεταβλητή ADMIN_PASSWORD της Vercel. Ό,τι γράφει ο διαχειριστής έχει
// προτεραιότητα: το τελικό στέλνεται με το ίδιο κλειδί «once» με το αυτόματο (live.py,
// ενημέρωση προγράμματος), οπότε όποια συσκευή το πήρε από εδώ δεν το ξαναπαίρνει, και το ίδιο
// για ένα σκορ σε εξέλιξη (π.χ. ένα γκολ) που θα έφερνε μετά το live.
import crypto from "node:crypto";
import { configured, deliver, getDb, readBody, send } from "./_lib.js";

const EMOJI = {
  football: "⚽", "football-women": "⚽", basketball: "🏀", "basketball-women": "🏀",
  volley: "🏐", "volley-women": "🏐", handball: "🤾", "handball-women": "🤾",
  waterpolo: "🤽", "waterpolo-women": "🤽", futsal: "🥅",
};
const KEEP_DAYS = 4;

function passwordOk(given) {
  const want = process.env.ADMIN_PASSWORD || "";
  if (!want || typeof given !== "string" || !given) return false;
  const h = (x) => crypto.createHash("sha256").update(x).digest();
  return crypto.timingSafeEqual(h(given), h(want));
}

async function findMatch(nt) {
  const urls = [
    `https://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/data/matches.json?t=${Math.floor(Date.now() / 60000)}`,
    "https://paokalendar.vercel.app/matches.json",
  ];
  for (const url of urls) {
    try {
      const r = await fetch(url, { headers: { "Cache-Control": "no-cache" } });
      if (r.ok) return ((await r.json()).matches || []).find((m) => m.nt === nt) || null;
    } catch { /* επόμενη */ }
  }
  throw new Error("Δεν διαβάστηκε το πρόγραμμα.");
}

// Το κλειδί «once» για ένα σκορ σε εξέλιξη: το ίδιο φτιάχνει και το live.py για τα γκολ.
export function scoreKey(nt, home, away) {
  return `${nt}-s${home}-${away}`;
}

export function message(m, e) {
  const emoji = EMOJI[m.section] || "";
  const score = `${m.home} ${e.home}–${e.away} ${m.away}`;
  const note = e.note ? ` (${e.note})` : "";
  const topics = (kinds) => kinds.flatMap((k) => [`s:${m.section}:${k}`, `m:${m.nt}:${k}`]);
  if (e.final) {
    return {
      topics: topics(["result", "live"]), once: `${m.nt}-result`,
      payload: { title: `${emoji} Τελικό: ${score}${note}`, body: [m.competition, m.round].filter(Boolean).join(", "),
        url: `/#/m/${m.nt}`, tag: `${m.nt}-result` },
    };
  }
  // Σε εξέλιξη: σε όσους θέλουν το live· στα τμήματα χωρίς live, σε όσους θέλουν την υπενθύμιση
  // (όπως και η ειδοποίηση έναρξης).
  return {
    topics: topics(m.live ? ["live"] : ["live", "pre"]), once: scoreKey(m.nt, e.home, e.away),
    payload: { title: `${emoji} ${score}`, body: e.note || "Σκορ τώρα", url: `/#/m/${m.nt}`, tag: `${m.nt}-admin` },
  };
}

export default async function handler(req, res) {
  if (!configured()) return send(res, 503, { error: "Η βάση δεν έχει ρυθμιστεί." });
  const col = (await getDb()).collection("admin");

  if (req.method === "GET") {
    const since = new Date(Date.now() - KEEP_DAYS * 86400 * 1000);
    const entries = await col.find({ at: { $gte: since } }, { projection: { _id: 0, history: 0 } }).toArray();
    res.setHeader("Cache-Control", "public, s-maxage=15");
    return res.status(200).json({ entries });
  }
  if (req.method !== "POST") return send(res, 405, { error: "Μόνο GET ή POST." });

  const body = await readBody(req);
  if (!process.env.ADMIN_PASSWORD) return send(res, 503, { error: "Λείπει το ADMIN_PASSWORD στη Vercel." });
  if (!passwordOk(body.password)) {
    await new Promise((r) => setTimeout(r, 1000));  // αργή απάντηση σε λάθος κωδικό
    return send(res, 401, { error: "Λάθος κωδικός." });
  }
  if (body.action === "check") return send(res, 200, { ok: true });

  const nt = String(body.nt || "");
  if (!/^[0-9a-f]{10}$/.test(nt)) return send(res, 400, { error: "Άγνωστος αγώνας." });

  if (body.action === "clear") {
    await col.deleteOne({ _id: nt });
    return send(res, 200, { ok: true });
  }
  if (body.action !== "score") return send(res, 400, { error: "Άγνωστη ενέργεια." });

  const home = Number(body.home), away = Number(body.away);
  if (![home, away].every((x) => Number.isInteger(x) && x >= 0 && x <= 300)) {
    return send(res, 400, { error: "Το σκορ πρέπει να είναι δύο αριθμοί." });
  }
  let m;
  try { m = await findMatch(nt); } catch (e) { return send(res, 502, { error: e.message }); }
  if (!m) return send(res, 404, { error: "Ο αγώνας δεν βρέθηκε στο πρόγραμμα." });

  const prior = await col.findOne({ _id: nt }, { projection: { home: 1, away: 1, final: 1 } });
  const entry = { nt, section: m.section, home, away, final: Boolean(body.final),
    note: String(body.note || "").trim().slice(0, 80), at: new Date() };
  await col.updateOne({ _id: nt }, {
    $set: entry, $push: { history: { $each: [{ home, away, final: entry.final, at: entry.at }], $slice: -30 } },
  }, { upsert: true });

  const msg = message(m, entry);
  // Διόρθωση τελικού που στάλθηκε ήδη: νέο κλειδί, ώστε να φτάσει ξανά σε όλους.
  if (entry.final && prior?.final && (prior.home !== home || prior.away !== away)) {
    msg.once = `${nt}-result-${home}-${away}`;
    msg.payload.title = msg.payload.title.replace("Τελικό:", "Διόρθωση τελικού:");
  }
  const r = await deliver(msg.topics, msg.payload, { once: msg.once });
  return send(res, 200, { ok: true, entry, push: r });
}
