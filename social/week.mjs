// Το πλάνο των social για τις επόμενες 7 μέρες, από το πρόγραμμα της εφαρμογής, με έτοιμες εικόνες.
//
//   node social/week.mjs [--date 2026-11-06] [--matches docs/matches.json] [--out out/social] [--prev dir]
//
// Τρέχει μετά από κάθε ενημέρωση των δεδομένων (social.yml), οπότε το πλάνο ακολουθεί τις αλλαγές
// στο πρόγραμμα και κοιτάζει μόνο μία εβδομάδα μπροστά. Βγάζει:
//   <out>/README.md   το πλάνο ανά μέρα, με τις εικόνες και τα κείμενα (φαίνεται στο GitHub)
//   <out>/plan.json   το ίδιο σε JSON
//   <out>/img/        οι εικόνες (και το JSON από το οποίο βγήκε η καθεμία)
//
// Οι κανόνες:
//   Μπλοκ: Σαββατοκύριακο = Σάββατο, Κυριακή και η Δευτέρα όταν έχει αγώνες (συνήθως η ίδια
//          αγωνιστική)· μεσοβδόμαδο = Τρίτη ως Παρασκευή. Μπλοκ χωρίς αγώνες δεν έχει post.
//   Post «Πρόγραμμα»: το βράδυ πριν από τον πρώτο αγώνα του μπλοκ (19:00, ή μετά τον τελευταίο αγώνα
//          εκείνης της μέρας). Carousel με μία κάρτα ανά μέρα.
//   Post «Αποτελέσματα»: το πρωί μετά τον τελευταίο αγώνα του μπλοκ (09:00). Ποτέ μαζί με πρόγραμμα.
//   Story «Σήμερα»: κάθε πρωί με αγώνα. Story «Αποτελέσματα ημέρας»: μετά τον τελευταίο αγώνα.
//   Reel: στη μέρα χωρίς άλλο post που απέχει περισσότερο από τα υπόλοιπα.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { chromium, render as renderFixtures } from "./fixtures.mjs";
import { render as renderResults } from "./results.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TZ = "Europe/Athens";
const RAW = "https://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/social";
const DATA_URL = "https://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/data/matches.json";

export const LABEL = {
  football: "Ποδόσφαιρο Ανδρών", "football-women": "Ποδόσφαιρο Γυναικών",
  basketball: "Μπάσκετ Ανδρών", "basketball-women": "Μπάσκετ Γυναικών",
  volley: "Βόλεϊ Ανδρών", "volley-women": "Βόλεϊ Γυναικών",
  handball: "Χάντμπολ Ανδρών", "handball-women": "Χάντμπολ Γυναικών",
  waterpolo: "Πόλο Ανδρών", "waterpolo-women": "Πόλο Γυναικών",
  futsal: "Φούτσαλ Ανδρών",
};
// Περίπου πόσο κρατά ένας αγώνας (λεπτά), για να ξέρουμε πότε έχει τελειώσει η μέρα.
const DURATION = { football: 115, basketball: 120, volley: 130, handball: 95, waterpolo: 90, futsal: 100 };
const HOME_VENUE = { football: "Τούμπα", basketball: "PAOK Sports Arena", volley: "PAOK Sports Arena",
  waterpolo: "Ποσειδώνιο" };
