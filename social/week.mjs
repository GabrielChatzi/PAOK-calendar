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
//   Post «Αποτελέσματα»: το ίδιο βράδυ (30' μετά τον τελευταίο αγώνα) αν το μπλοκ τελειώνει ως τις 21:00,
//          αλλιώς το επόμενο πρωί 08:30. Ποτέ μαζί με πρόγραμμα.
//   Post «Πρόγραμμα»: 09:00 την πρώτη μέρα του μπλοκ (Τρίτη / Σάββατο), μετά τα αποτελέσματα του
//          προηγούμενου· το Σαββατοκύριακο Παρασκευή βράδυ όταν τα αποτελέσματα βγαίνουν τότε. Carousel.
//   Story «Σήμερα»: κάθε πρωί με αγώνα. Story «Αποτελέσματα ημέρας»: μετά τον τελευταίο αγώνα.
//   Ενδιάμεσα: Reel + post με θέμα, ένα ζευγάρι την εβδομάδα σε διαφορετικές μέρες (βλ. addPairs).
//   Grid (σκακιέρα): ⬛ / ⬜ εναλλάσσονται. Τα αποτελέσματα ενός μπλοκ πάντα πριν από το πρόγραμμα του επόμενου.
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
  futsal: "Φούτσαλ Ανδρών", "basketball-amea": "Μπάσκετ Special Team",
};
// Περίπου πόσο κρατά ένας αγώνας (λεπτά), για να ξέρουμε πότε έχει τελειώσει η μέρα.
const DURATION = { football: 115, basketball: 120, volley: 130, handball: 95, waterpolo: 90, futsal: 100 };
const HOME_VENUE = { football: "Τούμπα", basketball: "PAOK Sports Arena", volley: "PAOK Sports Arena",
  waterpolo: "Ποσειδώνιο" };
const DAYS = ["Κυριακή", "Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο"];
const DAYS_ACC = ["την Κυριακή", "τη Δευτέρα", "την Τρίτη", "την Τετάρτη", "την Πέμπτη", "την Παρασκευή", "το Σάββατο"];
const MAX_PER_CARD = 6;
const RESULTS_SAME_DAY = 21 * 60;   // ως τότε τελειωμένο μπλοκ: αποτελέσματα το ίδιο βράδυ
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
  // «Κλειστό «Κατσιμήδειο» Τρικάλων» → «Κατσιμήδειο Τρικάλων» (όχι σκέτο «Κλειστό»).
  const q = /[«"]([^»"]+)[»"]\s*(.*)$/u.exec(raw);
  if (q && /^(?:Κλειστό|Γήπεδο|Στάδιο|Γυμναστήριο|Κολυμβητήριο)?$/iu.test(v)) return `${q[1]} ${q[2]}`.trim().slice(0, 24);
  return v.length <= 24 ? v : "";
}
function cleanTv(raw, names) {
  if (!raw) return "";
  if (names.tv[raw] !== undefined) return names.tv[raw];
  return raw.split(" / ")[0].replace(/\s+HD$/i, "").trim();
}

// Ακαδημίες: «Ποδόσφαιρο Κ19», «Μπάσκετ Έφηβοι», «Βόλεϊ Κ18 Κοριτσιών» (από τα sections του matches.json).
export function academyLabels(sections = []) {
  const out = {};
  for (const s of sections) if (s.academy) out[s.key] = s.key === "football-b" ? s.name : `${s.sport} ${s.name}`;
  return out;
}

export function row(m, names) {
  const raw = m.paokHome ? m.away : m.home;
  const team = names.teams[`${m.section}:${raw}`] || {};
  const t = local(new Date(m.start));
  const r = {
    section: LABEL[m.section] || names.labels?.[m.section] || m.section,
    opponent: team.name || cleanTeam(raw),
    logo: team.logo ? path.join(HERE, "logos", team.logo) : (m.paokHome ? m.awayLogo : m.homeLogo) || "",
    venue: m.venue ? cleanVenue(m.venue, names) : m.paokHome ? HOME_VENUE[m.section] || "" : "",
    tv: cleanTv(m.tv, names),
    home: m.paokHome,
    time: m.timeKnown ? t.time : "",
  };
  // Η διοργάνωση φαίνεται μόνο όταν δεν είναι το πρωτάθλημα (Ευρώπη, κύπελλο, φιλικό).
  if (/Euro|Cup|Κύπελλ|Champions|Conference|EHF|CEV|Φιλικ/i.test(m.competition)) r.competition = m.competition;
  const s = /^(\d+)-(\d+)$/.exec(m.score || "");
  if (s) {
    const [h, a] = [+s[1], +s[2]];
    r.us = m.paokHome ? h : a; r.them = m.paokHome ? a : h;
  }
  return r;
}

