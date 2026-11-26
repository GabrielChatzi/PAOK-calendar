// Οι καθαρές διευθύνσεις (/podosfairo, /programma, /paok-aris-<nt> κ.λπ., βλ. docs/seo.js και vercel.json).
//
// Δίνει την ίδια σελίδα (docs/index.html) με δικό της τίτλο, περιγραφή, canonical, εικόνα κοινοποίησης
// και δομημένα δεδομένα (schema.org), και με το πρόγραμμα ήδη γραμμένο μέσα στο <main>. Έτσι η Google
// (και οι προεπισκοπήσεις συνδέσμων σε Facebook, Instagram, Viber) βλέπουν κάθε σελίδα χωριστά.
// Όταν ανοίξει στον browser, η εφαρμογή μετατρέπει τη διεύθυνση στην αντίστοιχη #/... και δείχνει τα δικά της.
import { SITE, loadSeo, loadShell, loadMatches, esc } from "./_seo.js";

const PAGE_META = {
  programma: ["Πρόγραμμα αγώνων ΠΑΟΚ σε όλα τα τμήματα – PAOKalendar",
    "Όλοι οι επόμενοι αγώνες του ΠΑΟΚ σε ποδόσφαιρο, μπάσκετ, βόλεϊ, χάντμπολ, πόλο και φούτσαλ, ανδρών και γυναικών: μέρα, ώρα, γήπεδο και κανάλι."],
  athlimata: ["Όλα τα τμήματα του ΠΑΟΚ – PAOKalendar",
    "Ομαδικά και ατομικά αθλήματα και ακαδημίες του ΠΑΟΚ: πρόγραμμα, αποτελέσματα και βαθμολογίες για κάθε τμήμα."],
  tropaia: ["Τρόπαια του ΠΑΟΚ σε όλα τα τμήματα – PAOKalendar",
    "Πρωταθλήματα, κύπελλα και διακρίσεις του ΠΑΟΚ σε κάθε τμήμα, ανδρών, γυναικών και ακαδημιών."],
  archeio: ["Αρχείο σεζόν ΠΑΟΚ: αγώνες και βαθμολογίες – PAOKalendar",
    "Οι αγώνες και οι βαθμολογίες του ΠΑΟΚ από προηγούμενες σεζόν, σε όλα τα τμήματα."],
  akadimies: ["Ακαδημίες ΠΑΟΚ: πρόγραμμα αγώνων και αποτελέσματα – PAOKalendar",
    "Το πρόγραμμα και τα αποτελέσματα των ακαδημιών του ΠΑΟΚ σε ποδόσφαιρο, μπάσκετ, βόλεϊ και πόλο, αγοριών και κοριτσιών."],
  atomika: ["ΠΑΟΚ ατομικά αθλήματα: διοργανώσεις και μετάλλια – PAOKalendar",
    "Οι αθλητές του ΑΣ ΠΑΟΚ στα ατομικά αθλήματα: επόμενες διοργανώσεις, αποτελέσματα και μετάλλια."],
  imerologia: ["Ημερολόγιο αγώνων ΠΑΟΚ για iPhone, Android και Google – PAOKalendar",
    "Βάλε τους αγώνες του ΠΑΟΚ στο ημερολόγιο του κινητού σου, εντός ή εκτός έδρας, ανά τμήμα. Ενημερώνεται μόνο του."],
  efarmogi: ["Η εφαρμογή PAOKalendar στο κινητό",
    "Εγκατάστησε το PAOKalendar στην αρχική οθόνη: πρόγραμμα, αποτελέσματα και ειδοποιήσεις για όλα τα τμήματα του ΠΑΟΚ. Δωρεάν, χωρίς διαφημίσεις."],
  eidopoiiseis: ["Ειδοποιήσεις για τους αγώνες του ΠΑΟΚ – PAOKalendar",
    "Ειδοποίηση στο κινητό πριν από κάθε αγώνα, σε κάθε γκολ και στο τελικό αποτέλεσμα, για όποια τμήματα του ΠΑΟΚ θέλεις."],
  aporrito: ["Απόρρητο και cookies – PAOKalendar", "Πώς το PAOKalendar χειρίζεται τα δεδομένα σου."],
};