const DAYS = ["Κυριακή", "Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο"];
const DAYS_ACC = ["την Κυριακή", "τη Δευτέρα", "την Τρίτη", "την Τετάρτη", "την Πέμπτη", "την Παρασκευή", "το Σάββατο"];
const MAX_PER_CARD = 6;
const TAGS = "#ΠΑΟΚ #PAOK #PAOKalendar";
const SITE = "paokalendar.gr";
export const REELS = [
  ["Πώς βάζεις ειδοποίηση για έναν αγώνα", "Εγγραφή οθόνης: άνοιγμα εφαρμογής → αγώνας → «Ειδοποιήσεις» → «1 ώρα πριν» και «Live».",
    "Μάθε για κάθε γκολ πριν το δεις στην τηλεόραση ⚽🔔\nΣε 10'' από το κινητό σου, χωρίς λογαριασμό."],
  ["Όλα τα ματς στο ημερολόγιο του κινητού", "Εγγραφή οθόνης: «Ημερολόγια» → ένα τμήμα → προσθήκη → οι αγώνες στο ημερολόγιο του κινητού.",
    "Όλοι οι αγώνες του ΠΑΟΚ στο ημερολόγιο του κινητού σου 🗓️\nΕνημερώνεται μόνο του όταν αλλάζει μια ώρα."],
  ["Βαθμολογίες όλων των τμημάτων", "Εγγραφή οθόνης: μενού → ένα ερασιτεχνικό τμήμα → «Βαθμολογία», 2–3 τμήματα στη σειρά.",
    "Πού βρίσκεται ο ΠΑΟΚ σε κάθε άθλημα; 📊\nΒαθμολογίες για όλα τα τμήματα, ανδρών και γυναικών, σε μία εφαρμογή."],
  ["Live σκορ και ειδοποίηση στο γκολ", "Εγγραφή οθόνης την ώρα αγώνα: η σελίδα του αγώνα με το live σκορ και η ειδοποίηση που έρχεται.",
    "Live σκορ για όλα τα τμήματα, με ειδοποίηση σε κάθε γκολ και στο τελικό 🔴"],
  ["Βάλε την εφαρμογή στην αρχική οθόνη", `Εγγραφή οθόνης: ${SITE} στο Safari/Chrome → Κοινοποίηση → «Προσθήκη στην αρχική οθόνη».`,
    "Το PAOKalendar γίνεται εφαρμογή στο κινητό σου σε 5'' 📲\nΧωρίς App Store, χωρίς λογαριασμό."],
];

// ---------------------------------------------------------------- ημερομηνίες (ώρα Ελλάδας)

