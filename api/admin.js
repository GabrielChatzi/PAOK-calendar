// Καταχωρίσεις του διαχειριστή από τη σελίδα του αγώνα: σκορ (σε εξέλιξη ή τελικό), με ειδοποίηση.
//
//   GET                                             οι καταχωρίσεις των τελευταίων ημερών (δημόσιες:
//                                                   τις διαβάζουν η σελίδα και το build_calendars.py)
//   POST {password, action: "check"}                έλεγχος κωδικού
//   POST {password, action: "score", nt, home, away, event, side, minute, scorer, period, set, note, dry}
//                                                   αποθήκευση και ειδοποίηση (dry: μόνο προεπισκόπηση·
//                                                   event: βλ. EVENTS· χωρίς event, final → τελικό, αλλιώς σκορ)
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
    "https://paokalendar.gr/matches.json",
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

// Τα γεγονότα της φόρμας, με τους ίδιους τίτλους και τα ίδια κλειδιά «once» με το live.py
// (once_key), ώστε όποια συσκευή πήρε κάτι από εδώ να μην το ξαναπάρει από το live, και ανάποδα.
//   start       Ξεκίνησε
//   goal        ΓΚΟΛ (ΤΟΥ ΠΑΟΚ)! με το νέο σκορ· side: ποιος σκόραρε, minute, scorer
//   disallowed  Ακυρώθηκε γκολ, με το σκορ μετά την ακύρωση
//   half        Ημίχρονο
//   period      τέλος περιόδου ή σετ (period: 1–5, set: πόντοι του σετ στο βόλεϊ)
//   score       ελεύθερο σκορ τώρα, με σημείωση
//   final       Τελικό
export const EVENTS = ["start", "goal", "disallowed", "half", "period", "score", "final"];

const sport = (section) => String(section || "").replace(/-women$/, "");

// Ο τίτλος για το τέλος της περιόδου n, όπως στο live.py.
export function periodLabel(section, n) {
  const s = sport(section);
  if (s === "volley") return `Τέλος ${n}ου σετ`;
  if (n === 2) return "Ημίχρονο";
  if (n === 4) return s === "waterpolo" ? "Ισοπαλία, πάμε στα πέναλτι" : "Ισοπαλία, πάμε παράταση";
  return n <= 4 ? `Τέλος ${n}ης περιόδου` : "Τέλος παράτασης";
}

function paokScored(m, side) {
  if (typeof m.paokHome === "boolean") return side === "home" ? m.paokHome : !m.paokHome;
  return /ΠΑΟΚ|PAOK/i.test(side === "home" ? m.home : m.away);
}

// «23» → «23'», «45+2» → «45+2'»· ό,τι άλλο μένει όπως γράφτηκε.
function minuteText(x) {
  const t = String(x || "").trim();
  return /^\d+(\+\d+)?$/.test(t) ? `${t}'` : t;
}

export function message(m, e) {
  const emoji = EMOJI[m.section] || "";
  const score = `${m.home} ${e.home}–${e.away} ${m.away}`;
  const note = e.note ? ` (${e.note})` : "";
  const comp = m.competition || "";
  const url = `/#/m/${m.nt}`;
  const topics = (kinds) => kinds.flatMap((k) => [`s:${m.section}:${k}`, `m:${m.nt}:${k}`]);
  const event = e.event || (e.final ? "final" : "score");
  if (event === "final") {
    return {
      topics: topics(["result", "live"]), once: `${m.nt}-result`, label: "Τελικό",
      payload: { title: `${emoji} Τελικό: ${score}${note}`, body: [comp, m.round].filter(Boolean).join(", "),
        url, tag: `${m.nt}-result` },
    };
  }
  // Σε εξέλιξη: σε όσους θέλουν το live· στα τμήματα χωρίς live, σε όσους θέλουν την υπενθύμιση
  // (όπως και η ειδοποίηση έναρξης). Χωρίς tag, όπως οι αυτόματες: η μία δεν σβήνει την άλλη.
  const live = (title, body, once, label) => ({
    topics: topics(m.live ? ["live"] : ["live", "pre"]), once, label,
    payload: { title: `${emoji} ${title}`, body, url },
  });
  if (event === "start") return live(`Ξεκίνησε: ${m.home} – ${m.away}`, comp, `${m.nt}-start`, "Ξεκίνησε");
  if (event === "goal") {
    const minute = minuteText(e.minute);
    return live(`ΓΚΟΛ${paokScored(m, e.side) ? " ΤΟΥ ΠΑΟΚ" : ""}! ${score}`,
      [minute, e.scorer].filter(Boolean).join(" ") || comp, scoreKey(m.nt, e.home, e.away),
      ["Γκολ", minute].filter(Boolean).join(" "));
  }
  if (event === "disallowed") {
    return live(`Ακυρώθηκε γκολ: ${score}`, e.note || comp, `${m.nt}-x${e.home}-${e.away}`, "Ακυρώθηκε γκολ");
  }
  if (event === "half") return live(`Ημίχρονο: ${score}`, comp, `${m.nt}-ht`, "Ημίχρονο");
  if (event === "period") {
    const what = periodLabel(m.section, e.period);
    const volley = sport(m.section) === "volley";
    const pts = volley && e.set ? ` (${e.set.home}–${e.set.away})` : "";
    const once = what === "Ημίχρονο" ? `${m.nt}-ht` : `${m.nt}-${volley ? "set" : "p"}${e.period}`;
    return live(`${what}${pts}: ${score}`, comp, once, what);
  }
  return live(score, e.note || "Σκορ τώρα", scoreKey(m.nt, e.home, e.away), e.note || "Σε εξέλιξη");
}