const fmtTime = (m) => {
  const d = new Date(m.start);
  const day = new Intl.DateTimeFormat("el-GR", { timeZone: "Europe/Athens", weekday: "short", day: "numeric", month: "short" }).format(d);
  if (!m.timeKnown) return day;
  return day + " " + new Intl.DateTimeFormat("el-GR", { timeZone: "Europe/Athens", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(d);
};

function matchLi(S, m, secMap) {
  const sec = secMap[m.section];
  const teams = m.score ? `${esc(m.home)} ${esc(m.score)} ${esc(m.away)}` : `${esc(m.home)} – ${esc(m.away)}`;
  const extra = [sec ? S.sectionLabel(sec) : "", m.competition, m.tv].filter(Boolean).map(esc).join(" · ");
  return `<li><a href="/${esc(S.matchSlug(m))}">${teams}</a> <small>${esc(fmtTime(m))}${extra ? " · " + extra : ""}</small></li>`;
}

function lists(S, matches, secMap, n = 10) {
  const now = Date.now();
  const next = matches.filter((m) => !m.score && new Date(m.start) > now - 3 * 3600e3)
    .sort((a, b) => a.start.localeCompare(b.start)).slice(0, n);
  const last = matches.filter((m) => m.score && new Date(m.start) <= now)
    .sort((a, b) => b.start.localeCompare(a.start)).slice(0, n);
  return (next.length ? `<h2>Επόμενοι αγώνες</h2><ul>${next.map((m) => matchLi(S, m, secMap)).join("")}</ul>` : "") +
    (last.length ? `<h2>Τελευταία αποτελέσματα</h2><ul>${last.map((m) => matchLi(S, m, secMap)).join("")}</ul>` : "");
}

// Σύνδεσμοι σε όλα τα τμήματα: η Google βρίσκει έτσι και τις υπόλοιπες σελίδες.
function navHtml(S, sections) {
  const senior = sections.filter((s) => !s.academy);
  return `<nav aria-label="Τμήματα"><h2>Τμήματα</h2><ul>` +
    senior.map((s) => `<li><a href="/${S.sectionSlug(s.key)}">${esc(S.sectionLabel(s))}</a></li>`).join("") +
    `<li><a href="/akadimies">Ακαδημίες</a></li><li><a href="/atomika">Ατομικά αθλήματα</a></li>` +
    `<li><a href="/programma">Πρόγραμμα</a></li><li><a href="/tropaia">Τρόπαια</a></li><li><a href="/imerologia">Ημερολόγια</a></li></ul></nav>`;
}

function sportsEvent(S, m, secMap) {
  const sec = secMap[m.section] || {};
  const team = (name, logo) => ({ "@type": "SportsTeam", name, ...(logo ? { logo } : {}) });
  return {
    "@context": "https://schema.org",
    "@type": "SportsEvent",
    name: `${m.home} – ${m.away}`,
    description: [m.competition, m.round].filter(Boolean).join(", ") || undefined,
    startDate: m.start,
    eventStatus: "https://schema.org/EventScheduled",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    sport: sec.sport,
    url: `${SITE}/${S.matchSlug(m)}`,
    homeTeam: team(m.home, m.homeLogo),
    awayTeam: team(m.away, m.awayLogo),
    competitor: [team(m.home, m.homeLogo), team(m.away, m.awayLogo)],
    ...(m.venue ? { location: { "@type": "Place", name: m.venue, address: m.venue } } : {}),
    organizer: { "@type": "Organization", name: m.competition || "ΠΑΟΚ" },
  };
}

export async function build(slug) {
  const [S, shell, data] = await Promise.all([loadSeo(), loadShell(), loadMatches()]);
  const sections = data.sections || [];
  const secMap = Object.fromEntries(sections.map((s) => [s.key, s]));
  const matches = data.matches || [];
  const hash = S.hashFor(slug);
  let title, desc, body, ld = null, status = 200, canonical = `${SITE}/${slug}`;
  const h = (hash || "").replace(/^#\//, "");

  if (hash && h.startsWith("m/")) {
    const nt = h.slice(2);
    const m = matches.find((x) => x.nt === nt);
    if (m) {
      const sec = secMap[m.section] || {};
      canonical = `${SITE}/${S.matchSlug(m)}`;
      title = S.matchTitle(m);
      const when = fmtTime(m);
      desc = `${m.home} – ${m.away}${m.score ? " " + m.score : ""}: ${when}` +
        [sec.name ? S.sectionLabel(sec) : "", m.competition, m.round, m.venue, m.tv ? "TV: " + m.tv : ""].filter(Boolean).map((x) => ", " + x).join("") + ".";
      body = `<h1>${esc(m.home)} – ${esc(m.away)}${m.score ? " " + esc(m.score) : ""}</h1>` +
        `<p>${esc(when)}${m.timeKnown ? "" : " (η ώρα δεν έχει οριστεί ακόμα)"}</p><ul>` +
        [["Τμήμα", sec.name ? S.sectionLabel(sec) : ""], ["Διοργάνωση", m.competition], ["Αγωνιστική", m.round], ["Γήπεδο", m.venue], ["Κανάλι", m.tv]]
          .filter((x) => x[1]).map((x) => `<li>${x[0]}: ${esc(x[1])}</li>`).join("") + `</ul>` +
        (sec.key ? `<p><a href="/${S.sectionSlug(sec.key)}">Όλοι οι αγώνες: ${esc(S.sectionLabel(sec))}</a></p>` : "");
      ld = sportsEvent(S, m, secMap);
    } else status = 404;
  } else if (hash && PAGE_META[slug]) {
    [title, desc] = PAGE_META[slug];
    const pool = slug === "akadimies" ? matches.filter((m) => secMap[m.section]?.academy)
      : slug === "programma" ? matches.filter((m) => !secMap[m.section]?.academy) : null;
    body = `<h1>${esc(title.replace(/ – PAOKalendar$/, ""))}</h1><p>${esc(desc)}</p>` + (pool ? lists(S, pool, secMap, 20) : "");
  } else if (hash && secMap[h]) {
    const sec = secMap[h];
    const label = S.sectionLabel(sec);
    title = S.sectionTitle(sec);
    desc = `${label}${sec.academy ? " (ακαδημίες)" : ""}: όλοι οι αγώνες με μέρα, ώρα, γήπεδο και κανάλι, τα αποτελέσματα και η βαθμολογία. Ειδοποιήσεις και ημερολόγιο στο κινητό.`;
    body = `<h1>${esc(label)}</h1><p>${esc(desc)}</p>` + lists(S, matches.filter((m) => m.section === h), secMap);
  } else status = 404;

  if (status === 404) {
    title = "Η σελίδα δεν βρέθηκε – PAOKalendar";
    desc = "Η σελίδα δεν υπάρχει. Δες το πρόγραμμα αγώνων του ΠΑΟΚ στην αρχική.";
    body = `<h1>Η σελίδα δεν βρέθηκε</h1><p><a href="/">Στην αρχική</a></p>`;
  }

  let html = shell
    .replace(/<title>[^<]*<\/title>/, `<title>${esc(title)}</title>`)
    .replace(/(<meta name="description" content=")[^"]*/, `$1${esc(desc)}`)
    .replace(/(<meta property="og:title" content=")[^"]*/, `$1${esc(title.replace(/ – PAOKalendar$/, ""))}`)
    .replace(/(<meta property="og:description" content=")[^"]*/, `$1${esc(desc)}`)
    .replace(/<main id="app">[\s\S]*?<\/main>/, `<main id="app">${body}${navHtml(S, sections)}</main>`);
  if (status === 404) {
    html = html.replace(/<link rel="canonical"[^>]*>\n?/, "").replace(/<meta property="og:url"[^>]*>\n?/, "")
      .replace("<head>", '<head>\n<meta name="robots" content="noindex">');
  } else {
    html = html.replace(/(<link rel="canonical" href=")[^"]*/, `$1${canonical}`)
      .replace(/(<meta property="og:url" content=")[^"]*/, `$1${canonical}`);
  }
  if (ld) html = html.replace("</head>", `<script type="application/ld+json">${JSON.stringify(ld).replace(/</g, "\\u003c")}</script>\n</head>`);
  return { status, html };
}

export default async function handler(req, res) {
  const slug = String(req.query?.p || "").toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 120);
  try {
    const { status, html } = await build(slug);
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.setHeader("Cache-Control", status === 200
      ? "public, max-age=0, s-maxage=300, stale-while-revalidate=600, stale-if-error=86400"
      : "public, max-age=0, s-maxage=60");
    return res.status(status).send(html);
  } catch (e) {
    // Χωρίς δεδομένα: η απλή σελίδα (η εφαρμογή φορτώνει μόνη της το πρόγραμμα).
    try {
      res.setHeader("Content-Type", "text/html; charset=utf-8");
      res.setHeader("Cache-Control", "no-store");
      return res.status(200).send(await loadShell());
    } catch {
      return res.status(502).send("Σφάλμα");
    }
  }
}