const fmt = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
function local(d) {
  const p = Object.fromEntries(fmt.formatToParts(d).map((x) => [x.type, x.value]));
  return { day: `${p.year}-${p.month}-${p.day}`, time: `${p.hour}:${p.minute}` };
}
const addDays = (day, n) => {
  const d = new Date(`${day}T12:00:00Z`); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10);
};
const weekday = (day) => new Date(`${day}T12:00:00Z`).getUTCDay();
const ddmm = (day) => `${day.slice(8, 10)}.${day.slice(5, 7)}`;
const minutes = (t) => +t.slice(0, 2) * 60 + +t.slice(3, 5);
const hhmm = (m) => `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
const roundUp = (m) => Math.ceil(m / 30) * 30;

// ---------------------------------------------------------------- αγώνες → γραμμές εικόνας

// Λέξεις που δεν χρειάζονται στην εικόνα (νομική μορφή, χορηγοί). Ό,τι θέλει κι άλλη διόρθωση
// (π.χ. γενική «ΝΟ ΧΑΝΙΩΝ» → «ΝΟ Χανίων») μπαίνει στο names.json.
const NOISE = new Set(["ΑΟ", "ΑΣ", "ΓΣ", "ΠΑΕ", "ΚΑΕ", "ΤΑΑ", "ΣΦΠ", "ΑΟΔ", "ΑΣΕ", "ΝΑΣ", "ΑΕΟ", "ΑΕΠ", "ΓΑΣ", "ΑΝΟ", "ΟΦΠΦ",
  "WFC", "FC", "BC", "VC", "QUALCO", "AFFIDEA"]);
export function cleanTeam(raw) {
  const words = raw.replace(/((?:\p{Lu}\.){2,})(?=\p{L}{2})/gu, "$1 ").split(/\s+/)
    .filter((w) => w && !/^(?:\p{Lu}\.)+\p{Lu}?\.?$/u.test(w) && !NOISE.has(w.replace(/\./g, "").toUpperCase()));
  return words.join(" ") || raw;
}
function cleanVenue(raw, names) {
  if (!raw) return "";
  if (names.venues[raw] !== undefined) return names.venues[raw];
  const v = raw.replace(/Κλειστό Γυμναστήριο|ΚΛΕΙΣΤΟ ΓΥΜΝΑΣΤΗΡΙΟ|Δημοτικό Στάδιο|ΔΗΜΟΤΙΚΟ ΣΤΑΔΙΟ|ΓΗΠ\.|ΔΗΜ\.|Stadium/gu, " ")
    .replace(/["«»].*$/u, "").replace(/\s+/g, " ").trim();
  return v.length <= 24 ? v : "";
}
function cleanTv(raw, names) {
  if (!raw) return "";
  if (names.tv[raw] !== undefined) return names.tv[raw];
  return raw.split(" / ")[0].replace(/\s+HD$/i, "").trim();
}

export function row(m, names) {
  const raw = m.paokHome ? m.away : m.home;
  const team = names.teams[`${m.section}:${raw}`] || {};
  const t = local(new Date(m.start));
  const r = {
    section: LABEL[m.section] || m.section,
    opponent: team.name || cleanTeam(raw),
    logo: team.logo ? path.join(HERE, "logos", team.logo) : (m.paokHome ? m.awayLogo : m.homeLogo) || "",
    venue: m.venue ? cleanVenue(m.venue, names) : m.paokHome ? HOME_VENUE[m.section] || "" : "",
    tv: cleanTv(m.tv, names),
    home: m.paokHome,
    time: m.timeKnown ? t.time : "",
  };
  // Η διοργάνωση φαίνεται μόνο όταν δεν είναι το πρωτάθλημα (Ευρώπη, κύπελλο, φιλικό).
  if (/Euro|Cup|Κύπελλ|Champions|Conference|EHF|CEV|Φιλικ/i.test(m.competition)) r.competition = m.competition;
  // Βόλεϊ: τα σετ κάτω από τον αντίπαλο στις εικόνες αποτελεσμάτων (π.χ. «25-21 · 23-25 · 25-19 · 25-22»).
  if (m.periods?.length && /^volley/.test(m.section) && m.score) {
    const sets = m.periods.map(([h, a]) => (m.paokHome ? `${h}-${a}` : `${a}-${h}`)).join(" · ");
    r.competition = r.competition ? `${r.competition} · ${sets}` : sets;
  }
  const s = /^(\d+)-(\d+)$/.exec(m.score || "");
  if (s) {
    const [h, a] = [+s[1], +s[2]];
    r.us = m.paokHome ? h : a; r.them = m.paokHome ? a : h;
  }
  return r;
}

// ---------------------------------------------------------------- το πλάνο

export function blockKey(day) {
  const w = weekday(day);
  if (w === 6) return { key: day, kind: "weekend" };
  if (w === 0) return { key: addDays(day, -1), kind: "weekend" };
  if (w === 1) return { key: addDays(day, -2), kind: "weekend" };
  return { key: addDays(day, 2 - w), kind: "midweek" };
}

export function plan(matches, today, { names = { teams: {}, venues: {}, tv: {} } } = {}) {
  // Και η χθεσινή μέρα: ό,τι δεν πρόλαβε να ανέβει (π.χ. το πρόγραμμα της Δευτέρας στις 22:00) κρατά τις
  // εικόνες του ως την επόμενη μέρα, αντί να σβηστούν τα μεσάνυχτα.
  const from = addDays(today, -1), to = addDays(today, 6);
  const byDay = new Map();
  for (const m of matches) {
    const { day } = local(new Date(m.start));
    if (day < addDays(today, -8) || day > addDays(today, 14)) continue;
    if (!byDay.has(day)) byDay.set(day, []);
    byDay.get(day).push(m);
  }
  for (const list of byDay.values()) list.sort((a, b) => a.start.localeCompare(b.start));
  const gameDays = [...byDay.keys()].sort();

  // Πότε τελειώνει ο τελευταίος αγώνας μιας μέρας (λεπτά από τα μεσάνυχτα), ή null.
  const dayEnd = (day) => {
    const list = byDay.get(day);
    if (!list) return null;
    return Math.max(...list.map((m) => minutes(local(new Date(m.start)).time) +
      (DURATION[m.section.replace("-women", "")] || 110)));
  };

  const blocks = new Map();
  for (const day of gameDays) {
    const b = blockKey(day);
    if (!blocks.has(b.key)) blocks.set(b.key, { ...b, days: [] });
    blocks.get(b.key).days.push(day);
  }

  const items = [];
  const card = (kind, day, list) => {
    const rows = list.map((m) => row(m, names));
    const chunks = [];
    for (let i = 0; i < rows.length; i += MAX_PER_CARD) chunks.push(rows.slice(i, i + MAX_PER_CARD));
    return chunks.map((matches, i) => ({ kind, day: DAYS[weekday(day)], date: ddmm(day),
      file: `${day}${chunks.length > 1 ? `-${i + 1}` : ""}`, matches }));
  };

  // Λίγοι αγώνες σε πολλές μέρες: μία κάρτα για όλο το μπλοκ (με τη μέρα σε κάθε αγώνα), αντί για
  // κάρτες με έναν αγώνα η καθεμία.
  const COMBINE_UP_TO = 4;
  const blockCards = (kind, b, pick) => {
    const per = b.days.map((d) => [d, pick(byDay.get(d))]).filter(([, l]) => l.length);
    const total = per.reduce((n, [, l]) => n + l.length, 0);
    if (per.length < 2 || total > COMBINE_UP_TO) return per.flatMap(([d, l]) => card(kind, d, l));
    const first = per[0][0], last = per.at(-1)[0];
    const matches = per.flatMap(([d, l]) => l.map((m) => ({ ...row(m, names), when: `${DAYS[weekday(d)].slice(0, 3)} ${ddmm(d)}` })));
    const date = first.slice(5, 7) === last.slice(5, 7) ? `${first.slice(8, 10)}–${ddmm(last)}` : `${ddmm(first)}–${ddmm(last)}`;
    return [{ kind, day: b.kind === "weekend" ? "Σαββατοκύριακο" : "Εβδομάδα", date, file: `${first}_${last}`, matches }];
  };

  for (const b of blocks.values()) {
    const first = b.days[0], last = b.days.at(-1);
    const all = b.days.flatMap((d) => byDay.get(d));
    const label = b.kind === "weekend" ? "του Σαββατοκύριακου" : "της εβδομάδας";
    // Πρόγραμμα: το βράδυ πριν.
    const pday = addDays(first, -1);
    if (pday >= from && pday <= to) {
      const end = dayEnd(pday);
      items.push({ type: "post", what: "schedule", day: pday, time: hhmm(Math.max(19 * 60, end ? roundUp(end + 20) : 0)),
        title: `Πρόγραμμα ${label}`, cards: blockCards("fixtures", b, (l) => l),
        caption: scheduleCaption(b, all, byDay, names) });
    }
    // Αποτελέσματα: το πρωί μετά.
    const rday = addDays(last, 1);
    if (rday >= from && rday <= to) {
      const done = all.filter((m) => /^\d+-\d+$/.test(m.score || ""));
      const missing = all.filter((m) => !done.includes(m));
      items.push({ type: "post", what: "results", day: rday, time: "09:00", title: `Αποτελέσματα ${label}`,
        cards: blockCards("results", b, (l) => l.filter((m) => done.includes(m))),
        caption: done.length ? resultsCaption(b, done, names) : "",
        missing: missing.map((m) => `${m.home} – ${m.away}`) });
    }
  }
  for (const day of gameDays) {
    if (day < from || day > to) continue;
    const list = byDay.get(day);
    const firstStart = minutes(local(new Date(list[0].start)).time);
    items.push({ type: "story", what: "today", day, time: firstStart < 10 * 60 ? "08:00" : "09:00",
      title: "Σήμερα παίζει", cards: card("fixtures", day, list).map((c) => ({ ...c, story: true })),
      note: `Sticker «Σύνδεσμος» → ${SITE}` });
    const done = list.filter((m) => /^\d+-\d+$/.test(m.score || ""));
    items.push({ type: "story", what: "dayResults", day, time: hhmm(roundUp(dayEnd(day) + 20)),
      title: "Αποτελέσματα ημέρας",
      cards: done.length ? card("results", day, done).map((c) => ({ ...c, story: true })) : [],
      missing: list.filter((m) => !done.includes(m)).map((m) => `${m.home} – ${m.away}`) });
  }

  // Reel: η μέρα χωρίς post που απέχει περισσότερο από τα άλλα post (μετράνε και όσα πέφτουν λίγο
  // μετά την εβδομάδα, π.χ. το πρόγραμμα της επόμενης Παρασκευής).
  const postDays = [...blocks.values()].flatMap((b) => [addDays(b.days[0], -1), addDays(b.days.at(-1), 1)])
    .filter((d) => d >= addDays(from, -3) && d <= addDays(to, 3));
  let best = null, bestGap = -1;
  for (let d = today; d <= to; d = addDays(d, 1)) {
    if (postDays.includes(d)) continue;
    // Καλύτερα μέρα χωρίς αγώνα: τις μέρες αγώνων έχει ήδη stories.
    const gap = (postDays.length ? Math.min(...postDays.map((p) => Math.abs(new Date(p) - new Date(d)) / 864e5)) : 3) -
      (byDay.has(d) ? 1.5 : 0);
    if (gap > bestGap) { best = d; bestGap = gap; }
  }
  if (best) {
    const week = Math.floor((new Date(`${best}T12:00:00Z`) - new Date("2026-11-09T12:00:00Z")) / (7 * 864e5));
    const [title, how, caption] = REELS[((week % REELS.length) + REELS.length) % REELS.length];
    const end = dayEnd(best);
    items.push({ type: "reel", what: "reel", day: best, time: hhmm(Math.max(20 * 60, end ? roundUp(end + 20) : 0)),
      title, how, caption: `${caption}\n\nΔωρεάν στο ${SITE} (link στο bio)\n\n${TAGS}`, cards: [] });
  }
  const order = { post: 0, reel: 1, story: 2 };
  items.sort((a, b) => a.day.localeCompare(b.day) || a.time.localeCompare(b.time) || order[a.type] - order[b.type]);
  return { today, from, to, items };
}

function scheduleCaption(b, all, byDay, names) {
  const sports = new Set(all.map((m) => m.section.replace("-women", "")));
  const head = b.kind === "weekend" ? "Το Σαββατοκύριακο του ΠΑΟΚ σε όλα τα τμήματα ⚪️⚫️" : "Η εβδομάδα του ΠΑΟΚ σε όλα τα τμήματα ⚪️⚫️";
  const span = b.days.length > 1 ? `από ${DAYS_ACC[weekday(b.days[0])].replace(/^(την|τη|το) /, "")} ως ${DAYS_ACC[weekday(b.days.at(-1))].replace(/^(την|τη|το) /, "")}` : DAYS_ACC[weekday(b.days[0])];
  const n = all.length;
  let line = `${n} ${n === 1 ? "αγώνας" : "αγώνες"}${sports.size > 1 ? ` σε ${sports.size} αθλήματα` : ""}, ${span}`;
  const big = all.find((m) => m.section === "football") || all.find((m) => m.section === "basketball");
  if (big && n > 1) {
    const d = local(new Date(big.start));
    const r = row(big, names);
    const pair = big.paokHome ? `ΠΑΟΚ–${r.opponent}` : `${r.opponent}–ΠΑΟΚ`;
    line += `, με το ${pair} ${DAYS_ACC[weekday(d.day)]}${big.timeKnown ? ` στις ${d.time}` : ""}`;
  }
  return `${head}\n${line}.\n\nΏρες, κανάλια και ειδοποιήσεις για κάθε αγώνα: ${SITE} (link στο bio)\n\n${TAGS}`;
}

function resultsCaption(b, done, names) {
  const rows = done.map((m) => row(m, names));
  const w = rows.filter((r) => r.us > r.them).length, l = rows.filter((r) => r.us < r.them).length;
  const d = rows.length - w - l;
  const head = b.kind === "weekend" ? "Τα αποτελέσματα του Σαββατοκύριακου ⚪️⚫️" : "Τα αποτελέσματα της εβδομάδας ⚪️⚫️";
  const parts = [w && `${w} ${w === 1 ? "νίκη" : "νίκες"}`, l && `${l} ${l === 1 ? "ήττα" : "ήττες"}`,
    d && `${d} ${d === 1 ? "ισοπαλία" : "ισοπαλίες"}`].filter(Boolean);
  return `${head}\n${parts.join(", ")} σε ${rows.length} ${rows.length === 1 ? "αγώνα" : "αγώνες"}.\n\n` +
    `Όλα τα σκορ και οι βαθμολογίες: ${SITE} (link στο bio)\n\n${TAGS}`;
}

// ---------------------------------------------------------------- εικόνες και README

const TYPE = { post: "📸 Post", story: "⭕ Story", reel: "🎬 Reel" };

export function readme(p) {
  const lines = [`# Social: ${ddmm(p.today)} – ${ddmm(p.to)}`, "",
    "Φτιάχνεται μόνο του μετά από κάθε ενημέρωση του προγράμματος (social.yml), οπότε δείχνει πάντα τις τελευταίες ώρες και αλλαγές. " +
    "Στο iPhone (Safari): πάτα μια εικόνα, κράτα το δάχτυλο πάνω της → «Προσθήκη στις Φωτογραφίες».", ""];
  let cur = "";
  for (const it of p.items) {
    if (it.day !== cur) {
      cur = it.day;
      lines.push(`## ${DAYS[weekday(it.day)]} ${ddmm(it.day)}${it.day === p.today ? " (σήμερα)" : ""}`, "");
    }
    lines.push(`### ${it.time} · ${TYPE[it.type]}: ${it.title}`, "");
    if (it.how) lines.push(it.how, "");
    if (it.note) lines.push(it.note, "");
    if (it.missing?.length) {
      lines.push(it.images?.length ? `Λείπει ακόμα το σκορ: ${it.missing.join(", ")}. Θα μπει μόλις έρθει.` :
        "Οι εικόνες θα βγουν μόλις έρθουν τα σκορ.", "");
    }
    // Το πάτημα ανοίγει σκέτη την εικόνα (raw), όπου στο iPhone κρατάς πατημένο → «Προσθήκη στις Φωτογραφίες».
    if (it.images?.length) lines.push(it.images.map((f) => `<a href="${RAW}/img/${f}"><img src="img/${f}" width="${it.type === "story" ? 160 : 216}"></a>`).join(" "), "");
    if (it.caption) lines.push("```", it.caption, "```", "");
  }
  return lines.join("\n");
}

