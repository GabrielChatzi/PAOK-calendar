#!/usr/bin/env python3
"""Δεύτερη πηγή προγράμματος: οι ανακοινώσεις της ΑΣ ΠΑΟΚ (acpaok.gr).

Οι επίσημες πηγές (ομοσπονδίες, λίγκες) συχνά ανεβάζουν τους αγώνες με καθυστέρηση, ενώ
η ΑΣ ΠΑΟΚ τους ανακοινώνει αμέσως. Από το acpaok.gr διαβάζουμε:

  - την εβδομαδιαία ανάρτηση «Όπου και αν παίζεις σ' ακολουθάμε (dd/mm-dd/mm)», με όλους
    τους αγώνες της εβδομάδας σε σταθερή μορφή (τμήμα, διοργάνωση, γήπεδο, ώρα και ομάδες)·
  - τις ανακοινώσεις αγώνων, που έχουν στον τίτλο «(dd/mm, ωω:λλ)».

Η επίσημη πηγή έχει πάντα προτεραιότητα. Από την ΑΣ ΠΑΟΚ:
  - αγώνας που λείπει από την επίσημη πηγή προστίθεται (μέχρι να τον δημοσιεύσει εκείνη)·
  - αν η επίσημη πηγή δεν έχει ακόμα ώρα (TBC), παίρνει την ώρα της ΑΣ ΠΑΟΚ·
  - κάθε διαφορά (άλλη μέρα ή ώρα) καταγράφεται στους «ελέγχους», που το workflow ανεβάζει
    σε ένα issue στο GitHub, ώστε να έρθει email.

Ό,τι κι αν συμβεί εδώ (π.χ. αλλαγή στο site), η ενημέρωση του προγράμματος συνεχίζει κανονικά.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys

from build_calendars import ATHENS, Match, clean, fetch, greek_month, greekish, is_paok, plain, short_hash

API = "https://acpaok.gr/wp-json/wp/v2/"

# Τμήμα στην εβδομαδιαία ανάρτηση και κατηγορίες στις ανακοινώσεις → τμήμα της σελίδας.
PROGRAM_SECTIONS = {
    "ΠΑΕ ΠΑΟΚ": "football", "ΠΟΔΟΣΦΑΙΡΟ ΓΥΝΑΙΚΩΝ": "football-women",
    "ΚΑΕ ΠΑΟΚ": "basketball", "ΜΠΑΣΚΕΤ ΓΥΝΑΙΚΩΝ": "basketball-women",
    "ΒΟΛΕΪ ΑΝΔΡΩΝ": "volley", "ΒΟΛΕΙ ΑΝΔΡΩΝ": "volley",
    "ΒΟΛΕΪ ΓΥΝΑΙΚΩΝ": "volley-women", "ΒΟΛΕΙ ΓΥΝΑΙΚΩΝ": "volley-women",
    "ΧΑΝΤΜΠΟΛ ΑΝΔΡΩΝ": "handball", "ΧΑΝΤΜΠΟΛ ΓΥΝΑΙΚΩΝ": "handball-women",
    "ΠΟΛΟ ΑΝΔΡΩΝ": "waterpolo", "ΠΟΛΟ ΓΥΝΑΙΚΩΝ": "waterpolo-women",
    "ΠΟΔΟΣΦΑΙΡΟ ΣΑΛΑΣ": "futsal",
}
WEEKDAYS = ["ΔΕΥΤΕΡΑ", "ΤΡΙΤΗ", "ΤΕΤΑΡΤΗ", "ΠΕΜΠΤΗ", "ΠΑΡΑΣΚΕΥΗ", "ΣΑΒΒΑΤΟ", "ΚΥΡΙΑΚΗ"]

_DATA: dict = {}
# Φιλικοί αγώνες (και τουρνουά προετοιμασίας, «αποκαλυπτήρια»): μπαίνουν ως χωριστοί αγώνες και ποτέ
# δεν «ενώνονται» με επίσημο αγώνα της ίδιας ή διπλανής μέρας.
FRIENDLY_RE = re.compile(r"φιλικ|αποκαλυπτήρια|τουρνου[άα]|προετοιμασ", re.I)
FRIENDLY = "Φιλικός αγώνας"


def recent_posts() -> list[dict]:
    """Οι τελευταίες 50 αναρτήσεις (μία φορά ανά εκτέλεση)."""
    if "posts" not in _DATA:
        _DATA["posts"] = get_json("posts?per_page=50&_fields=id,date,title,content,link,categories")
    return _DATA["posts"]


def section_of(label: str) -> str | None:
    return PROGRAM_SECTIONS.get(plain(label).strip())


def get_json(path: str):
    return json.loads(fetch(API + path))


def nominative(name: str) -> str:
    """«τον Παναθηναϊκό» → «Παναθηναϊκός» (μόνο για τις συνηθισμένες καταλήξεις)."""
    name = re.sub(r"^(?:τον|την|το|τη|της|τους|τις|τα)\s+", "", name.strip())
    words = name.split()
    if words and re.search(r"[όο]$", words[0]) and len(words[0]) > 3:
        words[0] += "ς"
    return " ".join(words)


# ---------------------------------------------------------------- εβδομαδιαίο πρόγραμμα

def program_entries(today: dt.date) -> list[dict]:
    posts = get_json("posts?search=%CE%B1%CE%BA%CE%BF%CE%BB%CE%BF%CF%85%CE%B8%CE%AC%CE%BC%CE%B5"
                     "&per_page=3&_fields=id,date,modified,title,content,link")
    out = []
    for post in posts:
        title = html.unescape(post["title"]["rendered"])
        rng = re.search(r"\((\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\)", title)
        if not rng:
            continue
        year = int(post["modified"][:4])
        start = dt.date(year, int(rng.group(2)), int(rng.group(1)))
        end = dt.date(year + (1 if int(rng.group(4)) < int(rng.group(2)) else 0), int(rng.group(4)), int(rng.group(3)))
        if end < today - dt.timedelta(days=1):
            continue  # παλιά εβδομάδα
        days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
        current: dt.date | None = None
        for para in re.findall(r"<p[^>]*>(.*?)</p>", post["content"]["rendered"], re.S):
            lines = [clean(x) for x in re.split(r"<br\s*/?>", para) if clean(x)]
            if len(lines) == 1:
                m = re.match(r"(\S+)\s+(\d{1,2})\s+(\S+)\s+(\d{4})", lines[0])
                if m:
                    # Η ανάρτηση έχει κάποιες φορές λάθος αριθμό μέρας· κρατάμε τη μέρα της εβδομάδας.
                    wd = plain(m.group(1))
                    month = greek_month(m.group(3))
                    named = dt.date(int(m.group(4)), month, int(m.group(2))) if month else None
                    by_weekday = [d for d in days if WEEKDAYS[d.weekday()] == wd]
                    current = named if named in days and (not by_weekday or named in by_weekday) else (
                        by_weekday[0] if by_weekday else named)
                continue
            if current is None or len(lines) < 4:
                continue
            section = section_of(lines[0])
            tm = re.match(r"(\d{1,2})[:.](\d{2}),\s*(.+)", lines[-1])
            if not section or not tm:
                continue
            ch = re.search(r"\(([^)]*)\)\s*$", tm.group(3))  # το κανάλι, π.χ. «(ΕΡΤ2 ΣΠΟΡ HD)»
            teams = re.sub(r"\s*\([^)]*\)\s*$", "", tm.group(3)).strip()
            home = away = None
            for i in [i for i, ch in enumerate(teams) if ch in "-–"]:
                left, right = teams[:i].strip(), teams[i + 1:].strip()
                if left and right and is_paok(left) != is_paok(right):
                    home, away = left, right
                    break
            if not home:
                continue
            comp = lines[1]
            out.append({
                "kind": "program", "section": section, "day": current,
                "time": dt.time(int(tm.group(1)), int(tm.group(2))), "home": home, "away": away,
                "venue": lines[2], "round": comp.split(",", 1)[0].strip() if "," in comp else "",
                "competition": comp.split(",", 1)[1].strip() if "," in comp else comp,
                "link": post["link"], "id": f"p{post['id']}", "posted": post["modified"],
                "channel": ch.group(1).strip() if ch else "",
                "friendly": bool(FRIENDLY_RE.search(comp)),
            })
    return out


# ---------------------------------------------------------------- ανακοινώσεις αγώνων

def announcement_entries(today: dt.date) -> list[dict]:
    cats = get_json("categories?per_page=100&_fields=id,name")
    section_by_cat = {c["id"]: section_of(c["name"]) for c in cats}
    academy = {c["id"] for c in cats if "ΑΚΑΔΗΜ" in plain(c["name"])}
    posts = recent_posts()
    nicknames = re.compile(r"^(?:Δικέφαλ|Ασπρόμαυρ|Τρεμπλούχ|Νταμπλούχ|Πρωταθλ)")
    out = []
    for post in posts:
        if academy & set(post["categories"]):
            continue
        sections = {section_by_cat.get(c) for c in post["categories"]} - {None}
        if len(sections) != 1:
            continue
        section = sections.pop()
        title = html.unescape(post["title"]["rendered"])
        m = re.search(r"\((\d{1,2})/(\d{1,2}),\s*(\d{1,2})[:.](\d{2})\)", title)
        if not m:
            continue
        posted = dt.date.fromisoformat(post["date"][:10])
        day = dt.date(posted.year, int(m.group(2)), int(m.group(1)))
        if day < posted - dt.timedelta(days=60):
            day = day.replace(year=posted.year + 1)
        if day < today:
            continue
        text = clean(post["content"]["rendered"])
        # Έδρα και αντίπαλος, όπου το κείμενο τα λέει καθαρά.
        home = None
        if re.search(r"υποδ[εέ]χ|υποδεχθ|εντός έδρας", text):
            home = True
        elif re.search(r"φιλοξενηθ|ταξιδ[εέ]ύ|εκτός έδρας|στην έδρα (?:του|της)", text):
            home = False
        opponent = None
        t = re.search(r"([Α-ΩΆ-Ώ][^\s–-]*(?:\s+[^\s–-]+){0,3})\s*[–-]\s*([Α-ΩΆ-Ώ][^(]*?)\s*\(", title)
        if t and is_paok(t.group(1)) != is_paok(t.group(2)):
            opponent = t.group(2) if is_paok(t.group(1)) else t.group(1)
            home = is_paok(t.group(1))
        else:
            o = re.search(r"(?:υποδ[εέ]χεται|υποδεχθεί|αντιμετωπ[ίι]ζει|αντιμετωπίσει|κόντρα στ(?:ον|ην|ο)|"
                          r"απέναντι στ(?:ον|ην|ο)|φιλοξενηθεί από τ(?:ον|ην|ο)|με τ(?:ον|ην|ο|η)|κόντρα στη)\s+"
                          r"((?:τ(?:ον|ην|ο)\s+)?[Α-ΩΆ-Ώ][^\s,.!;«»]*(?:\s+[Α-ΩΆ-Ώ][^\s,.!;«»]*){0,2})",
                          title + " " + text)
            if o and not is_paok(o.group(1)) and not nicknames.match(o.group(1)):
                opponent = nominative(o.group(1))
        first = re.split(r"(?<=[.!;])\s", text, 1)[0]
        out.append({
            "kind": "announcement", "section": section, "day": day,
            "friendly": bool(FRIENDLY_RE.search(title + " " + first)),
            "time": dt.time(int(m.group(3)), int(m.group(4))), "home_flag": home, "opponent": opponent,
            "title": title, "link": post["link"], "id": f"a{post['id']}", "posted": post["date"],
        })
    return out


# ---------------------------------------------------------------- σύγκριση με την επίσημη πηγή

def entries(today: dt.date | None = None) -> list[dict]:
    """Όλα τα στοιχεία της ΑΣ ΠΑΟΚ (μία φορά ανά εκτέλεση)."""
    today = today or dt.date.today()
    if "entries" not in _DATA:
        found = []
        for get in (program_entries, announcement_entries):
            try:
                found += get(today)
            except Exception as e:  # η δεύτερη πηγή δεν σταματά ποτέ την ενημέρωση
                print(f"  ! ΑΣ ΠΑΟΚ ({get.__name__}): {e}", file=sys.stderr)
        _DATA["entries"] = found
    return _DATA["entries"]


def fmt(day: dt.date, time: dt.time | None) -> str:
    return f"{day:%d/%m}" + (f" {time:%H:%M}" if time else " (ώρα TBC)")


def friendly_match(section: str, e: dict, paok_home: bool | None, known: list[Match]) -> Match | None:
    """Ένας φιλικός αγώνας από ανακοίνωση ή το εβδομαδιαίο πρόγραμμα (αν ξέρουμε αντίπαλο)."""
    if e["kind"] == "program":
        home, away = e["home"], e["away"]
    elif e.get("opponent"):
        home, away = ("ΠΑΟΚ", e["opponent"]) if paok_home is not False else (e["opponent"], "ΠΑΟΚ")
    else:
        return None
    home = "ΠΑΟΚ" if is_paok(home) else home
    away = "ΠΑΟΚ" if is_paok(away) else away
    opponent = away if home == "ΠΑΟΚ" else home
    uid = f"{section}-friendly-{short_hash(e['day'].isoformat(), plain(opponent)[:5])}"
    if any(m.uid == uid for m in known):
        return None
    comp = e.get("competition") or ""
    return Match(section=section, uid=uid, day=e["day"], time=e["time"], home=home, away=away,
                 paok_home=home == "ΠΑΟΚ", venue=e.get("venue", ""),
                 competition=comp if comp and not FRIENDLY_RE.fullmatch(comp) and "φιλικ" not in comp.lower() else FRIENDLY,
                 url=e["link"], tv=e.get("channel", ""))


def reconcile(section: str, official: list[Match], checks: list[str], label: str) -> list[Match]:
    """Συμπληρώνει το πρόγραμμα ενός τμήματος από την ΑΣ ΠΑΟΚ. Επιστρέφει τους αγώνες που προστέθηκαν.

    Αλλάζει επίσης την ώρα των επίσημων αγώνων όταν η ΑΣ ΠΑΟΚ δίνει άλλη ώρα για την ίδια μέρα
    (ή η επίσημη πηγή δεν έχει ακόμα ώρα): η πιο πρόσφατη ανακοίνωση του συλλόγου είναι συνήθως
    πιο ενημερωμένη από τα site των ομοσπονδιών. Διαφορά στη μέρα μόνο καταγράφεται.
    """
    added: list[Match] = []
    today = dt.date.today()
    # Για την ίδια μέρα μετρά η πιο πρόσφατη ανακοίνωση (μπορεί να άλλαξε η ώρα).
    latest: dict = {}
    for e in sorted(entries(today), key=lambda e: e["posted"]):
        if e["section"] == section and e["day"] >= today:
            latest[(e["day"], e.get("friendly", False))] = e
    # Το κανάλι από όποια ανάρτηση το γράφει (η πιο πρόσφατη ανακοίνωση συχνά δεν το έχει).
    channels = {(e["day"], e.get("friendly", False)): e["channel"] for e in sorted(entries(today), key=lambda e: e["posted"])
                if e["section"] == section and e.get("channel")}
    seen: set[str] = set()
    for e in latest.values():
        key = (e["day"], e.get("friendly", False))
        if channels.get(key) and not e.get("channel"):
            e = dict(e, channel=channels[key])
        paok_home = is_paok(e["home"]) if e["kind"] == "program" else e["home_flag"]
        if e.get("friendly"):
            friendly = friendly_match(section, e, paok_home, official + added)
            if friendly:
                added.append(friendly)
            continue
        # Χωρίς ώρα, η επίσημη ημερομηνία είναι συνήθως της αγωνιστικής: ο αγώνας μπορεί να είναι λίγες μέρες μετά.
        candidates = [m for m in official + added
                      if abs((m.day - e["day"]).days) <= (3 if m.time is None else 1)
                      and (paok_home is None or m.paok_home == paok_home)]
        if candidates:
            m = min(candidates, key=lambda m: abs((m.day - e["day"]).days))
            if not m.tv and e.get("channel"):
                m.tv = e["channel"]  # το κανάλι από το εβδομαδιαίο πρόγραμμα της ΑΣ ΠΑΟΚ
            if not m.venue and e.get("venue"):
                m.venue = e["venue"]  # π.χ. η ΕΠΣ Σάλας δεν δίνει γήπεδο
            if m.time is None:
                m.day, m.time = e["day"], e["time"]  # η επίσημη πηγή δεν έχει ακόμα ώρα
            elif (m.day, m.time) != (e["day"], e["time"]) and m.uid not in seen:
                seen.add(m.uid)
                official_when = fmt(m.day, m.time)
                if m.day == e["day"]:
                    m.time = e["time"]
                    action = "κρατήθηκε η ώρα της ΑΣ ΠΑΟΚ"
                else:
                    action = "κρατήθηκε η μέρα της επίσημης πηγής"
                checks.append(f"- **{label}** {m.home} – {m.away}: η επίσημη πηγή γράφει {official_when}, "
                              f"η ΑΣ ΠΑΟΚ {fmt(e['day'], e['time'])} ([ανακοίνωση]({e['link']})) · {action}")
            continue
        if e["kind"] == "program":
            home, away = e["home"], e["away"]
        elif e["opponent"] and paok_home is not None:
            home, away = ("ΠΑΟΚ", e["opponent"]) if paok_home else (e["opponent"], "ΠΑΟΚ")
        else:
            checks.append(f"- **{label}** {fmt(e['day'], e['time'])}: η ΑΣ ΠΑΟΚ ανακοίνωσε αγώνα που δεν "
                          f"υπάρχει στο πρόγραμμα και δεν ήταν δυνατό να προστεθεί αυτόματα: "
                          f"[{e['title']}]({e['link']})")
            continue
        start = dt.datetime.combine(e["day"], e["time"], ATHENS)
        added.append(Match(
            section=section, uid=f"{section}-acpaok-{short_hash(e['day'].isoformat(), str(paok_home))}",
            day=start.date(), time=start.time(), home=home if not is_paok(home) else "ΠΑΟΚ",
            away=away if not is_paok(away) else "ΠΑΟΚ", paok_home=bool(paok_home),
            venue=e.get("venue", ""), competition=e.get("competition", ""), round=e.get("round", ""),
            url=e["link"], tv=e.get("channel", ""),
        ))
        checks.append(f"- **{label}** {added[-1].home} – {added[-1].away}, {fmt(e['day'], e['time'])}: "
                      f"δεν υπάρχει ακόμα στην επίσημη πηγή· προστέθηκε από την ΑΣ ΠΑΟΚ ([ανακοίνωση]({e['link']}))")
    return added


# ---------------------------------------------------------------- αποτελέσματα

# Η ΑΣ ΠΑΟΚ ανεβάζει το αποτέλεσμα λίγα λεπτά μετά τη λήξη (π.χ. «Επιστροφή στις νίκες για τον ΠΑΟΚ
# PayspotLabraki, νίκη με 7-3 επί του ΑΟΔ Κορυδαλλού!»), ενώ οι ομοσπονδίες καμιά φορά μετά από ώρες.
# Το παίρνουμε μόνο όταν όλα είναι ξεκάθαρα: τμήμα, ανάρτηση την ίδια μέρα μετά την έναρξη, ένα σκορ
# και ποιος κέρδισε (από τα ονόματα «Α – Β x-y» ή από λέξεις όπως νίκη/ήττα/ισοπαλία). Αλλιώς τίποτα.
# Όχι ώρες (14:00), ημερομηνίες (01/11) ή δεκαδικοί· η τελεία στο τέλος της πρότασης επιτρέπεται.
SCORE_RE = re.compile(r"(?<![\d/:])(?<!\d[.,])(\d{1,3})\s*[-–]\s*(\d{1,3})(?!\d|[/:.,]\d)")
YOUTH_RE = re.compile(r"Παίδ|Παμπαίδ|Κορασ|Νεαν|Εφήβ|Ακαδημ|\bΚ-?\d{2}\b|\bU-?\d{2}\b", re.I)
WIN_RE = re.compile(r"νίκ[ηαε]|νικ[ηώ]|επικρ[άα]τ|υπέταξ|υποτάσσ|θρίαμβ|διπλ[όο]\b|άλωσ|κέρδισ|πανηγύρισ", re.I)
LOSS_RE = re.compile(r"ήττα|ηττήθ|λύγισ|γονάτισ|έχασ|δεν τα κατάφερ|υποχώρησ", re.I)
DRAW_RE = re.compile(r"ισοπαλ|ισόπαλ", re.I)
SKIP_RE = re.compile(r"μικτή ζώνη|δήλωσ|τηλεόραση|στην TV|εισιτήρι|live stream|\(\d{1,2}/\d{1,2}", re.I)
RESULT_SECTIONS = {"football-women", "futsal", "basketball-women"}  # χωρίς τελικό από live


def score_from_post(title: str, text: str, home: str, away: str, paok_home: bool) -> str | None:
    """Το σκορ «γηπεδούχος-φιλοξενούμενος» από μια ανάρτηση, ή None αν δεν είναι ξεκάθαρο.

    Παίρνουμε το πρώτο σκορ (πρώτα στον τίτλο, μετά στην αρχή του κειμένου) και κρίνουμε ποιος
    κέρδισε μόνο από την πρόταση που το περιέχει (π.χ. «γνωρίζοντας την ήττα με 71-69»): πιο κάτω
    το κείμενο έχει σκορ περιόδων και λέξεις για άλλους αγώνες.
    """
    if SKIP_RE.search(title) or YOUTH_RE.search(title):
        return None
    # Τίτλος «ΠΑΣ Πύργος – ΠΑΟΚ 0-5»: τα ονόματα δίνουν τη σειρά.
    named = re.match(r"\s*([^\d–-]{2,40}?)\s+[–-]\s+([^\d–-]{2,40}?)\s+(\d{1,3})-(\d{1,3})\b", title)
    if named and is_paok(named.group(1)) != is_paok(named.group(2)):
        a, b = int(named.group(3)), int(named.group(4))
        return f"{a}-{b}" if is_paok(named.group(1)) == paok_home else f"{b}-{a}"
    for where in (title, text[:700]):
        found = SCORE_RE.search(where)
        if found:
            break
    else:
        return None
    a, b = int(found.group(1)), int(found.group(2))
    start = max(where.rfind(c, 0, found.start()) for c in ".!;") + 1
    ends = [i for i in (where.find(c, found.end()) for c in ".!;") if i >= 0]
    sentence = where[start:min(ends) if ends else len(where)]
    win, loss, draw = bool(WIN_RE.search(sentence)), bool(LOSS_RE.search(sentence)), bool(DRAW_RE.search(sentence))
    if draw and a == b and not (win or loss):
        paok, other = a, b
    elif win != loss and a != b:
        paok, other = (max(a, b), min(a, b)) if win else (min(a, b), max(a, b))
    else:
        return None
    return f"{paok}-{other}" if paok_home else f"{other}-{paok}"


def results(section: str, matches: list[Match], now: dt.datetime | None = None) -> None:
    """Συμπληρώνει το σκορ αγώνων που έγιναν σήμερα/χθες και δεν έχουν ακόμα επίσημο αποτέλεσμα."""
    now = now or dt.datetime.now(ATHENS)
    waiting = [m for m in matches if not m.score and not m.status and m.time
               and (section in RESULT_SECTIONS or "-friendly-" in m.uid)
               and m.start() < now and now - m.start() < dt.timedelta(days=2)]
    if not waiting:
        return
    cats = get_json("categories?per_page=100&_fields=id,name")
    section_by_cat = {c["id"]: section_of(c["name"]) for c in cats}
    youth = {c["id"] for c in cats if YOUTH_RE.search(c["name"])}
    for m in waiting:
        for post in sorted(recent_posts(), key=lambda p: p["date"]):
            if youth & set(post["categories"]):
                continue
            if {section_by_cat.get(c) for c in post["categories"]} - {None} != {section}:
                continue
            posted = dt.datetime.fromisoformat(post["date"]).replace(tzinfo=ATHENS)
            if not (m.start() + dt.timedelta(minutes=30) <= posted <= m.start() + dt.timedelta(hours=30)):
                continue
            title = html.unescape(post["title"]["rendered"])
            text = clean(post["content"]["rendered"])
            # Αποτέλεσμα φιλικού μόνο για φιλικό, και το ανάποδο.
            if bool(FRIENDLY_RE.search(title + " " + text[:200])) != ("-friendly-" in m.uid):
                continue
            score = score_from_post(title, text, m.home, m.away, m.paok_home)
            if score:
                print(f"  αποτέλεσμα από την ΑΣ ΠΑΟΚ: {m.home} – {m.away} {score} («{title}»)")
                m.score, m.live = score, None
                break


# ---------------------------------------------------------------- τηλεοπτική μετάδοση

# Η ΑΣ ΠΑΟΚ γράφει το κανάλι στην ανακοίνωση του αγώνα («Η αναμέτρηση θα μεταδοθεί μέσω του ΕΟΚ TV»)
# και ανεβάζει τη μέρα των αγώνων «Με τον ΠΑΟΚ και στην TV! (dd/mm)» με τα live streaming (YouTube):
# είτε ενσωματωμένα βίντεο με τον αγώνα στον τίτλο, είτε «14:00, Πύργος-ΠΑΟΚ (Ποδόσφαιρο γυναικών)» και σύνδεσμο.
CHANNEL_RE = re.compile(r"μεταδοθεί\s+(?:ζωντανά\s+)?(?:τηλεοπτικά\s+)?(?:μέσω|από)\s+(?:του\s+|της\s+|το\s+|την\s+)?"
                        r"(?:καναλιού\s+|σταθμού\s+)?([^.;,(]{2,40}?)\s*(?:[.;,(]|$| και )")
TV_POST_RE = re.compile(r"στην TV.*\((\d{1,2})/(\d{1,2})\)")
YOUTUBE_RE = re.compile(r"youtube\.com/(?:embed/|watch\?v=)([\w-]{11})|youtu\.be/([\w-]{11})")
SPORT_WORDS = {  # λέξεις στον τίτλο ενός βίντεο → άθλημα (για να μη μπερδευτούν αγώνες με ίδιο αντίπαλο)
    "futsal": r"FUTSAL|ΣΑΛΑΣ", "basketball": r"BASKET|ΜΠΑΣΚΕΤ|WBL|EUROCUP", "volley": r"VOLLEY|ΒΟΛΕ",
    "handball": r"HANDBALL|ΧΑΝΤΜΠΟΛ|HANDBAL", "waterpolo": r"WATER ?POLO|ΠΟΛΟ\b|WPL", "football": r"ΠΟΔΟΣΦΑΙΡΟ(?! ΣΑΛΑΣ)|FOOTBALL|WFL",
}


def team_words(name: str) -> list[str]:
    """Οι λέξεις ενός ονόματος ομάδας που ξεχωρίζουν (πρώτα 5 γράμματα), σε κεφαλαία ελληνικά."""
    words = re.findall(r"[A-ZΑ-Ω]{4,}", greekish(re.sub(r"[.\s]+(?=[A-ZΑ-Ω]\b)", "", plain(name))))
    return [w[:5] for w in words if not w.startswith("ΠΑΟΚ")]


def same_sport(section: str, text: str) -> bool:
    t = plain(text)
    sport = section.replace("-women", "")
    other = [k for k, rx in SPORT_WORDS.items() if k != sport and re.search(rx, t)]
    return not other or re.search(SPORT_WORDS.get(sport, "$^"), t) is not None


def tv(section: str, matches: list[Match], now: dt.datetime | None = None) -> None:
    """Κανάλι και σύνδεσμος μετάδοσης για τους αγώνες των επόμενων ημερών (όσο δεν τα έχει η επίσημη πηγή)."""
    now = now or dt.datetime.now(ATHENS)
    soon = [m for m in matches if not m.score and -1 <= (m.day - now.date()).days <= 10]
    if not soon:
        return
    cats = get_json("categories?per_page=100&_fields=id,name")
    section_by_cat = {c["id"]: section_of(c["name"]) for c in cats}
    youth = {c["id"] for c in cats if YOUTH_RE.search(c["name"])}
    for post in sorted(recent_posts(), key=lambda p: p["date"]):
        title = html.unescape(post["title"]["rendered"])
        raw = post["content"]["rendered"]
        posted = dt.date.fromisoformat(post["date"][:10])
        tvp = TV_POST_RE.search(title)
        if tvp:
            day = dt.date(posted.year, int(tvp.group(2)), int(tvp.group(1)))
            # Κάθε βίντεο ή σύνδεσμος με το κείμενο που τον περιγράφει (τίτλος βίντεο ή η γραμμή πριν).
            items = [(html.unescape(t), u) for t, u in re.findall(r'<iframe[^>]*title="([^"]*)"[^>]*src="([^"]*)"', raw)]
            for para, url in re.findall(r"<p[^>]*>([^<]*\d{1,2}:\d{2}[^<]*)</p>\s*<p[^>]*>\s*<a[^>]*href=\"([^\"]+)\"", raw):
                items.append((html.unescape(para), url))
            for text, url in items:
                y = YOUTUBE_RE.search(url)
                link = f"https://www.youtube.com/watch?v={y.group(1) or y.group(2)}" if y else url
                for m in soon:
                    other = m.away if is_paok(m.home) else m.home
                    words = team_words(other)
                    if m.day == day and words and any(w in greekish(plain(text)) for w in words) and same_sport(m.section, text):
                        if not m.tv_url:
                            m.tv_url = link
                            if not m.tv:
                                m.tv = "AC PAOK TV" if "AC PAOK TV" in text.upper() else "YouTube"
            continue
        if youth & set(post["categories"]):
            continue
        if {section_by_cat.get(c) for c in post["categories"]} - {None} != {section}:
            continue
        when = re.search(r"\((\d{1,2})/(\d{1,2}),\s*\d{1,2}[:.]\d{2}\)", title)
        ch = CHANNEL_RE.search(clean(raw))
        if not when or not ch:
            continue
        day = dt.date(posted.year, int(when.group(2)), int(when.group(1)))
        if day < posted - dt.timedelta(days=60):
            day = day.replace(year=posted.year + 1)
        channel = re.sub(r"\s+", " ", ch.group(1)).strip(" «»\"")
        for m in soon:
            if m.day == day and not m.tv:
                m.tv = channel
