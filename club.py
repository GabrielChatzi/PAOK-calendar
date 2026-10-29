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

from build_calendars import ATHENS, Match, clean, fetch, greek_month, is_paok, plain, short_hash

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


def section_of(label: str) -> str | None:
    return PROGRAM_SECTIONS.get(plain(label).strip())


def get_json(path: str):
    return json.loads(fetch(API + path))


def nominative(name: str) -> str:
    """«τον Παναθηναϊκό» → «Παναθηναϊκός» (μόνο για τις συνηθισμένες καταλήξεις)."""
    name = re.sub(r"^(?:τον|την|το|τους|τις|τα)\s+", "", name.strip())
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
            teams = re.sub(r"\s*\([^)]*\)\s*$", "", tm.group(3)).strip()  # χωρίς το κανάλι
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
            })
    return out


# ---------------------------------------------------------------- ανακοινώσεις αγώνων

def announcement_entries(today: dt.date) -> list[dict]:
    cats = get_json("categories?per_page=100&_fields=id,name")
    section_by_cat = {c["id"]: section_of(c["name"]) for c in cats}
    academy = {c["id"] for c in cats if "ΑΚΑΔΗΜ" in plain(c["name"])}
    posts = get_json("posts?per_page=50&_fields=id,date,title,content,link,categories")
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
                          r"απέναντι στ(?:ον|ην|ο)|φιλοξενηθεί από τ(?:ον|ην|ο)|με τ(?:ον|ην|ο))\s+"
                          r"((?:τ(?:ον|ην|ο)\s+)?[Α-ΩΆ-Ώ][^\s,.!;«»]*(?:\s+[Α-ΩΆ-Ώ][^\s,.!;«»]*){0,2})",
                          title + " " + text)
            if o and not is_paok(o.group(1)) and not nicknames.match(o.group(1)):
                opponent = nominative(o.group(1))
        out.append({
            "kind": "announcement", "section": section, "day": day,
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
            latest[e["day"]] = e
    seen: set[str] = set()
    for e in latest.values():
        paok_home = is_paok(e["home"]) if e["kind"] == "program" else e["home_flag"]
        # Χωρίς ώρα, η επίσημη ημερομηνία είναι συνήθως της αγωνιστικής: ο αγώνας μπορεί να είναι λίγες μέρες μετά.
        candidates = [m for m in official + added
                      if abs((m.day - e["day"]).days) <= (3 if m.time is None else 1)
                      and (paok_home is None or m.paok_home == paok_home)]
        if candidates:
            m = min(candidates, key=lambda m: abs((m.day - e["day"]).days))
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
            url=e["link"],
        ))
        checks.append(f"- **{label}** {added[-1].home} – {added[-1].away}, {fmt(e['day'], e['time'])}: "
                      f"δεν υπάρχει ακόμα στην επίσημη πηγή· προστέθηκε από την ΑΣ ΠΑΟΚ ([ανακοίνωση]({e['link']}))")
    return added