// Μία γραμμή ανά αγώνα (τμήμα, αντίπαλος, μέρα, ώρα, γήπεδο): με αυτές το social_remind.py βλέπει τι
// άλλαξε στο πρόγραμμα αφού ανέβηκε το post.
export function matchLine(m, names) {
  const r = row(m, names), t = local(new Date(m.start));
  return `${r.section}: ${r.home ? `ΠΑΟΚ – ${r.opponent}` : `${r.opponent} – ΠΑΟΚ`}, ${DAYS[weekday(t.day)].slice(0, 3)} ${ddmm(t.day)}` +
    `${m.timeKnown ? ` ${t.time}` : ""}${r.venue ? `, ${r.venue}` : ""}`;
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
      (DURATION[m.section.split("-")[0]] || 110)));
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
    // Οι μέρες η μία κάτω από την άλλη, η καθεμία με τον τίτλο της (όπως στις κάρτες μίας μέρας).
    const first = per[0][0], last = per.at(-1)[0];
    const sections = per.map(([d, l]) => ({ day: DAYS[weekday(d)], date: ddmm(d), matches: l.map((m) => row(m, names)) }));
    return [{ kind, day: sections[0].day, date: sections[0].date, file: `${first}_${last}`, sections,
      matches: sections.flatMap((x) => x.matches) }];
  };

  // Αποτελέσματα: το ίδιο βράδυ, 30' μετά τον τελευταίο αγώνα, αν αυτός τελειώνει ως τις 21:00· αλλιώς
  // το επόμενο πρωί στις 08:30. Πρόγραμμα: το πρωί στις 09:00 της πρώτης μέρας του μπλοκ (Τρίτη /
  // Σάββατο), μετά τα αποτελέσματα του προηγούμενου. Το Σαββατοκύριακο ανεβαίνει από την Παρασκευή το
  // βράδυ, 30' μετά τα αποτελέσματα της εβδομάδας, όταν αυτά βγαίνουν Παρασκευή βράδυ.
  const resultsAt = (b) => {
    const last = b.days.at(-1), end = dayEnd(last);
    return end <= RESULTS_SAME_DAY ? [last, hhmm(roundUp(end + 30))] : [addDays(last, 1), "08:30"];
  };
  const scheduleAt = (b) => {
    const prev = [...blocks.values()].filter((x) => x.key < b.key).at(-1);
    if (b.kind === "weekend" && prev) {
      const [d, t] = resultsAt(prev);
      if (d === addDays(b.key, -1) && minutes(t) >= 12 * 60) return [d, hhmm(minutes(t) + 30)];
    }
    return [b.key, "09:00"];
  };

  for (const b of blocks.values()) {
    const first = b.days[0], last = b.days.at(-1);
    const all = b.days.flatMap((d) => byDay.get(d));
    const label = b.kind === "weekend" ? "του Σαββατοκύριακου" : "της εβδομάδας";
    const [pday, ptime] = scheduleAt(b);
    // Πρόγραμμα που έχει ήδη ανέβει (πριν από το πλάνο) αλλά το μπλοκ δεν έχει τελειώσει: μένει στο πλάνο ως
    // «posted», χωρίς εικόνες, για να φαίνονται οι αλλαγές (νέος αγώνας, άλλη ώρα) ως τον τελευταίο αγώνα.
    const posted = pday < from && pday >= addDays(today, -8) && last >= today;
    if ((pday >= from && pday <= to) || posted) {
      items.push({ type: "post", what: "schedule", block: b.key, track: `${b.kind}-${b.key}`, day: pday,
        ...(posted && { posted: true }),
        first: all[0].start,
        time: ptime,
        title: `Πρόγραμμα ${label}`, cards: blockCards("fixtures", b, (l) => l),
        until: all.at(-1).start, lines: all.map((m) => matchLine(m, names)),
        caption: scheduleCaption(b, all, byDay, names) });
    }
    const [rday, rtime] = resultsAt(b);
    if (rday >= from && rday <= to) {
      const done = all.filter((m) => /^\d+-\d+$/.test(m.score || ""));
      const missing = all.filter((m) => !done.includes(m));
      items.push({ type: "post", what: "results", block: b.key, day: rday, time: rtime, title: `Αποτελέσματα ${label}`,
        ends: `${last}T${hhmm(Math.min(dayEnd(last), 23 * 60 + 59))}`,
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

  const order = { post: 0, reel: 1, story: 2 };
  items.sort((a, b) => a.day.localeCompare(b.day) || a.time.localeCompare(b.time) || order[a.type] - order[b.type]);
  return { today, from, to, items };
}

// ---------------------------------------------------------------- ακαδημίες

// Ακαδημίες: μόνο το Σαββατοκύριακο (εκεί παίζουν σχεδόν όλες). Μπαίνουν ως κάρτες στο carousel του
// κανονικού προγράμματος/αποτελεσμάτων (mergeAcademy)· οι ώρες εδώ μετράνε μόνο όταν δεν υπάρχει κανονικό
// post: πρόγραμμα Σάββατο 09:00, αποτελέσματα όπως τα κανονικά (ίδιο βράδυ ως τις 21:00, αλλιώς 08:30).
// Αν αλλάξει κάτι αφού ανέβει το πρόγραμμα, το social_remind.py στέλνει ειδοποίηση (βλ. «lines»).
const SPORT_NAME = { football: "Ποδόσφαιρο", basketball: "Μπάσκετ", volley: "Βόλεϊ" };
const sportOf = (m) => m.section.split("-")[0];
// «21.11», «21–22.11», «30.11–01.12»
const span = (ds) => ds.length < 2 ? ddmm(ds[0]) : ds[0].slice(5, 7) === ds.at(-1).slice(5, 7)
  ? `${ds[0].slice(8, 10)}–${ddmm(ds.at(-1))}` : `${ddmm(ds[0])}–${ddmm(ds.at(-1))}`;
function teamLabel(m, names) {
  if (m.section === "football-b") return "Β' Ομάδα";
  return (names.labels?.[m.section] || m.section).replace(/^(Ποδόσφαιρο|Μπάσκετ|Βόλεϊ) /, "");
}

export function academyPlan(matches, today, { names = { teams: {}, venues: {}, tv: {} } } = {}) {
  const from = addDays(today, -1), to = addDays(today, 6);
  const byDay = new Map();
  for (const m of matches) {
    const { day } = local(new Date(m.start));
    if (blockKey(day).kind !== "weekend") continue;
    if (!byDay.has(day)) byDay.set(day, []);
    byDay.get(day).push(m);
  }
  // Ανά μέρα: πρώτα ποδόσφαιρο, μετά μπάσκετ, βόλεϊ· μέσα στο άθλημα με την ώρα.
  const SPORT = { football: 0, basketball: 1, volley: 2 };
  for (const list of byDay.values()) list.sort((a, b) => (SPORT[a.section.split("-")[0]] ?? 9) -
    (SPORT[b.section.split("-")[0]] ?? 9) || a.start.localeCompare(b.start));
  const blocks = new Map();
  for (const day of [...byDay.keys()].sort()) {
    const k = blockKey(day).key;
    if (!blocks.has(k)) blocks.set(k, []);
    blocks.get(k).push(day);
  }
  // Μία κάρτα ανά άθλημα (ποδόσφαιρο, μπάσκετ, βόλεϊ) και από κάτω οι μέρες, για να μη μοιάζει με το
  // κανονικό πρόγραμμα (εκεί μία κάρτα ανά μέρα). Στις γραμμές μόνο η ομάδα («Κ19», «Κ15 Κοριτσιών»).
  const cards = (kind, days, pick) => {
    const out = [];
    const sports = [...new Set(days.flatMap((d) => pick(byDay.get(d))).map(sportOf))]
      .sort((a, b) => (SPORT[a] ?? 9) - (SPORT[b] ?? 9));
    for (const sport of sports) {
      const rows = days.flatMap((day) => pick(byDay.get(day)).filter((m) => sportOf(m) === sport)
        .map((m) => ({ day, r: { ...row(m, names), section: teamLabel(m, names) } })));
      const chunks = [];
      for (let i = 0; i < rows.length; i += MAX_PER_CARD) chunks.push(rows.slice(i, i + MAX_PER_CARD));
      chunks.forEach((ch, i) => {
        const ds = [...new Set(ch.map((x) => x.day))];
        out.push({ kind, academy: true, kick: kind === "results" ? "ΑΚΑΔΗΜΙΕΣ · ΑΠΟΤΕΛΕΣΜΑΤΑ" : "ΑΚΑΔΗΜΙΕΣ · ΠΡΟΓΡΑΜΜΑ",
          day: SPORT_NAME[sport] || sport, date: span(ds),
          file: `akadimies-${days[0]}-${sport}${chunks.length > 1 ? `-${i + 1}` : ""}`,
          sections: ds.map((d) => ({ day: DAYS[weekday(d)], date: ddmm(d), matches: ch.filter((x) => x.day === d).map((x) => x.r) })),
          matches: ch.map((x) => x.r) });
      });
    }
    return out;
  };
  const items = [];
  for (const [key, days] of blocks) {
    const first = days[0], last = days.at(-1);
    const all = days.flatMap((d) => byDay.get(d));
    // Όπως το κανονικό πρόγραμμα: Σάββατο 09:00 (μέσα στο carousel του κανονικού, όταν υπάρχει).
    const pday = key;
    const posted = pday < from && last >= today;   // όπως στο plan(): ανέβηκε, παρακολουθούμε τις αλλαγές
    if ((pday >= from && pday <= to) || posted) {
      items.push({ type: "post", what: "academySchedule", block: key, track: `academy-${key}`, day: pday, time: "09:00",
        ...(posted && { posted: true }),
        first: all.map((m) => m.start).sort()[0],
        title: "Πρόγραμμα ακαδημιών", cards: cards("fixtures", days, (l) => l),
        until: all.map((m) => m.start).sort().at(-1), lines: all.map((m) => matchLine(m, names)),
        caption: academyCaption("schedule", all) });
    }
    const endMin = Math.max(...byDay.get(last).map((m) => minutes(local(new Date(m.start)).time) + (DURATION[m.section.split("-")[0]] || 110)));
    const [rday, rtime] = endMin <= RESULTS_SAME_DAY ? [last, hhmm(roundUp(endMin + 30))] : [addDays(last, 1), "08:30"];
    if (rday >= from && rday <= to) {
      const done = all.filter((m) => /^\d+-\d+$/.test(m.score || ""));
      items.push({ type: "post", what: "academyResults", block: key, day: rday, time: rtime, title: "Αποτελέσματα ακαδημιών",
        ends: `${last}T${hhmm(Math.min(endMin, 23 * 60 + 59))}`,
        cards: cards("results", days, (l) => l.filter((m) => done.includes(m))),
        caption: done.length ? academyCaption("results", done, names) : "",
        missing: all.filter((m) => !done.includes(m)).map((m) => `${m.home} – ${m.away}`) });
    }
  }
  return items;
}

// Οι ακαδημίες μπαίνουν ως επιπλέον κάρτες στο carousel του Σαββατοκύριακου (εξώφυλλο το κανονικό), ώστε
// στο grid να εναλλάσσονται πάντα ⬛ πρόγραμμα και ⬜ αποτελέσματα (σκακιέρα). Μόνο Σαββατοκύριακο χωρίς
// κανονικό post έχει δικό του post ακαδημιών, που τότε μετρά ως το πρόγραμμα/αποτελέσματα του μπλοκ.
// Τα σκορ των ακαδημιών που αργούν δεν κρατάνε πίσω το post (μπαίνουν όσα έχουν έρθει).
export function mergeAcademy(items, acad) {
  const out = [...items];
  for (const a of acad) {
    const what = a.what === "academySchedule" ? "schedule" : "results";
    const host = out.find((i) => i.type === "post" && i.what === what && i.block === a.block);
    if (!host) { out.push({ ...a, what, academy: true }); continue; }
    host.cards = [...host.cards, ...a.cards];
    host.academyCards = a.cards.length;
    if (what === "schedule") {
      host.lines = [...(host.lines || []), ...a.lines];
      host.until = [host.until, a.until].sort().at(-1);
      host.caption = host.caption.replace(/\n\n(Ώρες)/, `\nΣτο carousel και οι ${a.lines.length} αγώνες των ακαδημιών 👶⚪️⚫️\n\n$1`);
    } else {
      host.ends = [host.ends, a.ends].sort().at(-1);
      if (a.cards.length) host.caption = (host.caption || a.caption).replace(/\n\n(Όλα τα σκορ)/, "\nΣτο carousel και τα αποτελέσματα των ακαδημιών 👏\n\n$1");
      if (a.missing?.length) host.note = `Ακαδημίες χωρίς σκορ ακόμα: ${a.missing.length}`;
    }
  }
  return out;
}

const at = (it) => `${it.day}T${it.time}`;
const plus = (day, time, m) => { const t = minutes(time) + m; return t >= 24 * 60 ? [addDays(day, 1), hhmm(t - 24 * 60)] : [day, hhmm(t)]; };

// Σκακιέρα στο grid: τα post πρέπει να εναλλάσσονται ⬛ πρόγραμμα / ⬜ αποτελέσματα. Όταν δύο ίδια πέφτουν
// στη σειρά, φέρνουμε νωρίτερα το επόμενο post του άλλου χρώματος: αποτελέσματα αμέσως μόλις τελειώσει το μπλοκ
// τους (και το πρόγραμμα 30' μετά, με «after» για να μην έρθει η υπενθύμιση πριν από αυτά), πρόγραμμα αμέσως
// μετά τα αποτελέσματα. Αλλιώς σημείωση «δύο ίδια στη σειρά».
export function gridOrder(items, before = null) {
  // before: το τελευταίο post που έχει ήδη ανέβει ({day, time, what}), για να συνεχίσει η εναλλαγή.
  const lead = before && { ...before, type: "post", lead: true };
  // Τα ενδιάμεσα (addPairs) μετρούν με το χρώμα τους και δεν μετακινούνται.
  for (const i of items) if (i.extra) { i.what = i.grid === "⬛" ? "schedule" : "results"; i.pin = true; }
  // Το Reel μετρά στο grid με το χρώμα του εξωφύλλου του (what), αλλά δεν μετακινείται.
  const posts = () => [...(lead ? [lead] : []), ...items.filter((i) => (i.type === "post" || i.type === "reel") && !i.posted)]
    .sort((a, b) => at(a).localeCompare(at(b)));
  for (let guard = 0; guard < 10; guard++) {
    const ps = posts();
    const i = ps.findIndex((p, k) => k > 0 && p.what === ps[k - 1].what);
    if (i < 0) break;
    const cur = ps[i], prev = ps[i - 1];
    if (cur.lead || cur.type === "reel" || cur.pin) { if (!cur.lead) cur.note = [cur.note, "⚠️ Δύο ίδια χρώματα στη σειρά στο grid"].filter(Boolean).join(" · "); break; }
    const j = ps.findIndex((p, k) => k > i && p.what !== cur.what && p.type !== "reel" && !p.pin);
    const other = j > 0 ? ps[j] : null;
    let fixed = false;
    if (other && cur.what === "schedule" && other.ends && other.ends <= at(cur)) {
      [other.day, other.time] = [cur.day, cur.time];
      [cur.day, cur.time] = plus(cur.day, cur.time, 30);
      cur.after = `${other.day}-${other.time.replace(":", "")}-${other.what}`;
      fixed = true;
    } else if (other && cur.what === "results") {
      const [d, t] = plus(prev.day, prev.time, 30);
      if (`${d}T${t}` < at(cur)) {
        [other.day, other.time] = [d, t];
        other.after = `${prev.day}-${prev.time.replace(":", "")}-${prev.what}`;
        fixed = true;
      }
    }
    if (!fixed) { cur.note = [cur.note, "⚠️ Δύο ίδια χρώματα στη σειρά στο grid"].filter(Boolean).join(" · "); break; }
  }
  for (const p of items) {
    if (p.extra) { p.what = "extra"; delete p.pin; continue; }
    if (p.type === "post" || (p.type === "reel" && p.what)) p.grid = p.what === "schedule" ? "⬛" : "⬜";
  }
  return items;
}

// Ενδιάμεσα: κάθε εβδομάδα ένα ζευγάρι Reel + post με θέμα, σε διαφορετικές μέρες, στο κενό ανάμεσα σε
// δύο post διαφορετικού χρώματος, ώστε να κρατά η σκακιέρα (μετά από ⬛ πρώτα ⬜ και μετά ⬛, μετά από ⬜
// ανάποδα). Κανονικά Τετάρτη–Πέμπτη, ανάμεσα στο ⬛ πρόγραμμα και τα ⬜ αποτελέσματα της εβδομάδας· όταν η
// εβδομάδα κλείνει νωρίς, Πέμπτη–Παρασκευή μετά τα αποτελέσματα. Το Reel είναι ⬜ τις ζυγές εβδομάδες
// (από 30.11) και ⬛ τις μονές, ανεξάρτητα από το θέμα του post.
export const THEMES = [
  ["Βαθμολογίες", "Οι βαθμολογίες όλων των τμημάτων που παίζουν σε πρωτάθλημα, μία κάρτα ανά τμήμα.",
    "Πού βρίσκεται ο ΠΑΟΚ σε κάθε άθλημα; 📊"],
  ["Πού θα τους δεις", "Τα κανάλια όλων των αγώνων του Σαββατοκύριακου.",
    "Όλα τα ματς του Σαββατοκύριακου και πού θα τα δεις 📺"],
  ["Φόρμα", "Τα τελευταία 5 αποτελέσματα κάθε τμήματος (Ν-Ι-Η).",
    "Η φόρμα του ΠΑΟΚ σε όλα τα τμήματα 📈"],
  ["Το ματς της εβδομάδας", "Ο μεγάλος αγώνας της εβδομάδας: αντίπαλος, ώρα, κανάλι, γήπεδο.",
    "Το ματς της εβδομάδας 🔥"],
  ["Σκόρερ", "Οι πρώτοι σκόρερ κάθε τμήματος.",
    "Οι σκόρερ του ΠΑΟΚ σε όλα τα τμήματα ⚽🏀🤾"],
  ["Σαν σήμερα", "Ένας τίτλος ή ένας αγώνας από το αρχείο των σεζόν.",
    "Σαν σήμερα στην ιστορία του ΠΑΟΚ 🏆"],
];
const MONTHLY = ["Ο μήνας του ΠΑΟΚ", "Απολογισμός του μήνα που πέρασε: νίκες, ισοπαλίες, ήττες σε όλα τα τμήματα.",
  "Ο μήνας του ΠΑΟΚ σε όλα τα τμήματα 🗓️"];
const PAIR_EPOCH = "2026-11-30";   // Δευτέρα· εβδομάδα 0
const weekOf = (day) => Math.floor((new Date(`${day}T12:00:00Z`) - new Date(`${PAIR_EPOCH}T12:00:00Z`)) / (7 * 864e5));
const monday = (day) => addDays(day, -((weekday(day) + 6) % 7));
// Η πρώτη εβδομάδα του μήνα (η Δευτέρα της πέφτει 1–7) έχει απολογισμό· το θέμα της πάει στην επόμενη.
const isMonthly = (mon) => +mon.slice(8, 10) <= 7;
export function themeOf(mon) {
  if (isMonthly(mon)) return MONTHLY;
  let n = 0;
  for (let d = PAIR_EPOCH; d < mon; d = addDays(d, 7)) if (!isMonthly(d)) n++;
  return THEMES[((n % THEMES.length) + THEMES.length) % THEMES.length];
}

export function addPairs(items, lead, { today, to, now, gameDays = new Set(), prev = [], keptOnly = false } = {}) {
  const color = (i) => i.grid || (i.what === "schedule" ? "⬛" : "⬜");
  const other = (c) => c === "⬛" ? "⬜" : "⬛";
  const slot = (d) => [d, gameDays.has(d) ? "13:00" : "19:00"];
  const out = [];
  for (let mon = monday(today); mon <= to; mon = addDays(mon, 7)) {
    const wk = weekOf(mon);
    const reelColor = wk % 2 === 0 ? "⬜" : "⬛";
    const [title, how, line] = themeOf(mon);
    const [rTitle, rHow, rCap] = REELS[((wk % REELS.length) + REELS.length) % REELS.length];
    const make = (day, time, c) => c === reelColor
      ? { type: "reel", what: "extra", extra: true, week: mon, day, time, grid: c, title: rTitle, how: rHow,
        caption: `${rCap}\n\nΔωρεάν στο ${SITE} (link στο bio)\n\n${TAGS}`, cards: [] }
      : { type: "post", what: "extra", extra: true, week: mon, day, time, grid: c, title, how,
        caption: `${line}\n\nΌλα σε μία εφαρμογή: ${SITE} (link στο bio)\n\n${TAGS}`, cards: [] };
    // Ό,τι αποφασίστηκε σε προηγούμενο τρέξιμο μένει ίδιο (για να μην αλλάξει μέρα ή χρώμα στη μέση).
    const old = prev.filter((i) => i.extra && i.week === mon);
    if (old.length === 2) {
      for (const o of old) out.push({ ...make(o.day, o.time, o.grid), ...(`${o.day}T${o.time}` <= now && { posted: true }) });
      continue;
    }
    // Αποφασίζουμε μόνο όταν όλη η εβδομάδα (ως την Παρασκευή) είναι μέσα στο πλάνο, για να φαίνονται τα
    // αποτελέσματα της εβδομάδας πριν διαλέξουμε μέρες.
    if (keptOnly || addDays(mon, 4) > to) continue;
    const seq = [...(lead ? [lead] : []), ...items.filter((i) => (i.type === "post" || i.type === "reel") && !i.posted)]
      .map((i) => ({ at: at(i), c: color(i) })).sort((a, b) => a.at.localeCompare(b.at));
    const cands = [[2, 3], [3, 4], [2, 4], [1, 3], [1, 2]].map(([a, b]) => [slot(addDays(mon, a)), slot(addDays(mon, b))]);
    for (const [[d1, t1], [d2, t2]] of cands) {
      const s1 = `${d1}T${t1}`, s2 = `${d2}T${t2}`;
      if (d1 < today || s1 <= now || d2 > to) continue;
      if (seq.some((x) => x.at > s1 && x.at < s2)) continue;
      const P = seq.filter((x) => x.at <= s1).at(-1), N = seq.find((x) => x.at >= s2);
      if (P && N && P.c === N.c) continue;
      const c1 = P ? other(P.c) : N ? N.c : "⬛";
      out.push(make(d1, t1, c1), make(d2, t2, other(c1)));
      break;
    }
  }
  for (const e of out) if (e.type === "reel") e.note = `Εξώφυλλο ${e.grid === "⬛" ? "⬛ σκούρο" : "⬜ ανοιχτό"}, για να κρατήσει η σκακιέρα στο grid.`;
    else e.note = `${e.grid === "⬛" ? "⬛ Σκούρο" : "⬜ Ανοιχτό"} σχέδιο. Η εικόνα δεν βγαίνει ακόμα αυτόματα.`;
  return out;
}

// Αλλαγές μετά την ανάρτηση του προγράμματος: νέος αγώνας (π.χ. αναβληθείς που ανακοινώθηκε την
// τελευταία στιγμή), άλλη ώρα/μέρα/γήπεδο ή αγώνας που βγήκε. Οι γραμμές του προγράμματος όπως ήταν όταν
// ανέβηκε («sentLines») κρατιούνται από το προηγούμενο plan.json· για κάθε διαφορά βγαίνει story
// «Αλλαγή προγράμματος» με τους αγώνες που μπήκαν ή άλλαξαν (όχι post, για να μη χαλάσει η σκακιέρα).
// now: «YYYY-MM-DDTHH:MM» ώρα Ελλάδας.
export function changeStories(items, prev = [], now, matches = [], names = { teams: {}, venues: {}, tv: {} }) {
  const out = [];
  const nowDate = new Date(`${now}:00${offset(now)}`);
  const byLine = new Map(matches.map((m) => [matchLine(m, names), m]));
  for (const it of items) {
    if (it.type !== "post" || it.what !== "schedule" || !it.track || !it.lines) continue;
    const old = prev.find((p) => p.type === "post" && p.what === "schedule" && p.track === it.track);
    // Ανέβηκε; Όταν έχει περάσει η ώρα του και η υπενθύμιση δεν περιμένει κάτι άλλο (τα σκορ του, ή τα
    // αποτελέσματα που πρέπει να μπουν πρώτα στο grid, «after»). Από εκεί κρατάμε τις γραμμές του.
    const dep = it.after && items.find((x) => `${x.day}-${x.time.replace(":", "")}-${x.what}` === it.after);
    const up = it.posted || (at(it) <= now && !it.missing?.length && !dep?.missing?.length);
    if (!up && !old?.sentLines) continue;
    it.sentLines = old?.sentLines || it.lines;
    if (!it.until || new Date(it.until) <= nowDate) continue;
    const added = it.lines.filter((l) => !it.sentLines.includes(l));
    const gone = it.sentLines.filter((l) => !it.lines.includes(l));
    if (!added.length && !gone.length) continue;
    const sig = crypto.createHash("sha1").update(JSON.stringify([added, gone])).digest("hex").slice(0, 8);
    const was = prev.find((p) => p.what === "change" && p.track === it.track && p.sig === sig);
    const [day, time] = was ? [was.day, was.time] : now.split("T");
    const ms = added.map((l) => byLine.get(l)).filter(Boolean).sort((a, b) => a.start.localeCompare(b.start));
    const days = [...new Set(ms.map((m) => local(new Date(m.start)).day))];
    const cards = days.flatMap((d) => {
      const rows = ms.filter((m) => local(new Date(m.start)).day === d).map((m) => row(m, names));
      const chunks = [];
      for (let i = 0; i < rows.length; i += MAX_PER_CARD) chunks.push(rows.slice(i, i + MAX_PER_CARD));
      return chunks.map((matches, i) => ({ kind: "fixtures", story: true, kick: "ΑΛΛΑΓΗ ΠΡΟΓΡΑΜΜΑΤΟΣ",
        day: DAYS[weekday(d)], date: ddmm(d), file: `allagi-${sig}-${d}${chunks.length > 1 ? `-${i + 1}` : ""}`, matches }));
    });
    // Ίδιος αγώνας με άλλη ώρα: «Άλλαξε», αλλιώς «Νέος» / «Βγήκε».
    const what = (l) => l.split(",")[0];
    const changed = added.filter((l) => gone.some((g) => what(g) === what(l)));
    const parts = [...changed.map((l) => `Άλλαξε: ${l}`),
      ...added.filter((l) => !changed.includes(l)).map((l) => `Νέος: ${l}`),
      ...gone.filter((g) => !added.some((l) => what(l) === what(g))).map((g) => `Βγήκε: ${g}`)];
    out.push({ type: "story", what: "change", track: it.track, sig, day, time, title: "Αλλαγή προγράμματος",
      cards, added, gone,
      note: `${parts.join(" · ")} · Sticker «Σύνδεσμος» → ${SITE}. Αν θέλεις, πρόσθεσε και στο post τη νέα εικόνα (επεξεργασία carousel).` });
  }
  return out;
}
// Η διαφορά ώρας της Ελλάδας μια συγκεκριμένη ώρα («+02:00» ή «+03:00»).
function offset(t) {
  const d = new Date(`${t}:00Z`);
  const l = local(d);
  const diff = (new Date(`${l.day}T${l.time}:00Z`) - d) / 36e5;
  return `+0${diff}:00`;
}

function academyCaption(what, list, names) {
  const sports = new Set(list.map((m) => m.section.split("-")[0]));
  const n = list.length;
  const tail = "\n\nΤο παιδί σου παίζει στις ακαδημίες του ΠΑΟΚ; Βάλε τους αγώνες της ομάδας του στο ημερολόγιο " +
    `του κινητού, με ειδοποιήσεις και βαθμολογία: ${SITE} → Ακαδημίες (link στο bio)\n\n#ΠΑΟΚ #PAOK #PAOKAcademy #PAOKalendar`;
  if (what === "schedule") {
    return `Οι ακαδημίες του ΠΑΟΚ το Σαββατοκύριακο ⚪️⚫️\n${n} ${n === 1 ? "αγώνας" : "αγώνες"}` +
      `${sports.size > 1 ? ` σε ${sports.size} αθλήματα` : ""}, από την Β' ομάδα ως τα μικρά τμήματα.${tail}`;
  }
  const rows = list.map((m) => row(m, names));
  const w = rows.filter((r) => r.us > r.them).length;
  return `Τα αποτελέσματα των ακαδημιών ⚪️⚫️\n${w} ${w === 1 ? "νίκη" : "νίκες"} σε ${n} ${n === 1 ? "αγώνα" : "αγώνες"}. ` +
    `Μπράβο σε όλα τα παιδιά! 👏${tail}`;
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
  for (const it of p.items.filter((i) => !i.posted || (i.day === p.today && i.images?.length))) {
    if (it.day !== cur) {
      cur = it.day;
      lines.push(`## ${DAYS[weekday(it.day)]} ${ddmm(it.day)}${it.day === p.today ? " (σήμερα)" : ""}`, "");
    }
    lines.push(`### ${it.time} · ${TYPE[it.type]}${it.grid ? ` ${it.grid}` : ""}: ${it.title}`, "");
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

// Όλο το πλάνο της εβδομάδας με τη σκακιέρα του grid. Το τελευταίο post που ανέβηκε (από όπου συνεχίζει
// η εναλλαγή): --last, αλλιώς το τελευταίο post ή Reel του προηγούμενου πλάνου που έχει περάσει η ώρα του,
// αλλιώς το πλάνο της προηγούμενης εβδομάδας. Ό,τι έχει περάσει η ώρα του θεωρείται ότι ανέβηκε.
export function weekGrid(main, acad, today, now, { names, prevItems = [], last = null } = {}) {
  const gameDays = new Set(main.map((m) => local(new Date(m.start)).day));
  const p = plan(main, today, { names });
  const grid = (i) => (i.type === "post" || i.type === "reel") && i.day && i.time;
  const ac = academyPlan(acad, today, { names });
  // Από πού συνεχίζει η σκακιέρα: το πιο πρόσφατο από το --last (ή social/grid.json), το τελευταίο post ή Reel
  // του προηγούμενου πλάνου που έχει περάσει η ώρα του, και ό,τι του τωρινού πλάνου έχει περάσει η ώρα του.
  const asPost = (a) => ({ ...a, type: "post", what: a.what === "academySchedule" ? "schedule" : "results" });
  const cands = [last,
    ...prevItems.filter((i) => grid(i) && (i.what === "schedule" || i.what === "results") && at(i) <= now),
    // Τα ενδιάμεσα (Reel + post) μετρούν με το χρώμα τους.
    ...prevItems.filter((i) => i.extra && at(i) <= now).map((i) => ({ ...i, what: i.grid === "⬛" ? "schedule" : "results" })),
    ...[...p.items.filter((i) => i.type === "post"), ...ac.map(asPost)].filter((i) => at(i) <= now)].filter(Boolean);
  let lead = cands.sort((x, y) => at(x).localeCompare(at(y))).at(-1);
  lead &&= { day: lead.day, time: lead.time, what: lead.what };
  if (!lead) {
    const past = mergeAcademy(plan(main, addDays(today, -7), { names }).items, academyPlan(acad, addDays(today, -7), { names }))
      .filter((i) => i.type === "post" && i.day < p.from).sort((a, b) => at(a).localeCompare(at(b))).at(-1);
    if (past) lead = { day: past.day, time: past.time, what: past.what };
  }
  const gone = (i) => grid(i) && lead && at(i) <= at(lead);
  for (const i of p.items) if (i.type === "post" && gone(i)) i.posted = true;
  for (const a of ac) if (gone(a)) a.posted = true;
  const opts = { today, to: p.to, now, gameDays, prev: prevItems };
  const merged = mergeAcademy(p.items, ac.filter((a) => !a.posted || a.what === "academySchedule"));
  const kept = addPairs(merged, lead, { ...opts, keptOnly: true });   // ζευγάρια που έχουν ήδη αποφασιστεί
  p.items = gridOrder([...merged, ...kept], lead);
  p.items.push(...addPairs(p.items, lead, { ...opts, prev: [] }).filter((e) => !kept.some((k) => k.week === e.week)));
  p.items = p.items.filter((i) => !(i.type === "post" && i.posted && i.what === "results"));
  p.lead = lead;
  return p;
}

async function main() {
  const args = Object.fromEntries(process.argv.slice(2).join(" ").split("--").filter(Boolean)
    .map((a) => a.trim().split(/\s+/)).map(([k, v]) => [k, v]));
  const today = args.date || local(new Date()).day;
  const out = path.resolve(args.out || "out/social");
  let prev = args.prev && path.resolve(args.prev);
  // Το προηγούμενο πλάνο: από εκεί οι γραμμές του προγράμματος όπως ήταν όταν ανέβηκε (changeStories).
  const prevItems = (() => { try { return JSON.parse(fs.readFileSync(path.join(prev || out, "plan.json"), "utf8")).items || []; } catch { return []; } })();
  const src = args.matches || (fs.existsSync("docs/matches.json") ? "docs/matches.json" : DATA_URL);
  const data = /^https?:/.test(src) ? await (await fetch(src)).json() : JSON.parse(fs.readFileSync(src, "utf8"));
  const names = JSON.parse(fs.readFileSync(path.join(HERE, "names.json"), "utf8"));
  // Β' ομάδα και ακαδημίες: δικά τους post (academyPlan), όχι μέσα στο κανονικό πρόγραμμα.
  const academy = new Set((data.sections || []).filter((s) => s.academy).map((s) => s.key));
  names.labels = academyLabels(data.sections);
  const main = data.matches.filter((m) => !academy.has(m.section)), acad = data.matches.filter((m) => academy.has(m.section));
  const n = local(new Date());
  const now = args.date && args.date !== n.day ? `${today}T12:00` : `${n.day}T${n.time}`;
  // --last «2026-11-24T19:30 schedule»: το τελευταίο post που ανέβηκε στο grid, όταν διαφέρει από το πλάνο.
  const pick = (v) => v && { day: v.slice(0, 10), time: v.slice(11, 16) };
  // social/grid.json: {"last": "2026-11-24T19:30 schedule"}, για όταν τα post στο Instagram ανέβηκαν αλλιώς
  // από το πλάνο (το --last υπερισχύει).
  const conf = (() => { try { return JSON.parse(fs.readFileSync(path.join(HERE, "grid.json"), "utf8")); } catch { return {}; } })();
  if (!args.last && conf.last) { args.last = conf.last.split(" ")[0]; process.argv.push("--last", ...conf.last.split(" ")); }
  const last = args.last && { ...pick(args.last), what: process.argv.join(" ").match(/--last\s+\S+\s+(schedule|results)/)?.[1] || "schedule" };
  const p = weekGrid(main, acad, today, now, { names, prevItems, last });
  p.items.push(...changeStories(p.items, prevItems, now, data.matches, names));
  // Έχει ήδη ανέβει: μόνο για τις αλλαγές. Όσα πέρασε η ώρα τους σήμερα κρατούν τις εικόνες τους, γιατί το
  // «πέρασε η ώρα» δεν σημαίνει ότι ανέβηκαν (π.χ. ενημέρωση στις 20:07 για post των 20:00).
  for (const it of p.items) if (it.posted && it.day !== today) it.cards = [];
  const order = { post: 0, reel: 1, story: 2 };
  p.items.sort((a, b) => a.day.localeCompare(b.day) || a.time.localeCompare(b.time) || order[a.type] - order[b.type]);

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
      const spec = { day: c.day, date: c.date, file: c.file, matches: c.matches, ...(c.sections && { sections: c.sections }),
        ...(c.academy && { academy: true }),
        ...(c.kick && { kick: c.kick }) };
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
