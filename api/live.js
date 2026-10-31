// Ζωντανό σκορ από τα επίσημα συστήματα, για τη σελίδα και το live.py:
//   koe: πόλο, ελληνικά πρωταθλήματα (live.koe.org.gr, Microplus· το ίδιο δείχνει το waterpololeague.gr)
//   ea:  πόλο, ευρωπαϊκά κύπελλα (European Aquatics, Microplus)
//   dp:  βόλεϊ, Data Project (ΕΟΠΕ: eope-web, Volley League ανδρών: hvl-web), μέσω SignalR
//   gs:  μπάσκετ, Genius Sports / FIBA LiveStats (Basket League, όπως το esake.gr)
// Οι πηγές δεν δέχονται αιτήματα από browsers (CORS) ή δίνουν πολύ περισσότερα από έναν αγώνα,
// γι' αυτό τις διαβάζουμε από εδώ. Η απάντηση κρατιέται 15'' στο CDN της Vercel, όσοι κι αν τη ζητούν.
//
// Απάντηση: { state: "pre" | "in" | "post", home, away, quarter, done, clock, quarters: [{ home, away }] }
//   quarter: η περίοδος/σετ σε εξέλιξη (0 αν δεν ξέρουμε), done: πόσες περίοδοι/σετ τελείωσαν,
//   clock: ο χρόνος που απομένει (πόλο ΚΟΕ) ή οι πόντοι του τρέχοντος σετ (βόλεϊ), quarters: σκορ ανά
//   περίοδο ή πόντοι ανά σετ. Στο βόλεϊ home/away είναι τα σετ.

const KOE = "https://live.koe.org.gr/api-waterpolo/wp";
const EA = "https://ea.microplustimingservices.com/api/wp";
const UA = "Mozilla/5.0 (PAOKalendar live; +https://paokalendar.vercel.app)";
const ID = /^[A-Za-z0-9_-]{1,40}$/;  // και ημερομηνίες (2026-10-31)

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
  const h = { "x-wp-token": await token("koe") };
  const [j, sch] = await Promise.all([
    getJson(`${KOE}/KOE/get/resultsDBlikeJSON/${p.cat}/${p.gara}/${p.tur}/${p.gru}/${p.a}/${p.b}`, h),
    getJson(`${KOE}/KOE/get/schedulereferee/${p.cat}/${p.gara}/*/*/*`, h),
  ]);
  // Η κατάσταση του αγώνα (0/1/2) από το πρόγραμμα: είναι η μόνη αξιόπιστη. Στις περιόδους το st
  // γίνεται 2 κάθε φορά που σταματά το ρολόι (time-out, διάλειμμα), όχι μόνο στο τέλος τους.
  const x = (sch?.Schedule || []).find((o) => String(o.OraTurCode) === p.tur &&
    String(o.OraTeamCodeA) === p.a && String(o.OraTeamCodeB) === p.b);
  if (!x) throw new Error("ο αγώνας δεν βρέθηκε στο πρόγραμμα της ΚΟΕ");
  const state = stateOf(x.OraStatus);
  // q: 4 περίοδοι και τα πέναλτι, η καθεμία με σκορ (r1, r2), κατάσταση st (0/1/2) και χρόνο tg.
  const q = Array.isArray(j?.q) ? j.q : [];
  const st = q.map((o) => String(o?.st ?? "0"));
  let last = -1;  // η τελευταία περίοδος που έχει ξεκινήσει
  st.forEach((s, i) => { if (s !== "0") last = i; });
  const blank = { home: "", away: "" };
  const quarters = q.slice(0, st[4] && st[4] !== "0" ? 5 : 4).map((o, i) => (st[i] === "0" ? blank : pair(o) || blank));
  return {
    state, home: num(j?.r1) ?? num(x.OraResA) ?? 0, away: num(j?.r2) ?? num(x.OraResB) ?? 0,
    quarter: state === "in" && last >= 0 ? last + 1 : 0,
    // Τελειωμένες: όσες είναι πριν από την τελευταία που ξεκίνησε (στο τέλος, όλες).
    done: state === "post" ? Math.min(4, last + 1) : Math.max(0, last),
    clock: state === "in" && st[last] === "1" ? String(q[last].tg || "") : "",
    quarters: state === "pre" ? [] : quarters,
  };
}

// ---- Βόλεϊ: Data Project (ΕΟΠΕ: eope-web, Volley League ανδρών: hvl-web), μέσω SignalR 2.
const DP = "https://dataprojectservicesignalr.azurewebsites.net/signalr";
const DP_HUB = "signalrlivehubfederations";
const PAOK = /P\.?\s?A\.?\s?O\.?\s?K|Π\.?Α\.?Ο\.?Κ/i;

