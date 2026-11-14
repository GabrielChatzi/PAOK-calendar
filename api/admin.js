// Καταχωρίσεις του διαχειριστή από τη σελίδα του αγώνα: σκορ (σε εξέλιξη ή τελικό), με ειδοποίηση.
//
//   GET                                             οι καταχωρίσεις των τελευταίων ημερών (δημόσιες:
//                                                   τις διαβάζουν η σελίδα και το build_calendars.py)
//   POST {password, action: "check"}                έλεγχος κωδικού
//   POST {password, action: "score", nt, home, away, event, side, points, minute, scorer, period, set, note,
//         title, body, dry, silent}
//                                                   αποθήκευση και ειδοποίηση (dry: μόνο προεπισκόπηση·
//                                                   silent: μόνο αποθήκευση, χωρίς ειδοποίηση·
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
//   goal        ΓΚΟΛ (ΤΟΥ ΠΑΟΚ)! με το νέο σκορ· side: ποιος σκόραρε, minute, scorer·
//               στο μπάσκετ points 1–3: ΒΟΛΗ / ΚΑΛΑΘΙ / ΤΡΙΠΟΝΤΟ
//   disallowed  Ακυρώθηκε γκολ, με το σκορ μετά την ακύρωση
//   red         Κόκκινη κάρτα· side, minute, scorer (ο παίκτης ή η παίκτρια)
//   half        Ημίχρονο
//   second      Ξεκίνησε το 2ο ημίχρονο
//   et, pens    Πάμε παράταση / Πάμε στα πέναλτι
//   pstart      αρχή περιόδου ή σετ (period: 1–5)
//   period      τέλος περιόδου ή σετ (period: 1–5, set: πόντοι του σετ στο βόλεϊ)
//   score       σκορ τώρα, με σημείωση· στο βόλεϊ και με τους πόντους του σετ (set, period)
//   final       Τελικό
//   custom      ελεύθερη: title και body όπως τα γράφει ο διαχειριστής (κενός τίτλος → το σκορ)
export const EVENTS = ["start", "goal", "disallowed", "red", "half", "second", "et", "pens", "pstart", "period",
  "score", "final", "custom"];

const sport = (section) => String(section || "").replace(/-women$/, "");

// Ο τίτλος για το τέλος της περιόδου n, όπως στο live.py.
export function periodLabel(section, n) {
  const s = sport(section);
  if (s === "volley") return `Τέλος ${n}ου σετ`;
  if (n === 2) return "Ημίχρονο";
  if (n === 4) return s === "waterpolo" ? "Ισοπαλία, πάμε στα πέναλτι" : "Ισοπαλία, πάμε παράταση";
  return n <= 4 ? `Τέλος ${n}ης περιόδου` : "Τέλος παράτασης";
}