async function main() {
  const args = Object.fromEntries(process.argv.slice(2).join(" ").split("--").filter(Boolean)
    .map((a) => a.trim().split(/\s+/)).map(([k, v]) => [k, v]));
  const today = args.date || local(new Date()).day;
  const out = path.resolve(args.out || "out/social");
  let prev = args.prev && path.resolve(args.prev);
  const src = args.matches || (fs.existsSync("docs/matches.json") ? "docs/matches.json" : DATA_URL);
  const data = /^https?:/.test(src) ? await (await fetch(src)).json() : JSON.parse(fs.readFileSync(src, "utf8"));
  const names = JSON.parse(fs.readFileSync(path.join(HERE, "names.json"), "utf8"));
  const p = plan(data.matches, today, { names });

  if (prev === out && fs.existsSync(out)) {   // ίδιος φάκελος: κρατάμε τις παλιές εικόνες στην άκρη
    fs.rmSync(`${out}.prev`, { recursive: true, force: true });
    fs.renameSync(out, `${out}.prev`);
    prev = `${out}.prev`;
  }
  fs.rmSync(out, { recursive: true, force: true });
  fs.mkdirSync(path.join(out, "img"), { recursive: true });
  let browser = null;
  for (const it of p.items) {
    it.images = [];
    for (const c of it.cards) {
      const kind = c.story ? "story" : "post";
      const spec = { day: c.day, date: c.date, file: c.file, matches: c.matches };
      const name = `${c.file}-${c.kind === "results" ? "apotelesmata-" : ""}${kind}.png`;
      const json = JSON.stringify(spec);
      const hash = crypto.createHash("sha1").update(json + fs.readFileSync(path.join(HERE, `${c.kind}.mjs`))).digest("hex").slice(0, 10);
      const target = path.join(out, "img", name);
      if (!fs.existsSync(target)) {
        const old = prev && path.join(prev, "img", name);
        if (old && fs.existsSync(old) && fs.existsSync(`${old}.hash`) && fs.readFileSync(`${old}.hash`, "utf8") === hash) {
          fs.copyFileSync(old, target);
        } else {
          browser ||= await (await chromium()).launch();
          const r = c.kind === "results" ? renderResults : renderFixtures;
          await r(spec, path.join(out, "img"), { browser, kinds: [kind] });
        }
        fs.writeFileSync(`${target}.hash`, hash);
      }
      it.images.push(name);
    }
    delete it.cards;
  }
  if (browser) await browser.close();
  if (prev?.endsWith(".prev")) fs.rmSync(prev, { recursive: true, force: true });
  fs.writeFileSync(path.join(out, "plan.json"), JSON.stringify(p, null, 1));
  fs.writeFileSync(path.join(out, "README.md"), readme(p));
  console.log(`${p.items.length} καταχωρίσεις, ${fs.readdirSync(path.join(out, "img")).filter((f) => f.endsWith(".png")).length} εικόνες → ${out}`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
