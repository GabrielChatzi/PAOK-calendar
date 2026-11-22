#!/usr/bin/env python3
"""Ατομικά αθλήματα της ΑΣ ΠΑΟΚ: διοργανώσεις (όχι αγώνες «ΠΑΟΚ – αντίπαλος»).

Στίβος, κολύμβηση, πάλη, πυγμαχία, άρση βαρών, τζούντο κ.ά. δεν έχουν αντίπαλο ούτε σταθερή πηγή
προγράμματος: έχουν διοργανώσεις (πανελλήνιο, μίτινγκ, κύπελλο…) μιας ή περισσότερων ημερών, με
αποτελέσματα σε θέσεις και μετάλλια. Γι' αυτό ζουν χωριστά από τους αγώνες: δικό τους αρχείο
(docs/events.json), δικά τους ημερολόγια (docs/<άθλημα>-events.ics, docs/all-events.ics) και δική τους
σελίδα (#/atomika, προς το παρόν μόνο για τον διαχειριστή). Δεν μπαίνουν στο matches.json, άρα ούτε στην
αρχική, στα social, στα συνδυαστικά ημερολόγια ή στο live.

Από πού έρχονται:
  1. ΑΣ ΠΑΟΚ (acpaok.gr): οι αναρτήσεις κάθε ατομικού αθλήματος (κατηγορίες του WordPress). Όταν μια
     ανάρτηση γράφει ημερομηνίες διοργάνωσης («19 έως 22 Νοεμβρίου», «28-29/11»), γίνεται διοργάνωση με
     τίτλο της ανάρτησης· οι επόμενες αναρτήσεις για τις ίδιες μέρες (π.χ. τα αποτελέσματα) μπαίνουν στην
     ίδια διοργάνωση ως «Νέα». Λέξεις όπως ΑμεΑ ή παραολυμπιακός βάζουν την ένδειξη «ΑμεΑ».
  2. Ο διαχειριστής (φόρμα «Νέα διοργάνωση», api/admin.js, συλλογή «events»): νέες διοργανώσεις, αλλαγές
     στις αυτόματες (ίδιο id) και κρύψιμο όσων δεν είναι διοργανώσεις (hidden). Μετρά πάνω από όλα.
  3. Ομοσπονδίες (ΣΕΓΑΣ, ΕΟΑΒ): οι ανακοινώσεις με προκηρύξεις και ημερομηνίες δεν διαβάζονται (είναι PDF),
     αλλά κάθε νέα στέλνει ειδοποίηση στον διαχειριστή και φαίνεται στη σελίδα με κουμπί «Πρόσθεσε».

Οι αυτόματες διοργανώσεις κρατιούνται και όταν η ανάρτηση φύγει από τις τελευταίες 50 (από το
προηγούμενο events.json), ώστε να μένουν στα αποτελέσματα.

    python3 events.py          κανονικά (PUSH=1 για ειδοποιήσεις στον διαχειριστή)
    DRY=1 python3 events.py    μόνο εμφάνιση, χωρίς αποθήκευση ή ειδοποίηση
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from build_calendars import (ADMIN_URL, ATHENS, OUT_DIR, VTIMEZONE, clean, fetch, fold, greek_month, ics_escape, plain,
                             write_if_changed)

API = "https://acpaok.gr/wp-json/wp/v2/"
DATA_PATH = OUT_DIR / "events.json"
DRY = os.environ.get("DRY") == "1"

# Τα κλειδιά είναι και ονόματα αρχείων (<κλειδί>-events.ics): μην τα αλλάξεις.
# cats: οι κατηγορίες του acpaok.gr (ειδήσεις και ακαδημία του αθλήματος).
SPORTS = {
    "athletics": {"emoji": "🏃", "name": "Στίβος", "cats": [86, 103]},
    "swimming": {"emoji": "🏊", "name": "Κολύμβηση", "cats": [58, 99]},
    "finswimming": {"emoji": "🤿", "name": "Τεχνική Κολύμβηση", "cats": [85, 109]},
    "weightlifting": {"emoji": "🏋️", "name": "Άρση Βαρών", "cats": [64]},
    "wrestling": {"emoji": "🤼", "name": "Πάλη", "cats": [63, 102]},
    "boxing": {"emoji": "🥊", "name": "Πυγμαχία", "cats": [88, 108]},
    "judo": {"emoji": "🥋", "name": "Τζούντο", "cats": [67, 105]},
    "taekwondo": {"emoji": "🥋", "name": "Ταεκβοντό", "cats": [70, 107]},
    "kickboxing": {"emoji": "🥊", "name": "Kick Boxing", "cats": [72]},
    "sambo": {"emoji": "🤼", "name": "Σάμπο", "cats": [69]},
    "cycling": {"emoji": "🚴", "name": "Ποδηλασία", "cats": [66, 104]},
    "chess": {"emoji": "♟️", "name": "Σκάκι", "cats": [87, 106]},
}
CAT_SPORT = {c: k for k, v in SPORTS.items() for c in v["cats"]}

# Ομοσπονδίες με WordPress: ανακοινώσεις που μοιάζουν με πρόγραμμα ή προκήρυξη → ειδοποίηση στον διαχειριστή.
FEDERATIONS = [
    {"key": "segas", "name": "ΣΕΓΑΣ", "sport": "athletics",
     "url": "https://www.segas.gr/wp-json/wp/v2/posts?per_page=20&_fields=id,date,title,link"},
    {"key": "eoav", "name": "ΕΟΑΒ", "sport": "weightlifting",
     "url": "https://weightlifting.gr/wp-json/wp/v2/posts?per_page=20&_fields=id,date,title,link"},
]
FED_KINDS = re.compile(r"ΠΡΟΚΗΡΥΞ|ΗΜΕΡΟΜΗΝΙ|ΑΓΩΝΙΣΤΙΚ[ΟΗ] (ΠΡΟΓΡΑΜΜΑ|ΣΧΕΔΙΑΣΜ|ΚΑΛΕΝΤΑΡ)|ΠΡΟΓΡΑΜΜΑ ΑΓΩΝ|ΚΑΛΕΝΤΑΡΙ|ΩΡΟΛΟΓΙΟ")
FED_KEEP = 12  # πόσες ανακοινώσεις κρατάμε ανά ομοσπονδία για τη σελίδα

PARA_RE = re.compile(r"ΑΜΕΑ|ΑΜΕ\.Α|ΠΑΡΑΟΛΥΜΠ|ΠΑΡΑΛΥΜΠ|\bPARA\b|PARALYMP|ΑΝΑΠΗΡ|ΜΠΟΤΣΙΑ|BOCCIA|ΑΜΑΞΙΔΙ")

# ---------------------------------------------------------------- ημερομηνίες στο κείμενο

_WD = r"(?:(?:ΔΕΥΤΕΡΑ|ΤΡΙΤΗ|ΤΕΤΑΡΤΗ|ΠΕΜΠΤΗ|ΠΑΡΑΣΚΕΥΗ|ΣΑΒΒΑΤΟ|ΚΥΡΙΑΚΗ)\s+)?"
_SEP = r"\s*(?:-|–|—|ΕΩΣ|ΜΕΧΡΙ|ΚΑΙ|ΩΣ|&)(?:\s+(?:ΚΑΙ|ΤΗΝ|ΤΗ|ΤΟ|ΤΙΣ))*\s*" + _WD
_MON = r"([Α-Ω]{4,})"
_YEAR = r"(?:\s+(20\d\d))?"
DATE_PATTERNS = [
    # 28 Νοεμβρίου έως 1 Δεκεμβρίου (2026)
    ("mm", re.compile(r"\b(\d{1,2})\s+" + _MON + _SEP + r"(\d{1,2})\s+" + _MON + _YEAR)),
    # 19 έως 22 Νοεμβρίου · Σάββατο 28 και Κυριακή 29 Νοεμβρίου
    ("dm", re.compile(r"\b(\d{1,2})" + _SEP + r"(\d{1,2})\s+" + _MON + _YEAR)),
    # 28/11 - 1/12 · 28/11 έως 1/12
    ("nn", re.compile(r"\b(\d{1,2})/(\d{1,2})" + _SEP + r"(\d{1,2})/(\d{1,2})(?:/(20\d\d|\d\d))?\b")),
    # 28-29/11
    ("nd", re.compile(r"\b(\d{1,2})\s*(?:-|–|&|ΚΑΙ)\s*(\d{1,2})/(\d{1,2})(?:/(20\d\d|\d\d))?\b")),
    # Σάββατο 28 Νοεμβρίου (2026)
    ("m", re.compile(r"\b(\d{1,2})\s+" + _MON + _YEAR)),
    # 28/11 (/2026)
    ("n", re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(20\d\d|\d\d))?\b")),
]
MAX_SPAN = 16  # ημέρες· πιο μεγάλο «διάστημα» μάλλον δεν είναι μία διοργάνωση


def _month(word: str) -> int | None:
    """Μήνας μόνο από ολόκληρη λέξη μήνα (όχι π.χ. «ΜΑΡΤΥΡΙΑ»)."""
    m = greek_month(word)
    if not m:
        return None
    full = ["ΙΑΝΟΥΑΡΙ", "ΦΕΒΡΟΥΑΡΙ", "ΜΑΡΤΙ", "ΑΠΡΙΛΙ", "ΜΑΙ", "ΙΟΥΝΙ", "ΙΟΥΛΙ", "ΑΥΓΟΥΣΤ", "ΣΕΠΤΕΜΒΡΙ", "ΟΚΤΩΒΡΙ",
            "ΝΟΕΜΒΡΙ", "ΔΕΚΕΜΒΡΙ"][m - 1]
    w = plain(word)
    return m if w.startswith(full) and len(w) <= len(full) + 3 else None


def _year(y: str | None, month: int, day: int, ref: dt.date) -> int:
    if y:
        return int(y) + (2000 if len(y) == 2 else 0)
    best = None
    for year in (ref.year - 1, ref.year, ref.year + 1):
        try:
            d = dt.date(year, month, day)
        except ValueError:
            continue
        if best is None or abs((d - ref).days) < abs((best - ref).days):
            best = d
    return best.year if best else ref.year


def _range(kind: str, g: tuple, ref: dt.date) -> tuple[dt.date, dt.date] | None:
    try:
        if kind == "mm":
            d1, m1, d2, m2, y = int(g[0]), _month(g[1]), int(g[2]), _month(g[3]), g[4]
            if not m1 or not m2:
                return None
        elif kind == "dm":
            d1, d2, m2, y = int(g[0]), int(g[1]), _month(g[2]), g[3]
            if not m2:
                return None
            m1 = m2 if d1 <= d2 else (m2 - 2) % 12 + 1  # «30 έως 2 Δεκεμβρίου»: από τον προηγούμενο μήνα
        elif kind == "nn":
            d1, m1, d2, m2, y = int(g[0]), int(g[1]), int(g[2]), int(g[3]), g[4]
        elif kind == "nd":
            d1, d2, m2, y = int(g[0]), int(g[1]), int(g[2]), g[3]
            m1 = m2
        elif kind == "m":
            d1, m1, y = int(g[0]), _month(g[1]), g[2]
            if not m1:
                return None
            d2, m2 = d1, m1
        else:  # "n"
            d1, m1, y = int(g[0]), int(g[1]), g[2]
            d2, m2 = d1, m1
        if not (1 <= m1 <= 12 and 1 <= m2 <= 12):
            return None
        y2 = _year(y, m2, d2, ref)
        end = dt.date(y2, m2, d2)
        start = dt.date(y2 - (1 if m1 > m2 else 0), m1, d1)
    except ValueError:
        return None
    if not 0 <= (end - start).days <= MAX_SPAN:
        return None
    return start, end


def find_dates(text: str, ref: dt.date, before: int = 10, after: int = 200) -> tuple[dt.date, dt.date] | None:
    """Το πρώτο διάστημα ημερομηνιών στο κείμενο που πέφτει κοντά στη μέρα της ανάρτησης (ως `before` ημέρες
    πριν και `after` μετά)· αν δεν υπάρχει διάστημα, η πρώτη απλή ημερομηνία. Το διάστημα προηγείται γιατί
    μια μεμονωμένη μέρα συχνά είναι η αναχώρηση ή η κλήρωση («από την Τετάρτη (18/11)… από τις 19 έως τις 22
    Νοεμβρίου»). Στο ίδιο σημείο του κειμένου τα μεγαλύτερα μοτίβα μετρούν πριν από τα μικρότερα."""
    t = plain(text)
    found = []  # (θέση, -μήκος, διάστημα)
    taken: list[tuple[int, int]] = []
    for kind, rx in DATE_PATTERNS:
        for m in rx.finditer(t):
            if any(a <= m.start() < b or a < m.end() <= b for a, b in taken):
                continue  # μέρος ενός μεγαλύτερου μοτίβου που ήδη βρέθηκε
            r = _range(kind, m.groups(), ref)
            if not r:
                continue
            taken.append((m.start(), m.end()))
            if -before <= (r[1] - ref).days and (r[0] - ref).days <= after:
                found.append((m.start(), r))
    found.sort(key=lambda x: (x[1][0] == x[1][1], x[0]))  # διαστήματα πρώτα, μετά με τη σειρά του κειμένου
    return found[0][1] if found else None


# ---------------------------------------------------------------- διοργανώσεις από την ΑΣ ΠΑΟΚ

def event_id(sport: str, start: dt.date, end: dt.date) -> str:
    return hashlib.sha1(f"{sport}|{start}|{end}".encode()).hexdigest()[:12]


def tidy_title(title: str, sport: str) -> str:
    t = clean(title).strip()
    t = re.sub(r"^\s*" + re.escape(SPORTS[sport]["name"]) + r"\s*[:–-]\s*", "", t, flags=re.I)
    return re.sub(r"\s*!+\s*$", "", t).strip() or SPORTS[sport]["name"]


def post_sport(post: dict) -> str | None:
    for c in post.get("categories") or []:
        if c in CAT_SPORT:
            return CAT_SPORT[c]
    return None


def is_para(text: str) -> bool:
    return bool(PARA_RE.search(plain(text)))


def events_from_posts(posts: list[dict]) -> list[dict]:
    """Διοργανώσεις από τις αναρτήσεις της ΑΣ ΠΑΟΚ, από την παλαιότερη στη νεότερη: η πρώτη ανάρτηση για
    μια διοργάνωση δίνει τον τίτλο, οι επόμενες (ίδιο άθλημα, ημερομηνίες μέσα στη διοργάνωση ή λίγο μετά)
    μπαίνουν στα «Νέα» της."""
    out: dict[str, dict] = {}
    for post in sorted(posts, key=lambda p: p.get("date", "")):
        sport = post_sport(post)
        if not sport:
            continue
        posted = dt.date.fromisoformat(post["date"][:10])
        title = clean((post.get("title") or {}).get("rendered", ""))
        body = clean((post.get("content") or {}).get("rendered", ""))
        link = {"title": title, "url": post.get("link", ""), "date": post["date"][:10]}
        dates = find_dates(title + " . " + body, posted)
        # Η ανάρτηση ανήκει σε διοργάνωση που υπάρχει ήδη (π.χ. αποτελέσματα, χωρίς ημερομηνίες ή με τις ίδιες);
        host = None
        for e in out.values():
            if e["sport"] != sport:
                continue
            s, en = dt.date.fromisoformat(e["start"]), dt.date.fromisoformat(e["end"])
            if dates and dates[0] <= en and dates[1] >= s:
                host = e
            elif not dates and s <= posted <= en + dt.timedelta(days=3):
                host = e
        if host:
            if link["url"] not in {p["url"] for p in host["posts"]}:
                host["posts"].append(link)
            host["para"] = host["para"] or is_para(title + " " + body)
            continue
        if not dates:
            continue
        eid = event_id(sport, *dates)
        out[eid] = {
            "id": eid, "sport": sport, "title": tidy_title(title, sport), "start": dates[0].isoformat(),
            "end": dates[1].isoformat(), "time": "", "venue": "", "athletes": "", "results": "",
            "para": is_para(title + " " + body), "url": link["url"], "posts": [link], "source": "acpaok",
        }
    return list(out.values())


def acpaok_posts() -> list[dict]:
    cats = ",".join(str(c) for c in CAT_SPORT)
    return json.loads(fetch(f"{API}posts?categories={cats}&per_page=50&_fields=id,date,title,content,link,categories"))


# ---------------------------------------------------------------- ο διαχειριστής

def admin_events() -> list[dict]:
    """Οι διοργανώσεις της φόρμας (και οι αλλαγές/κρυψίματα των αυτόματων), από το api/admin."""
    got = json.loads(fetch(ADMIN_URL))
    return [e for e in got.get("events", []) if isinstance(e, dict) and e.get("id")]


FIELDS = ("sport", "title", "start", "end", "time", "venue", "athletes", "results", "para", "url")


def merge(auto: list[dict], previous: list[dict], admin: list[dict]) -> list[dict]:
    """Αυτόματες (νέες + όσες υπήρχαν ήδη) και του διαχειριστή. Ό,τι γράφει ο διαχειριστής μετρά πάνω από όλα·
    hidden: η αυτόματη διοργάνωση δεν φαίνεται."""
    by: dict[str, dict] = {}
    for e in previous:
        if e.get("source") == "acpaok":
            by[e["id"]] = dict(e)
    for e in auto:
        old = by.get(e["id"])
        if old:  # κρατά τις αναρτήσεις που έφυγαν από τις τελευταίες 50
            urls = {p["url"] for p in e["posts"]}
            e = {**e, "posts": [p for p in old.get("posts", []) if p["url"] not in urls] + e["posts"]}
            e["posts"].sort(key=lambda p: p.get("date", ""))
            e["title"] = old.get("title") or e["title"]  # ο τίτλος της πρώτης ανάρτησης
            e["para"] = e["para"] or old.get("para", False)
        by[e["id"]] = e
    for a in admin:
        base = by.get(a["id"], {"id": a["id"], "posts": [], "source": "admin"})
        if a.get("hidden"):
            by.pop(a["id"], None)
            continue
        merged = {**base, **{k: a[k] for k in FIELDS if k in a and a[k] is not None}}
        merged["edited"] = True
        by[a["id"]] = merged
    out = [e for e in by.values() if e.get("sport") in SPORTS and e.get("start")]
    for e in out:
        e["end"] = max(e.get("end") or e["start"], e["start"])
    out.sort(key=lambda e: (e["start"], e["end"], e["id"]))
    return out


# ---------------------------------------------------------------- ομοσπονδίες

def federation_notices(previous: dict) -> tuple[list[dict], list[dict]]:
    """(όλες οι πρόσφατες σχετικές ανακοινώσεις, όσες είναι νέες από την προηγούμενη φορά)."""
    old = {n["url"]: n for n in previous.get("notices", [])}
    seen_before = set(previous.get("seenNotices", [])) | set(old)
    notices, new, seen = [], [], set(seen_before)
    for f in FEDERATIONS:
        try:
            posts = json.loads(fetch(f["url"]))
        except Exception as e:
            print(f"  ! {f['name']}: {e}", file=sys.stderr)
            notices += [n for n in old.values() if n["fed"] == f["key"]]
            continue
        mine = []
        for p in posts:
            title = clean((p.get("title") or {}).get("rendered", ""))
            url = p.get("link", "")
            seen.add(url)
            if not FED_KINDS.search(plain(title)):
                continue
            n = {"fed": f["key"], "name": f["name"], "sport": f["sport"], "title": title, "url": url,
                 "date": str(p.get("date", ""))[:10]}
            mine.append(n)
            if url not in seen_before:
                new.append(n)
        # Και όσες είχαμε ήδη (π.χ. έφυγαν από τις τελευταίες 20), μέχρι FED_KEEP συνολικά.
        urls = {n["url"] for n in mine}
        mine += [n for n in old.values() if n["fed"] == f["key"] and n["url"] not in urls]
        mine.sort(key=lambda n: n["date"], reverse=True)
        notices += mine[:FED_KEEP]
    previous["seenNotices"] = sorted(seen)[-400:]
    return notices, new


# ---------------------------------------------------------------- ημερολόγια

def build_ics(name: str, events: list[dict], stamp: str) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//PAOK-calendar//EL", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             f"X-WR-CALNAME:{ics_escape(name)}", "X-WR-TIMEZONE:Europe/Athens",
             "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H", *VTIMEZONE]
    for e in events:
        s, en = dt.date.fromisoformat(e["start"]), dt.date.fromisoformat(e["end"])
        sp = SPORTS[e["sport"]]
        summary = f"{sp['emoji']} {e['title']}" + (" (ΑμεΑ)" if e.get("para") else "")
        lines += ["BEGIN:VEVENT", f"UID:event-{e['id']}@paok-calendar", f"DTSTAMP:{stamp}"]
        if e.get("time") and re.fullmatch(r"\d\d:\d\d", e["time"]):
            h, mi = map(int, e["time"].split(":"))
            start = dt.datetime.combine(s, dt.time(h, mi))
            end = max(dt.datetime.combine(en, dt.time(h, mi)), start) + dt.timedelta(hours=3)
            lines += [f"DTSTART;TZID=Europe/Athens:{start:%Y%m%dT%H%M%S}", f"DTEND;TZID=Europe/Athens:{end:%Y%m%dT%H%M%S}"]
        else:  # ολοήμερη, όσες μέρες κρατά (το DTEND είναι η επόμενη μέρα)
            lines += [f"DTSTART;VALUE=DATE:{s:%Y%m%d}", f"DTEND;VALUE=DATE:{en + dt.timedelta(days=1):%Y%m%d}"]
        lines.append(f"SUMMARY:{ics_escape(summary)}")
        if e.get("venue"):
            lines.append(f"LOCATION:{ics_escape(e['venue'])}")
        desc = [f"ΠΑΟΚ {sp['name']}"] + [x for x in (e.get("athletes"), e.get("results")) if x]
        lines.append(f"DESCRIPTION:{ics_escape(chr(10).join(desc))}")
        if e.get("url"):
            lines.append(f"URL:{e['url']}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


# ---------------------------------------------------------------- ειδοποιήσεις στον διαχειριστή

def notify_admin(new_events: list[dict], new_notices: list[dict]) -> None:
    if DRY or (not new_events and not new_notices):
        return
    import notify
    import watchdog
    for e in new_events[:5]:
        sp = SPORTS[e["sport"]]
        notify._push([watchdog.TOPIC], f"{sp['emoji']} Νέα διοργάνωση: {sp['name']}", f"{e['title']} ({when(e)})"[:140],
                     f"/#/atomika/e/{e['id']}", tag=f"event-{e['id']}")
    for n in new_notices[:5]:
        notify._push([watchdog.TOPIC], f"{SPORTS[n['sport']]['emoji']} {n['name']}: νέα ανακοίνωση", n["title"][:140],
                     n["url"], tag="fed-" + hashlib.sha1(n["url"].encode()).hexdigest()[:10])


def when(e: dict) -> str:
    s, en = dt.date.fromisoformat(e["start"]), dt.date.fromisoformat(e["end"])
    if s == en:
        return f"{s.day}/{s.month}"
    return f"{s.day}-{en.day}/{en.month}" if s.month == en.month else f"{s.day}/{s.month}-{en.day}/{en.month}"


def main() -> int:
    previous = json.loads(DATA_PATH.read_text(encoding="utf-8")) if DATA_PATH.exists() else {}
    first_run = not previous
    ok = True
    try:
        auto = events_from_posts(acpaok_posts())
        print(f"ΑΣ ΠΑΟΚ: {len(auto)} διοργανώσεις από τις αναρτήσεις")
    except Exception as e:
        ok = False
        auto = []
        print(f"! ΑΣ ΠΑΟΚ (ατομικά): {e}", file=sys.stderr)
    try:
        admin = admin_events()
    except Exception as e:
        admin = [{"id": x["id"], **{k: x[k] for k in FIELDS if k in x}} for x in previous.get("events", [])
                 if x.get("source") == "admin"]  # μένουν οι προηγούμενες της φόρμας
        print(f"  ! καταχωρίσεις διαχειριστή (ατομικά): {e}", file=sys.stderr)
    events = merge(auto, previous.get("events", []), admin)
    notices, new_notices = federation_notices(previous)
    old_ids = {e["id"] for e in previous.get("events", [])} | set(previous.get("hiddenSeen", []))
    today = dt.datetime.now(ATHENS).date()
    new_events = [e for e in events if e["id"] not in old_ids and e.get("source") == "acpaok"
                  and dt.date.fromisoformat(e["end"]) >= today]
    for e in events:
        print(f"  {e['start']}–{e['end']} {SPORTS[e['sport']]['name']}: {e['title']}{' (ΑμεΑ)' if e.get('para') else ''}")
    for n in new_notices:
        print(f"  νέα ανακοίνωση {n['name']}: {n['title']}")
    if DRY:
        return 0 if ok else 1
    data = {
        "sports": [{"key": k, "emoji": v["emoji"], "name": v["name"]} for k, v in SPORTS.items()],
        "events": events,
        "notices": notices,
        "seenNotices": previous.get("seenNotices", []),
        # Αυτόματες που έκρυψε ο διαχειριστής: να μη στέλνουν ξανά «Νέα διοργάνωση».
        "hiddenSeen": sorted(set(previous.get("hiddenSeen", [])) | {a["id"] for a in admin if a.get("hidden")}),
    }
    write_if_changed(DATA_PATH, json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                     ignore=lambda s: json.dumps(json.loads(s), sort_keys=True))
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_if_changed(OUT_DIR / "all-events.ics", build_ics("ΠΑΟΚ – Ατομικά αθλήματα", events, stamp))
    for key, sp in SPORTS.items():
        write_if_changed(OUT_DIR / f"{key}-events.ics",
                         build_ics(f"ΠΑΟΚ {sp['name']}", [e for e in events if e["sport"] == key], stamp))
    if not first_run:  # την πρώτη φορά όλα είναι «νέα»: καμία ειδοποίηση
        notify_admin(new_events, new_notices)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
