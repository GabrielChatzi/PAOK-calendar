// Καθαρές διευθύνσεις για τη Google και για κοινοποίηση (π.χ. /podosfairo, /paok-aris-a86e124e1e).
//
// Η εφαρμογή δουλεύει με #/... (η Google αγνοεί ό,τι είναι μετά το #, γι' αυτό έβλεπε μόνο την αρχική).
// Το ίδιο αρχείο χρησιμοποιείται:
//   - από τη σελίδα (docs/index.html): μια καθαρή διεύθυνση γίνεται η αντίστοιχη #/... όταν ανοίγει,
//     και η «Κοινοποίηση» δίνει την καθαρή διεύθυνση·
//   - από το api/page.js: τίτλος, περιγραφή, canonical και περιεχόμενο ανά σελίδα για τις μηχανές αναζήτησης·
//   - από το api/sitemap.js: το sitemap.xml.
// Όλες οι διευθύνσεις έχουν ένα μόνο κομμάτι (χωρίς /), ώστε τα σχετικά αρχεία (matches.json, icons/) να δουλεύουν.
var PKSEO = (function () {
  "use strict";
  // Τμήματα (κλειδί του matches.json → διεύθυνση). Οι ακαδημίες παίρνουν «akadimia-<κλειδί>».
  var SECTIONS = {
    "football": "podosfairo",
    "football-women": "podosfairo-gynaikon",
    "basketball": "basket",
    "basketball-women": "basket-gynaikon",
    "volley": "volei",
    "volley-women": "volei-gynaikon",
    "handball": "handball",
    "handball-women": "handball-gynaikon",
    "waterpolo": "polo",
    "waterpolo-women": "polo-gynaikon",
    "futsal": "futsal",
    "basketball-amea": "basket-special-team"
  };
  // Σελίδες της εφαρμογής.
  var PAGES = {
    "programma": "#/program",
    "athlimata": "#/sports",
    "tropaia": "#/history/trophies",
    "archeio": "#/history/archive",
    "akadimies": "#/academies",
    "atomika": "#/atomika",
    "imerologia": "#/calendars",
    "efarmogi": "#/app",
    "eidopoiiseis": "#/notifications",
    "aporrito": "#/privacy"
  };
  var BY_KEY = {};
  Object.keys(SECTIONS).forEach(function (k) { BY_KEY[SECTIONS[k]] = k; });

  var GR = {
    "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i", "θ": "th", "ι": "i", "κ": "k", "λ": "l",
    "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y", "φ": "f",
    "χ": "ch", "ψ": "ps", "ω": "o"
  };
  // «Ολυμπιακός Σ.Φ.Π.» → «olympiakos-sfp». Τόνοι και σημεία στίξης φεύγουν.
  function slugify(s) {
    s = String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
      .replace(/ου/g, "ou").replace(/αυ/g, "av").replace(/ευ/g, "ev").replace(/γγ/g, "ng")
      .replace(/(^|[^α-ω])μπ/g, "$1b").replace(/(^|[^α-ω])ντ/g, "$1d");  // «Μπάσκετ» → basket, «Ολυμπιακός» → olympiakos
    s = s.replace(/[α-ω]/g, function (c) { return GR[c] || ""; });
    return s.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40).replace(/-+$/, "");
  }
  function sectionSlug(key) { return SECTIONS[key] || "akadimia-" + key; }
  function matchSlug(m) {
    var base = slugify(m.home) + "-" + slugify(m.away);
    return (base.replace(/^-+|-+$/g, "") || "agonas") + "-" + m.nt;
  }
  // Διεύθυνση (χωρίς το αρχικό /) → #/... της εφαρμογής, ή null αν δεν την ξέρουμε.
  function hashFor(slug) {
    slug = String(slug || "").replace(/^\/+|\/+$/g, "").toLowerCase();
    if (!slug) return "#/";
    if (PAGES[slug]) return PAGES[slug];
    if (BY_KEY[slug]) return "#/" + BY_KEY[slug];
    var a = /^akadimia-([a-z0-9-]+)$/.exec(slug);
    if (a) return "#/" + a[1];
    var m = /-([0-9a-f]{10})$/.exec(slug) || /^([0-9a-f]{10})$/.exec(slug);
    if (m) return "#/m/" + m[1];
    return null;
  }
  // Το αντίστροφο: #/... → καθαρή διεύθυνση (για την «Κοινοποίηση»), ή null.
  // isSection(key): αν το κλειδί είναι τμήμα (η σελίδα το ξέρει από το matches.json).
  function pathFor(hash, match, isSection) {
    var h = String(hash || "").replace(/^#\/?/, "").split("?")[0];
    if (!h) return "/";
    var parts = h.split("/");
    if (parts[0] === "m" && parts[1]) return "/" + (match ? matchSlug(match) : parts[1]);
    for (var p in PAGES) if (PAGES[p] === "#/" + h) return "/" + p;
    if (parts.length === 1 && (SECTIONS[parts[0]] || (isSection && isSection(parts[0])))) return "/" + sectionSlug(parts[0]);
    return null;
  }
  // Τίτλοι: ίδιοι στη σελίδα (document.title) και σε όσα βλέπει η Google (api/page.js).
  // «ΠΑΟΚ Μπάσκετ Γυναικών», «ΠΑΟΚ Ποδόσφαιρο Κ19», «ΠΑΟΚ Β».
  function sectionLabel(sec) {
    var name = sec.name || "";
    if (/^ΠΑΟΚ/.test(name)) return name;
    if (sec.academy && sec.sport && name.indexOf(sec.sport) < 0) name = sec.sport + " " + name;
    return "ΠΑΟΚ " + name;
  }
  function sectionTitle(sec) {
    return sectionLabel(sec) + (sec.academy ? " (ακαδημίες)" : "") + ": πρόγραμμα αγώνων και αποτελέσματα – PAOKalendar";
  }
  function matchDate(m, opts) {
    try {
      return new Intl.DateTimeFormat("el-GR", Object.assign({ timeZone: "Europe/Athens", day: "numeric", month: "long", year: "numeric" }, opts || {})).format(new Date(m.start));
    } catch (e) { return ""; }
  }
  function matchTitle(m) {
    var teams = m.score ? m.home + " " + m.score + " " + m.away : m.home + " – " + m.away;
    var d = matchDate(m);
    return teams + (d ? ", " + d : "") + " – PAOKalendar";
  }
  return {
    SECTIONS: SECTIONS, PAGES: PAGES, slugify: slugify, sectionSlug: sectionSlug, matchSlug: matchSlug, hashFor: hashFor, pathFor: pathFor,
    sectionLabel: sectionLabel, sectionTitle: sectionTitle, matchDate: matchDate, matchTitle: matchTitle
  };
})();