// Ο τίτλος για την αρχή της περιόδου ή του σετ n.
export function periodStartLabel(section, n) {
  if (sport(section) === "volley") return n >= 5 ? "Ξεκίνησε το τάι-μπρέικ" : `Ξεκίνησε το ${n}ο σετ`;
  return n >= 5 ? "Ξεκίνησε η παράταση" : `Ξεκίνησε η ${n}η περίοδος`;
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
  const volley = sport(m.section) === "volley";
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
  const who = [minuteText(e.minute), e.scorer].filter(Boolean).join(" ");
  if (event === "start") return live(`Ξεκίνησε: ${m.home} – ${m.away}`, comp, `${m.nt}-start`, "Ξεκίνησε");
  if (event === "goal") {
    const word = sport(m.section) !== "basketball" ? "ΓΚΟΛ"
      : e.points === 3 ? "ΤΡΙΠΟΝΤΟ" : e.points === 1 ? "ΒΟΛΗ" : "ΚΑΛΑΘΙ";
    const label = word === "ΓΚΟΛ" ? "Γκολ" : word === "ΤΡΙΠΟΝΤΟ" ? "Τρίποντο" : word === "ΒΟΛΗ" ? "Βολή" : "Καλάθι";
    return live(`${word}${paokScored(m, e.side) ? " ΤΟΥ ΠΑΟΚ" : ""}! ${score}`, who || comp,
      scoreKey(m.nt, e.home, e.away), [label, minuteText(e.minute)].filter(Boolean).join(" "));
  }
  if (event === "disallowed") {
    return live(`Ακυρώθηκε γκολ: ${score}`, e.note || comp, `${m.nt}-x${e.home}-${e.away}`, "Ακυρώθηκε γκολ");
  }
  if (event === "red") {
    const r = live(`Κόκκινη κάρτα (${m[e.side]}): ${score}`, who || comp, undefined, "Κόκκινη κάρτα");
    r.payload.title = `🟥 ${r.payload.title.replace(`${emoji} `, "")}`;  // η κάρτα στη θέση του emoji του αθλήματος
    return r;
  }
  if (event === "half") return live(`Ημίχρονο: ${score}`, comp, `${m.nt}-ht`, "Ημίχρονο");
  if (event === "second") return live(`Ξεκίνησε το 2ο ημίχρονο: ${score}`, comp, `${m.nt}-h2`, "2ο ημίχρονο");
  if (event === "et") return live(`Πάμε παράταση: ${score}`, comp, `${m.nt}-et`, "Παράταση");
  if (event === "pens") return live(`Πάμε στα πέναλτι: ${score}`, comp, `${m.nt}-pens`, "Πέναλτι");
  if (event === "pstart") {
    const what = periodStartLabel(m.section, e.period);
    return live(`${what}: ${score}`, comp, `${m.nt}-ps${e.period}`, what.replace(/^Ξεκίνησε (η |το )?/, ""));
  }
  if (event === "period") {
    const what = periodLabel(m.section, e.period);
    const pts = volley && e.set ? ` (${e.set.home}–${e.set.away})` : "";
    const once = what === "Ημίχρονο" ? `${m.nt}-ht` : `${m.nt}-${volley ? "set" : "p"}${e.period}`;
    return live(`${what}${pts}: ${score}`, comp, once, what);
  }
  if (event === "custom") {
    return live(e.title || score, e.body || comp, undefined, "Σε εξέλιξη");
  }
  // Σκορ τώρα· στο βόλεϊ μαζί με τους πόντους του σετ που παίζεται.
  // (όχι όταν μια ομάδα έφτασε τα 3 σετ: ο αγώνας τελείωσε, δεν υπάρχει επόμενο σετ)
  if (volley && e.set && Math.max(e.home, e.away) < 3) {
    const n = e.period || e.home + e.away + 1;
    return live(`${score} (${e.set.home}–${e.set.away} στο ${n}ο σετ)`, e.note || comp,
      `${scoreKey(m.nt, e.home, e.away)}-p${n}-${e.set.home}-${e.set.away}`, `${n}ο σετ ${e.set.home}–${e.set.away}`);
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
  if (["goal", "disallowed", "red"].includes(event)) {
    if (body.side !== "home" && body.side !== "away") return { error: "Διάλεξε ομάδα." };
    e.side = body.side;
  }
  if (event === "goal" || event === "red") { e.minute = text(body.minute, 10); e.scorer = text(body.scorer, 40); }
  if (event === "goal") e.points = [1, 2, 3].includes(Number(body.points)) ? Number(body.points) : 1;
  if (event === "custom") { e.title = text(body.title, 100); e.body = text(body.body, 140); }
  if (body.period != null && body.period !== "") {
    e.period = Number(body.period);
    if (!Number.isInteger(e.period) || e.period < 1 || e.period > 5) return { error: "Διάλεξε περίοδο." };
  }
  if ((event === "period" || event === "pstart") && !e.period) return { error: "Διάλεξε περίοδο." };
  const sh = Number(body.set?.home), sa = Number(body.set?.away);
  if (body.set && [sh, sa].every((x) => Number.isInteger(x) && x >= 0 && x <= 99)) e.set = { home: sh, away: sa };
  return e;
}

export default async function handler(req, res) {
  if (!configured()) return send(res, 503, { error: "Η βάση δεν έχει ρυθμιστεί." });
  const col = (await getDb()).collection("admin");

  if (req.method === "GET") {
    const since = new Date(Date.now() - KEEP_DAYS * 86400 * 1000);
    const entries = await col.find({ at: { $gte: since } }, { projection: { _id: 0, history: 0 } }).toArray();
    // Τελικά που έστειλε το live.py (api/push.js), για αγώνες χωρίς ακόμα επίσημο σκορ.
    const live = await (await getDb()).collection("livefinals").find({ at: { $gte: since } }, { projection: { _id: 0 } }).toArray();
    res.setHeader("Cache-Control", "public, s-maxage=15");
    return res.status(200).json({ entries, live });
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

  const entry = { nt, section: m.section, home, away, final: ev.final, note: ev.note, event: ev.event, set: ev.set || null,
    label: msg.label, at: new Date() };
  await col.updateOne({ _id: nt }, {
    $set: entry,
    $push: { history: { $each: [{ home, away, final: entry.final, event: ev.event, title: body.silent ? null : msg.payload.title, at: entry.at }], $slice: -30 } },
  }, { upsert: true });
  // Μόνο ενημέρωση: το σκορ φαίνεται στη σελίδα, χωρίς ειδοποίηση.
  if (body.silent) return send(res, 200, { ok: true, entry, push: null });
  const r = await deliver(msg.topics, msg.payload, { once: msg.once });
  return send(res, 200, { ok: true, entry, push: r });
}
