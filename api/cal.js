// Ένα ημερολόγιο .ics με όποια τμήματα διαλέξει κανείς, σε μία συνδρομή:
//   /paok.ics                                   όλα τα τμήματα, εντός και εκτός
//   /cal.ics?t=football,basketball-women&v=home  τα τμήματα που διάλεξε, μόνο εντός (v: home|away|all)
// Ενώνει τα αρχεία ανά τμήμα (football-home.ics κ.λπ.) του κλάδου «data», ώστε οι αγώνες να γράφονται
// ακριβώς όπως και εκεί (build_calendars.py). Τα κινητά ζητούν το ημερολόγιο λίγες φορές τη μέρα και
// το CDN κρατά κάθε συνδυασμό 5 λεπτά, άρα η function τρέχει ελάχιστα.
const RAW = "https://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/data/";

// Ίδια σειρά και ονόματα με το SECTIONS του build_calendars.py (το ελέγχει τεστ).
export const SECTIONS = [
  ["football", "Ποδόσφαιρο", "Ποδόσφαιρο"],
  ["football-women", "Ποδόσφαιρο Γυναικών", "Ποδόσφαιρο"],
  ["basketball", "Μπάσκετ", "Μπάσκετ"],
  ["basketball-women", "Μπάσκετ Γυναικών", "Μπάσκετ"],
  ["volley", "Βόλεϊ", "Βόλεϊ"],
  ["volley-women", "Βόλεϊ Γυναικών", "Βόλεϊ"],
  ["handball", "Χάντμπολ", "Χάντμπολ"],
  ["handball-women", "Χάντμπολ Γυναικών", "Χάντμπολ"],
  ["waterpolo", "Πόλο", "Πόλο"],
  ["waterpolo-women", "Πόλο Γυναικών", "Πόλο"],
  ["futsal", "Ποδόσφαιρο Σάλας", "Ποδόσφαιρο Σάλας"],
  ["basketball-amea", "Special Team", "Μπάσκετ"],
];
const KEYS = SECTIONS.map((s) => s[0]);
const SIDES = { home: ["home"], away: ["away"], all: ["home", "away"] };

// Τα τμήματα με τη σειρά του SECTIONS, χωρίς διπλά και άγνωστα: ίδια επιλογή, ίδιο ημερολόγιο.
export function parseKeys(t) {
  const want = String(t || "").split(",").map((s) => s.trim());
  if (want.includes("all")) return KEYS.slice();
  return KEYS.filter((k) => want.includes(k));
}

export function calName(keys, v) {
  let what;
  if (keys.length === KEYS.length) what = "Όλα τα τμήματα";
  else {
    const parts = [];
    for (const [key, name, sport] of SECTIONS) {
      if (!keys.includes(key)) continue;
      // Ανδρών & Γυναικών: μόνο τα δύο κανονικά τμήματα του αθλήματος (όχι π.χ. το Special Team).
      const peers = SECTIONS.filter((s) => s[2] === sport && !s[0].endsWith("-amea"));
      const both = !key.endsWith("-amea") && peers.every((s) => keys.includes(s[0]));
      const pair = peers.length > 1;
      if (both && pair) { if (!key.endsWith("-women")) parts.push(`${sport} Ανδρών & Γυναικών`); }
      else parts.push(name);
    }
    what = parts.join(" · ");  // χωρίς κόμμα: κάποιες εφαρμογές δείχνουν το «\,» στο όνομα
  }
  const side = v === "home" ? " – Εντός έδρας" : v === "away" ? " – Εκτός έδρας" : "";
  return `ΠΑΟΚ – ${what}${side}`;
}

const escapeText = (s) => s.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\n/g, "\\n");

// Γραμμές ως 75 bytes (RFC 5545), χωρίς να κόβεται χαρακτήρας στη μέση.
export function fold(line) {
  const out = [];
  let cur = "", bytes = 0;
  for (const ch of line) {
    const n = Buffer.byteLength(ch);
    if (bytes + n > (out.length ? 74 : 75)) { out.push(cur); cur = ""; bytes = 0; }
    cur += ch; bytes += n;
  }
  out.push(cur);
  return out.join("\r\n ");
}

const EVENT = /BEGIN:VEVENT\r?\n[\s\S]*?END:VEVENT\r?\n?/g;
const start = (ev) => (ev.match(/^DTSTART[^:]*:(\S+)/m) || [])[1] || "";

// Ενώνει αρχεία .ics σε ένα: η κεφαλίδα (με τη ζώνη ώρας) του πρώτου, με νέο όνομα, και όλοι οι αγώνες.
export function merge(files, name) {
  const head = files[0].split(/BEGIN:VEVENT|END:VCALENDAR/)[0]
    .replace(/^X-WR-CALNAME:.*\r?\n(?:[ \t].*\r?\n)*/m, fold(`X-WR-CALNAME:${escapeText(name)}`) + "\r\n");
  const events = files.flatMap((f) => (f.match(EVENT) || []).map((e) => e.replace(/\r?\n?$/, "").replace(/\r?\n/g, "\r\n") + "\r\n"));
  events.sort((a, b) => start(a).localeCompare(start(b)));
  return head + events.join("") + "END:VCALENDAR\r\n";
}

export default async function handler(req, res) {
  const keys = parseKeys(req.query?.t);
  const v = SIDES[req.query?.v] ? req.query.v : "all";
  if (!keys.length) {
    res.setHeader("Cache-Control", "no-store");
    return res.status(404).json({ error: "διάλεξε τουλάχιστον ένα τμήμα" });
  }
  try {
    const stamp = Math.floor(Date.now() / 60000);
    const files = await Promise.all(keys.flatMap((k) => SIDES[v].map(async (side) => {
      const r = await fetch(`${RAW}${k}-${side}.ics?t=${stamp}`, {
        headers: { "User-Agent": "PAOKalendar (+https://paokalendar.gr)" },
      });
      if (!r.ok) throw new Error(`GitHub ${r.status}: ${k}-${side}.ics`);
      return r.text();
    })));
    res.setHeader("Content-Type", "text/calendar; charset=utf-8");
    res.setHeader("Cache-Control", "public, max-age=0, s-maxage=300, stale-while-revalidate=600, stale-if-error=86400");
    return res.status(200).send(merge(files, calName(keys, v)));
  } catch (e) {
    res.setHeader("Cache-Control", "no-store");
    return res.status(502).json({ error: e.message });
  }
}
