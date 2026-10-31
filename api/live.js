// Ζωντανό σκορ πόλο από τα συστήματα χρονομέτρησης της Microplus:
//   koe: ελληνικά πρωταθλήματα (live.koe.org.gr, το ίδιο που δείχνει το waterpololeague.gr)
//   ea:  ευρωπαϊκά κύπελλα (European Aquatics)
// Η ΚΟΕ δεν δέχεται αιτήματα από browsers (CORS) και το πρόγραμμα της European Aquatics είναι
// όλη η σεζόν σε ένα αρχείο, γι' αυτό η σελίδα και το live.py παίρνουν από εδώ μόνο τον αγώνα που
// θέλουν. Η απάντηση κρατιέται 15'' στο CDN της Vercel, όσοι κι αν τη ζητούν.
//
// Απάντηση: { state: "pre" | "in" | "post", home, away, quarter, done, quarters: [{ home, away }] }
//   quarter: η περίοδος σε εξέλιξη (0 αν δεν ξέρουμε), done: πόσες περίοδοι τελείωσαν.

const KOE = "https://live.koe.org.gr/api-waterpolo/wp";
const EA = "https://ea.microplustimingservices.com/api/wp";
const UA = "Mozilla/5.0 (PAOKalendar live; +https://paokalendar.vercel.app)";
const ID = /^[A-Za-z0-9_-]{1,24}$/;

const tokens = {};  // ανά πηγή: { value, until }

async function getJson(url, headers = {}) {
  const r = await fetch(url, { headers: { "User-Agent": UA, Accept: "application/json", ...headers } });
  if (!r.ok) throw new Error(`${r.status} από ${new URL(url).host}`);
  const text = await r.text();
  return text.trim() ? JSON.parse(text) : null;
}

async function token(src) {
  const t = tokens[src];
  if (t && Date.now() < t.until) return t.value;
  if (src === "koe") {
    const d = await getJson(`${KOE}/token`);
    tokens.koe = { value: d.token, until: Date.now() + Math.max(60, (d.expiresInSec || 600) - 120) * 1000 };
  } else {
    const d = await getJson(`${EA}/site/token`);
    tokens.ea = { value: d.data.token, until: Date.now() + 10 * 60 * 1000 };
  }
  return tokens[src].value;
}

function num(x) {
  const n = parseInt(String(x ?? "").trim(), 10);
  return Number.isFinite(n) ? n : null;
}

// 0 = δεν ξεκίνησε, 1 = σε εξέλιξη, 2 = τελείωσε (όπως στις σελίδες της Microplus).
function stateOf(code) {
  const c = String(code ?? "").toUpperCase();
  return c === "1" || c === "RUNNING" || c === "LIVE" ? "in"
    : c === "2" || c === "OFFICIAL" || c === "UNOFFICIAL" ? "post" : "pre";
}

// Σκορ μιας περιόδου από το αντικείμενο της πηγής, όποια ονόματα κι αν έχει.
function pair(q) {
  if (!q || typeof q !== "object") return null;
  const a = num(q.r1 ?? q.s1 ?? q.ResA ?? q.a), b = num(q.r2 ?? q.s2 ?? q.ResB ?? q.b);
  return a == null && b == null ? null : { home: a ?? 0, away: b ?? 0 };
}

async function koe(p) {
  const url = `${KOE}/KOE/get/resultsDBlikeJSON/${p.cat}/${p.gara}/${p.tur}/${p.gru}/${p.a}/${p.b}`;
  const j = (await getJson(url, { "x-wp-token": await token("koe") })) || {};
  const home = num(j.r1), away = num(j.r2);
  const quarters = (Array.isArray(j.q) ? j.q : []).map(pair).filter(Boolean);
  let state = stateOf(j.st);
  if (state === "pre" && (home != null || away != null) && j.st == null) state = "in";
  const quarter = num(j.p?.q ?? j.per ?? j.pe) || (state === "in" ? quarters.length || 1 : 0);
  return {
    state, home: home ?? 0, away: away ?? 0, quarter,
    done: state === "post" ? quarters.length : Math.max(0, quarter - 1), quarters,
  };
}

async function ea(p) {
  if (!/^EACLUB\d\d$/.test(p.code || "")) throw new Error("λάθος κωδικός");
  const d = await getJson(`${EA}/${p.code}/get/schedule/*/*/*/*/*`, { Authorization: `Bearer ${await token("ea")}` });
  const x = (d?.Schedule || []).find((o) => o.OraCatCode === p.cat && String(o.OraGaraCode) === p.gara &&
    String(o.OraTurCode) === p.tur && o.OraTeamCodeA === p.a && o.OraTeamCodeB === p.b);
  if (!x) throw new Error("ο αγώνας δεν βρέθηκε");
  const state = stateOf(x.OraStatus);
  const quarter = state === "in" ? num(x.OraPeriods) || 1 : 0;
  return {
    state, home: num(x.OraResA) ?? 0, away: num(x.OraResB) ?? 0, quarter,
    done: state === "post" ? num(x.OraPeriods) || 4 : Math.max(0, quarter - 1), quarters: [],
  };
}

export default async function handler(req, res) {
  const q = req.query || {};
  const p = {};
  for (const k of ["src", "code", "cat", "gara", "tur", "gru", "a", "b"]) {
    if (q[k] == null) continue;
    if (!ID.test(String(q[k]))) return res.status(400).json({ error: `λάθος ${k}` });
    p[k] = String(q[k]);
  }
  const need = p.src === "koe" ? ["cat", "gara", "tur", "gru", "a", "b"] : p.src === "ea" ? ["code", "cat", "gara", "tur", "a", "b"] : null;
  if (!need || need.some((k) => !p[k])) return res.status(400).json({ error: "λάθος αγώνας" });
  const run = () => (p.src === "koe" ? koe(p) : ea(p));
  try {
    // Αν έληξε το token νωρίτερα από ό,τι περιμέναμε, παίρνουμε νέο και ξαναδοκιμάζουμε μία φορά.
    const out = await run().catch((e) => {
      if (!/^40[13] /.test(e.message)) throw e;
      delete tokens[p.src];
      return run();
    });
    res.setHeader("Cache-Control", "public, s-maxage=15, stale-while-revalidate=15");
    return res.status(200).json(out);
  } catch (e) {
    res.setHeader("Cache-Control", "no-store");
    return res.status(502).json({ error: e.message });
  }
}