async function dpCall(fed, list) {
  const h = { "User-Agent": "Mozilla/5.0 (PAOKalendar live)", Origin: `https://${fed}-web.dataproject.com`,
    Referer: `https://${fed}-web.dataproject.com/` };
  const cd = encodeURIComponent(JSON.stringify([{ name: DP_HUB }]));
  const neg = await getJson(`${DP}/negotiate?clientProtocol=2.1&connectionData=${cd}`, h);
  const q = `transport=longPolling&clientProtocol=2.1&connectionToken=${encodeURIComponent(neg.ConnectionToken)}&connectionData=${cd}`;
  await fetch(`${DP}/connect?${q}`, { headers: h });
  await fetch(`${DP}/start?${q}`, { headers: h });
  const body = "data=" + encodeURIComponent(JSON.stringify({ H: DP_HUB, M: "getLiveScoreListData_From_ES", A: [list, fed], I: 0 }));
  const r = await fetch(`${DP}/send?${q}`, {
    method: "POST", body, headers: { ...h, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8" },
  });
  const out = await r.json();
  fetch(`${DP}/abort?${q}`, { method: "POST", headers: h }).catch(() => {});
  return Array.isArray(out?.R) ? out.R : [];
}

async function dp(p) {
  if (!/^(eope|hvl)$/.test(p.fed || "")) throw new Error("λάθος ομοσπονδία");
  let list = p.id;
  if (!list) {
    // Χωρίς κωδικό αγώνα: οι αγώνες της ημέρας από τη σελίδα LIVE SCORE της διοργάνωσης.
    const r = await fetch(`https://${p.fed}-web.dataproject.com/MainLiveScore.aspx`, { headers: { "User-Agent": UA } });
    list = ((await r.text()).match(/id="HF_MatchesList" value="([^"]*)"/) || [])[1];
    if (!list) throw new Error("κανένας αγώνας σήμερα");
  }
  const rows = await dpCall(p.fed, list);
  const x = p.id ? rows.find((o) => String(o.ChampionshipMatchID) === p.id)
    : rows.find((o) => String(o.MatchDateTime || "").startsWith(p.day) && (PAOK.test(o.HomeEmpty) || PAOK.test(o.GuestEmpty)));
  if (!x) throw new Error("ο αγώνας δεν βρέθηκε στη Data Project");
  // Αν η Data Project έχει ανάποδα γηπεδούχο και φιλοξενούμενο από εμάς, γυρίζουμε τα σκορ.
  const flip = p.side && PAOK.test(x.HomeEmpty) !== (p.side === "h");
  const H = flip ? "Guest" : "Home", G = flip ? "Home" : "Guest";
  const state = stateOf(x.Status);
  const won = (num(x.WonSetHome) || 0) + (num(x.WonSetGuest) || 0);
  const sets = [];
  for (let i = 1; i <= 5; i++) {
    const a = num(x[`Set${i}${H}`]) || 0, b = num(x[`Set${i}${G}`]) || 0;
    if (i <= won || (state === "in" && i === won + 1) || a || b) sets.push({ home: a, away: b });
  }
  const cur = state === "in" ? sets[won] : null;
  return {
    state, home: num(x[`WonSet${H}`]) || 0, away: num(x[`WonSet${G}`]) || 0,
    quarter: state === "in" ? won + 1 : 0, done: won,
    clock: cur ? `${cur.home}-${cur.away}` : "", quarters: state === "pre" ? [] : sets.slice(0, state === "post" ? won : 5),
  };
}

// ---- Μπάσκετ: Genius Sports (FIBA LiveStats), όπως το esake.gr. Τον αγώνα της ημέρας τον βρίσκουμε
// στο widget της διοργάνωσης (κοντινοί αγώνες με κωδικούς), τα στοιχεία από το data.json του αγώνα.
const GS_WIDGET = "https://widget.wh.geniussports.com/widget//?";
const GS_DATA = "https://fibalivestats.dcd.shared.geniussports.com/data/";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const gsFound = {};  // «κλειδί|ημέρα» → κωδικός αγώνα

async function gsMatches(key) {
  const r = await fetch(GS_WIDGET + key, { headers: { "User-Agent": UA, Referer: "https://www.esake.gr/" } });
  const js = await r.text();
  const raw = (js.match(/var html = "([\s\S]*?)";\n/) || [])[1];
  if (!raw) throw new Error("άγνωστη μορφή widget");
  const html = JSON.parse(`"${raw}"`);
  return [...html.matchAll(/<li class="spls_lsmatch[^"]*">([\s\S]*?)<\/li>/g)].map(([, li]) => ({
    id: (li.match(/webcast\/\w+\/(\d+)/) || [])[1],
    status: ((li.match(/spls_matchstatus">([^<]*)/) || [])[1] || "").trim(),
    date: ((li.match(/spls_datefield">([^<]*)/) || [])[1] || "").trim(),
    teams: [...li.matchAll(/teamname">([^<]*)/g)].map((x) => x[1].trim()),
  })).filter((x) => x.id);
}

async function gs(p) {
  const d = new Date(`${p.day}T12:00:00Z`);
  const dayText = `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  const list = await gsMatches(p.key);
  let id = gsFound[`${p.key}|${p.day}`];
  let row = id && list.find((x) => x.id === id);
  if (!row) {
    // Οι αγώνες σε εξέλιξη δείχνουν περίοδο αντί για ημερομηνία· γι' αυτό μπαίνουν κι αυτοί.
    const today = new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Athens" });
    const cands = list.filter((x) => x.date === dayText || (p.day === today && /live/i.test(x.status)));
    for (const c of cands) {
      const j = await getJson(`${GS_DATA}${c.id}/data.json`).catch(() => null);
      if (j && (PAOK.test(j.tm?.["1"]?.name || "") || PAOK.test(j.tm?.["2"]?.name || ""))) { row = c; break; }
    }
    if (!row) throw new Error("ο αγώνας δεν βρέθηκε στη Genius Sports");
    gsFound[`${p.key}|${p.day}`] = row.id;
  }
  const j = (await getJson(`${GS_DATA}${row.id}/data.json`).catch(() => null)) || {};
  const pbp = Array.isArray(j.pbp) ? j.pbp : [];  // τα πιο πρόσφατα πρώτα
  const ended = pbp.some((a) => a.actionType === "game" && a.subType === "end");
  let state = /final/i.test(row.status) || ended ? "post" : /live/i.test(row.status) || pbp.length ? "in" : "pre";
  const flip = p.side && PAOK.test(j.tm?.["1"]?.name || "") !== (p.side === "h");
  const A = flip ? "2" : "1", B = flip ? "1" : "2";
  const period = num(j.period) || 0;
  // Η περίοδος τελείωσε μόνο αν η τελευταία ενέργεια είναι το τέλος *αυτής* της περιόδου: στην αρχή της
  // επόμενης, το data.json δείχνει ήδη τη νέα περίοδο ενώ η τελευταία ενέργεια είναι ακόμα το τέλος της
  // προηγούμενης (έτσι βγήκε «Τέλος 3ης» μόλις ξεκίνησε η 3η).
  const periodEnded = pbp[0]?.actionType === "period" && pbp[0]?.subType === "end" && num(pbp[0]?.period) === period;
  // Σκορ ανά περίοδο από το play-by-play: το τελευταίο σκορ κάθε περιόδου, μείον της προηγούμενης.
  const last = {};
  for (let i = pbp.length - 1; i >= 0; i--) {
    const a = pbp[i], n = num(a.period);
    if (n) last[n] = [num(a.s1) || 0, num(a.s2) || 0];
  }
  const quarters = [];
  let prev = [0, 0];
  for (let n = 1; n <= Math.max(4, period); n++) {
    const cur = last[n];
    quarters.push(cur ? { home: cur[A === "1" ? 0 : 1] - prev[A === "1" ? 0 : 1], away: cur[A === "1" ? 1 : 0] - prev[A === "1" ? 1 : 0] } : { home: "", away: "" });
    if (cur) prev = cur;
  }
  return {
    state, home: num(j.tm?.[A]?.score) ?? 0, away: num(j.tm?.[B]?.score) ?? 0,
    quarter: state === "in" ? period : 0,
    done: state === "post" ? period : periodEnded ? period : Math.max(0, period - 1),
    clock: state === "in" && !periodEnded ? String(j.clock || "") : "",
    quarters: state === "pre" ? [] : quarters,
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
  for (const k of ["src", "code", "cat", "gara", "tur", "gru", "a", "b", "fed", "id", "day", "side", "key"]) {
    if (q[k] == null) continue;
    if (!ID.test(String(q[k]))) return res.status(400).json({ error: `λάθος ${k}` });
    p[k] = String(q[k]);
  }
  const need = p.src === "koe" ? ["cat", "gara", "tur", "gru", "a", "b"] : p.src === "ea" ? ["code", "cat", "gara", "tur", "a", "b"]
    : p.src === "dp" ? ["fed", p.id ? "id" : "day"] : p.src === "gs" ? ["key", "day"] : null;
  if (!need || need.some((k) => !p[k])) return res.status(400).json({ error: "λάθος αγώνας" });
  const run = () => (p.src === "koe" ? koe(p) : p.src === "dp" ? dp(p) : p.src === "gs" ? gs(p) : ea(p));
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