// Το γεγονός από το αίτημα, ελεγμένο· σε λάθος { error }.
export function parseEvent(body) {
  const event = EVENTS.includes(body.event) ? body.event : body.final ? "final" : "score";
  const home = Number(body.home), away = Number(body.away);
  if (![home, away].every((x) => Number.isInteger(x) && x >= 0 && x <= 300)) {
    return { error: "Το σκορ πρέπει να είναι δύο αριθμοί." };
  }
  const text = (x, n) => String(x ?? "").trim().slice(0, n);
  const e = { event, home, away, final: event === "final", note: text(body.note, 80) };
  if (event === "goal" || event === "disallowed") {
    if (body.side !== "home" && body.side !== "away") return { error: "Διάλεξε ομάδα." };
    e.side = body.side;
  }
  if (event === "goal") { e.minute = text(body.minute, 10); e.scorer = text(body.scorer, 40); }
  if (event === "period") {
    e.period = Number(body.period);
    if (!Number.isInteger(e.period) || e.period < 1 || e.period > 5) return { error: "Διάλεξε περίοδο." };
    const sh = Number(body.set?.home), sa = Number(body.set?.away);
    if (body.set && [sh, sa].every((x) => Number.isInteger(x) && x >= 0 && x <= 99)) e.set = { home: sh, away: sa };
  }
  return e;
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

  const ev = parseEvent(body);
  if (ev.error) return send(res, 400, { error: ev.error });
  const { home, away } = ev;
  let m;
  try { m = await findMatch(nt); } catch (e) { return send(res, 502, { error: e.message }); }
  if (!m) return send(res, 404, { error: "Ο αγώνας δεν βρέθηκε στο πρόγραμμα." });

  const prior = await col.findOne({ _id: nt }, { projection: { home: 1, away: 1, final: 1 } });
  const msg = message(m, ev);
  // Διόρθωση τελικού που στάλθηκε ήδη: νέο κλειδί, ώστε να φτάσει ξανά σε όλους.
  if (ev.final && prior?.final && (prior.home !== home || prior.away !== away)) {
    msg.once = `${nt}-result-${home}-${away}`;
    msg.payload.title = msg.payload.title.replace("Τελικό:", "Διόρθωση τελικού:");
  }
  // Προεπισκόπηση: ό,τι θα σταλεί, χωρίς αποθήκευση ή αποστολή.
  if (body.dry) return send(res, 200, { ok: true, preview: { title: msg.payload.title, body: msg.payload.body } });

  const entry = { nt, section: m.section, home, away, final: ev.final, note: ev.note, event: ev.event,
    label: msg.label, at: new Date() };
  await col.updateOne({ _id: nt }, {
    $set: entry,
    $push: { history: { $each: [{ home, away, final: entry.final, event: ev.event, title: msg.payload.title, at: entry.at }], $slice: -30 } },
  }, { upsert: true });
  const r = await deliver(msg.topics, msg.payload, { once: msg.once });
  return send(res, 200, { ok: true, entry, push: r });
}
