#!/usr/bin/env python3
"""Τρόπαια ανά τμήμα (docs/trophies.json), για τις καρτέλες «Τρόπαια» και τη σελίδα #/trophies.

Πηγές:
  - ΑΣ ΠΑΟΚ (acpaok.gr): η «ΤΡΟΠΑΙΟΘΗΚΗ» στη σελίδα κάθε τμήματος (βόλεϊ, χάντμπολ, ποδόσφαιρο γυναικών,
    σάλας, πάλη, άρση βαρών, κολύμβηση…). Διαβάζεται σε κάθε ενημέρωση, άρα ένας νέος τίτλος μπαίνει μόνος του
    όταν τον γράψει ο σύλλογος.
  - Τα επίσημα άρθρα τίτλων της ΑΣ ΠΑΟΚ (OFFICIAL): ομαδικά, ατομικά, ακαδημίες. Μετρούν πρώτα.
  - Τα αποτελέσματα των ατομικών αθλημάτων (docs/events.json, events.py): «🏆 1η θέση, κατηγορία Νέων Ανδρών»
    σε Πανελλήνιο Πρωτάθλημα = τίτλος εκείνης της χρονιάς, αμέσως. Μέχρι να τον γράψει και η ΑΣ ΠΑΟΚ στην
    τροπαιοθήκη μένει «σε αναμονή» (pending στο json)· όταν εμφανιστεί εκεί, ο διαχειριστής παίρνει ειδοποίηση.

Οι διακρίσεις (2η/3η θέση) κρατιούνται χωριστά («places»). Αν μια σελίδα δεν απαντήσει, μένει ό,τι υπήρχε.

    python3 trophies.py         ενημέρωση του docs/trophies.json
    DRY=1 python3 trophies.py   μόνο εμφάνιση
"""
from __future__ import annotations

import json
import os
import re
import sys

from build_calendars import OUT_DIR, clean, fetch, plain, write_if_changed

PATH = OUT_DIR / "trophies.json"
DRY = os.environ.get("DRY") == "1"

# Σελίδες της ΑΣ ΠΑΟΚ (WordPress pages) → τμήμα του PAOKalendar. «event:» = ατομικό άθλημα (events.py).
ACPAOK_PAGES = {
    1188: "volley", 1913: "volley-women", 1920: "handball", 1996: "handball-women", 2025: "football-women",
    2017: "futsal", 2040: "event:wrestling", 2042: "event:weightlifting", 2030: "event:swimming",
    2077: "event:boxing", 2056: "event:taekwondo", 2052: "event:sambo", 2046: "event:cycling", 2037: "event:finswimming",
}
ACPAOK_URL = "https://acpaok.gr/wp-json/wp/v2/pages/{id}?_fields=id,link,content"

# Τα επίσημα άρθρα της ΑΣ ΠΑΟΚ για τους τίτλους (2026): «81 τίτλοι στα 100 χρόνια» (ομαδικά), «39 τίτλοι στα άλλα
# αθλήματα» (ατομικά) και «58 τίτλοι ακαδημιών στα ομαδικά αθλήματα». Χρονιές όπως στα άρθρα (η χρονιά του τίτλου).
# Μετρούν πάνω από την τροπαιοθήκη των σελίδων· νέος τίτλος = μία χρονιά εδώ (ή νέο άρθρο του συλλόγου).
def _t(name, *years, note=None):
    d = {"name": name, "years": [str(y) for y in years]}
    if note:
        d["note"] = note
    return d


OFFICIAL = {
    # Ομαδικά (81)
    "football": [_t("Πρωτάθλημα Ελλάδας", 1976, 1985, 2019, 2024),
                 _t("Κύπελλο Ελλάδας", 1972, 1974, 2001, 2003, 2017, 2018, 2019, 2021)],
    "football-women": [_t("Πρωτάθλημα Ελλάδας", 2002, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2015, 2016, 2017,
                          2018, 2019, 2020, 2021, 2022, 2023, 2024, 2026),
                       _t("Κύπελλο Ελλάδας", 2002, 2013, 2014, 2015, 2016, 2017, 2024, 2026)],
    "basketball": [_t("Πρωτάθλημα Ελλάδας", 1959, 1992), _t("Κύπελλο Ελλάδας", 1984, 1995, 1999),
                   _t("Κύπελλο Κυπελλούχων Ευρώπης", 1991), _t("Κύπελλο Κόρατς", 1994)],
    "volley": [_t("Πρωτάθλημα Ελλάδας", 2015, 2016, 2017), _t("Κύπελλο Ελλάδας", 2015, 2018, 2019, 2022, 2023),
               _t("Σούπερ Καπ Ελλάδας", 2023)],
    "volley-women": [_t("Κύπελλο Ελλάδας", 2021)],
    "handball": [_t("Πρωτάθλημα Ελλάδας", 2009, 2010, 2015), _t("Κύπελλο Ελλάδας", 2012, 2015, 2017, 2024)],
    "handball-women": [_t("Πρωτάθλημα Ελλάδας", 2013, 2019, 2020, 2021, 2022, 2023, 2026),
                       _t("Κύπελλο Ελλάδας", 2014, 2016, 2019, 2020, 2021, 2022, 2024, 2026),
                       _t("Σούπερ Καπ Ελλάδας", 2023, 2026)],
    # Ατομικά και άλλα αθλήματα (39)
    "event:wrestling": [_t("Πρωτάθλημα Ελλάδας Ανδρών", 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026)],
    "event:weightlifting": [_t("Πρωτάθλημα Ελλάδας Ανδρών", 2006, 2017, 2019, 2021, 2022, 2024, 2025)],
    "event:swimming": [_t("Πρωτάθλημα Ελλάδας OPEN", 1987), _t("Πρωτάθλημα Ελλάδας Γυναικών", 1986, 1987, 1988, 1999, 2000)],
    "event:judo": [_t("Πρωτάθλημα Ελλάδας Μεικτό", 2023), _t("Πρωτάθλημα Ελλάδας Ανδρών", 2019, 2021),
                   _t("Πρωτάθλημα Ελλάδας Γυναικών", 2019, 2022)],
    "event:athletics": [_t("Πρωτάθλημα Ελλάδας Γυναικών", 1976, 1977, 1982),
                        _t("Πρωτάθλημα Ελλάδας Ανώμαλου Δρόμου Γυναικών", 1968, 1974)],
    "event:boxing": [_t("Πρωτάθλημα Ελλάδας Ανδρών", 2003, 2007)],
    "event:hockey": [_t("Βαλκανικό Κύπελλο Επί Πάγου Ανδρών", 2007), _t("Πρωτάθλημα Ελλάδας Ρόλερ Ανδρών", 2008)],
    "event:artistic-swimming": [_t("Πρωτάθλημα Ελλάδας Γυναικών", 1993)],
    "event:cycling": [_t("Πρωτάθλημα Ελλάδας Ορεινής Ανδρών", 2002)],
    # Ακαδημίες ομαδικών (58)
    "football-u19": [_t("Πρωτάθλημα Ελλάδας Κ-19", 2003, 2007, 2014, 2018, 2019, 2020, 2021, 2026),
                     _t("Κύπελλο Ελλάδας Κ-19", 2025, 2026)],
    "football-u17": [_t("Πρωτάθλημα Ελλάδας Κ-17", 2013, 2016, 2020, 2022, 2024, 2025)],
    "football-u15": [_t("Πρωτάθλημα Ελλάδας Κ-15", 2015, 2017, 2019, 2023, 2024, 2025, 2026)],
    "academy:football": [_t("Πρωτάθλημα Ελλάδας Εφήβων", 1969, 1971, 1973, 1979),
                         _t("Πρωτάθλημα Ελλάδας Ερασιτεχνών", 1981, 1986), _t("Κύπελλο Ελλάδας Ερασιτεχνών", 1975)],
    "academy:football-women": [_t("Πρωτάθλημα Ελλάδας Β' Ομάδων", 2024)],
    "basketball-u18": [_t("Πρωτάθλημα Ελλάδας Εφήβων", 1981, 1990, 1994, 2002)],
    "basketball-u16": [_t("Πρωτάθλημα Ελλάδας Παίδων", 1978, 1985, 1988, 1991, 2013, 2017)],
    "basketball-women-u18": [_t("Πρωτάθλημα Ελλάδας Νεανίδων", 2013, 2026)],
    "basketball-women-u16": [_t("Πρωτάθλημα Ελλάδας Κορασίδων", 2010, 2011)],
    "volley-u18": [_t("Πρωτάθλημα Ελλάδας Εφήβων", 1983)],
    "academy:volley": [_t("Πρωτάθλημα Ελλάδας Παίδων", 2025)],
    "volley-women-u20": [_t("Πρωτάθλημα Ελλάδας Νεανίδων", 2019, 2020, 2022)],
    "academy:waterpolo": [_t("Πρωτάθλημα Ελλάδας Νέων Ανδρών", 2015, 2022), _t("Πρωτάθλημα Ελλάδας Εφήβων", 2019, 2022, 2023),
                          _t("Πρωτάθλημα Ελλάδας Παίδων", 2017)],
    "academy:waterpolo-women": [_t("Πρωτάθλημα Ελλάδας Νεανίδων", 2004), _t("Πρωτάθλημα Ελλάδας Κορασίδων", 2022)],
    "academy:beach-handball": [_t("Πρωτάθλημα Ελλάδας Παίδων", 2018)],
}
# Όσα δεν είναι στα άρθρα αλλά είναι τεκμηριωμένα (τοπικά πρωταθλήματα πριν από την Α' Εθνική, Wikipedia).
EXTRA = {
    "football": [_t("Πρωτάθλημα ΕΠΣ Μακεδονίας", "1936-37", "1947-48", "1949-50", "1953-54", "1954-55", "1955-56", "1956-57",
                    note="Τοπικό, πριν από την Α' Εθνική"),
                 _t("Πρωτάθλημα ΕΠΣ Μακεδονίας-Θράκης", "1939-40", note="Τοπικό")],
}
LABELS = {
    "event:hockey": "🏒 Χόκεϊ", "event:artistic-swimming": "🤽 Καλλιτεχνική κολύμβηση",
    "academy:football": "⚽ Ποδόσφαιρο (παλιές κατηγορίες)", "academy:football-women": "⚽ Ποδόσφαιρο γυναικών (Β' ομάδα)",
    "academy:volley": "🏐 Βόλεϊ αγοριών", "academy:waterpolo": "🤽 Πόλο ανδρών", "academy:waterpolo-women": "🤽 Πόλο γυναικών",
    "academy:beach-handball": "🤾 Μπιτς χάντμπολ",
}
ARTICLES = [
    {"name": "ΑΣ ΠΑΟΚ: 81 τίτλοι στα 100 χρόνια",
     "url": "https://acpaok.gr/%cf%80-%ce%b1-%ce%bf-%ce%ba-81-%cf%84%ce%af%cf%84%ce%bb%ce%bf%ce%b9-%cf%83%cf%84%ce%b1-100-%cf%87%cf%81%cf%8c%ce%bd%ce%b9%ce%b1/"},
    {"name": "ΑΣ ΠΑΟΚ: 39 τίτλοι στα άλλα αθλήματα",
     "url": "https://acpaok.gr/%cf%80-%ce%b1-%ce%bf-%ce%ba-39-%cf%84%ce%af%cf%84%ce%bb%ce%bf%ce%b9-%cf%83%cf%84%ce%b1-%ce%ac%ce%bb%ce%bb%ce%b1-%ce%b1%ce%b8%ce%bb%ce%ae%ce%bc%ce%b1%cf%84%ce%b1/"},
    {"name": "ΑΣ ΠΑΟΚ: 58 τίτλοι ακαδημιών στα ομαδικά",
     "url": "https://acpaok.gr/%cf%80-%ce%b1-%ce%bf-%ce%ba-58-%cf%84%ce%af%cf%84%ce%bb%ce%bf%ce%b9-%ce%b1%ce%ba%ce%b1%ce%b4%ce%b7%ce%bc%ce%b9%cf%8e%ce%bd-%cf%83%cf%84%ce%b1-%ce%bf%ce%bc%ce%b1%ce%b4%ce%b9%ce%ba%ce%ac-%ce%b1%ce%b8/"},
]
SOURCES = ARTICLES + [
    {"name": "ΑΣ ΠΑΟΚ (τροπαιοθήκη τμημάτων)", "url": "https://acpaok.gr/"},
    {"name": "Wikipedia (τοπικά πρωταθλήματα)", "url": "https://en.wikipedia.org/wiki/PAOK_FC"},
]

_YEAR = r"(?:19|20)\d\d(?:\s*[-–/]\s*(?:19|20)?\d\d)?"


def season(y: str) -> str:
    """«2001-2002», «2001/02», «2023-2024» → «2001-02»· σκέτη χρονιά μένει ίδια."""
    m = re.fullmatch(r"((?:19|20)\d\d)\s*[-–/]\s*((?:19|20)?\d\d)", y.strip())
    return f"{m[1]}-{m[2][-2:]}" if m else y.strip()


def tidy(name: str) -> str:
    n = re.sub(r"\s+", " ", name).strip(" .,:–-")
    n = re.sub(r"^\d+\s+(?=[Α-ΩA-Z])", "", n)  # «7 Πρωταθλήματα…» → «Πρωταθλήματα…»
    n = re.sub(r"^Πρωταθλητ(?:ές|ής|ρια|ριες)\s+Ελλάδο?ς", "Πρωτάθλημα Ελλάδας", n)
    n = re.sub(r"^Πρωταθλήματα\s+Ελλάδο?ς", "Πρωτάθλημα Ελλάδας", n)
    n = re.sub(r"^Πανελλήνια πρωταθλήματα", "Πανελλήνιο πρωτάθλημα", n)
    n = re.sub(r"^Πανελλήνιο πρωτάθλημα", "Πανελλήνιο Πρωτάθλημα", n)
    # «Πανελλήνιο Πρωτάθλημα νέων ανδρών» → «… Νέων Ανδρών» (όπως οι υπόλοιποι τίτλοι).
    n = re.sub(r"^(Πανελλήνιο Πρωτάθλημα|Πρωτάθλημα Ελλάδας) (.+)$",
               lambda m: m[1] + " " + " ".join(w[:1].upper() + w[1:] for w in m[2].split()), n)
    n = re.sub(r"\bΕλλάδος\b", "Ελλάδας", n)
    return n[:1].upper() + n[1:]


def parse_trophy_text(text: str) -> tuple[list[dict], list[dict], list[str]]:
    """Το κείμενο της «ΤΡΟΠΑΙΟΘΗΚΗΣ» → (τίτλοι, διακρίσεις 2η/3η θέση, σημειώσεις).

    Δύο μορφές: «Κύπελλο Ελλάδος 2001-2002 Πρωτάθλημα Ελλάδος 2001-2002 …» και
    «7 Πρωταθλήματα Ελλάδος Ανδρών (2006, 2017, …) … 2η θέση Άνδρες (2004, 2005)»."""
    titles: dict[str, list[str]] = {}
    places: dict[str, list[str]] = {}
    notes: list[str] = []

    def add(name: str, years: list[str]) -> None:
        name = tidy(name)
        if not name or not years:
            return
        if re.match(r"^\d\s*η\s+θ[εέ]ση", name, re.I):
            target = places
            name = re.sub(r"^(\d)\s*η\s+θ[εέ]ση", r"\1η θέση", name, flags=re.I)
        else:
            target = titles
        lst = target.setdefault(name, [])
        lst += [season(y) for y in years if season(y) not in lst]

    t = re.sub(r"\s+", " ", text).strip()
    t = re.sub(r"Πανελλήνιες Θέσεις", " ", t)
    # «Συμμετοχή στο … το 2017.»: σημείωση, όχι τίτλος.
    for m in re.finditer(r"(Συμμετοχή[^.]*?(?:19|20)\d\d)\.?", t):
        notes.append(m[1].strip())
    t = re.sub(r"Συμμετοχή[^.]*?(?:19|20)\d\d\.?", " ", t)
    # Μορφή με παρενθέσεις.
    for m in re.finditer(r"([^()]+?)\s*\(((?:\s*(?:19|20)\d\d\s*,?)+)\)\s*(?:και\s+)?", t):
        add(m[1], re.findall(r"(?:19|20)\d\d", m[2]))
    t = re.sub(r"[^()]+?\s*\(((?:\s*(?:19|20)\d\d\s*,?)+)\)\s*(?:και\s+)?", " ", t)
    # Μορφή «Όνομα χρονιά Όνομα χρονιά …» (και κολλημένα: «Εφήβων 20253η θέση»).
    t = re.sub(r"((?:19|20)\d\d)(\d\s*η\s+θ)", r"\1 \2", t)
    for m in re.finditer(r"\s*(.+?)\s+(" + _YEAR + r")(?=\s|$)", t):
        add(m[1], [m[2].replace(" ", "")])

    def out(d: dict[str, list[str]]) -> list[dict]:
        return [{"name": k, "years": v} for k, v in d.items()]
    return out(titles), out(places), notes


ORDER = ["Πρωτάθλημα Ελλάδας", "Κύπελλο Ελλάδας", "Σούπερ Καπ", "Λιγκ Καπ", "Κύπελλο", "Πρωτάθλημα", "Πανελλήνιο"]


def sort_key(t: dict) -> tuple:
    name = t["name"]
    rank = next((i for i, p in enumerate(ORDER) if name.startswith(p)), len(ORDER))
    youth = bool(re.search(r"Παίδ|Εφήβ|Παμπαίδ|Νέ(ων|οι)|Νεαν|Κορασ|U\d|Κ\d\d", name))
    return (youth, rank, name)


# Κατηγορίες ηλικίας/φύλου των πρωταθλημάτων (οι μεγαλύτερες πρώτα, για το ταίριασμα).
CATEGORIES = ["Νέων Ανδρών", "Νέων Γυναικών", "Παμπαίδων", "Παγκορασίδων", "Εφήβων", "Νεανίδων", "Παίδων",
              "Κορασίδων", "Ανδρών", "Γυναικών"]
_NATIONAL = re.compile(r"ΠΑΝΕΛΛΗΝΙ\w* ΠΡΩΤΑΘΛΗΜΑ|ΠΡΩΤΑΘΛΗΜΑ\w* ΕΛΛΑΔ")
_NOT_NATIONAL = re.compile(r"ΒΑΛΚΑΝ|ΕΥΡΩΠ|ΠΑΓΚΟΣΜ|ΜΕΣΟΓΕΙ|ΚΥΠΕΛΛ|ΔΙΕΘΝ|ΣΧΟΛΙΚ|ΠΕΡΙΦΕΡΕΙΑΚ|ΒΕΤΕΡΑΝ|MASTERS", re.I)
_WIN = re.compile(r"^🏆\s*1η θέση(?:,\s*κατηγορία\s+([^(]+?))?(?:\s+ομαδικά)?\s*(?:\(|$)")


def category(text: str) -> str | None:
    """Η κατηγορία (ως plain) στο τέλος ενός ονόματος/κειμένου: «… Νέων Ανδρών» → «ΝΕΩΝ ΑΝΔΡΩΝ»."""
    up = plain(text)
    for c in CATEGORIES:
        if re.search(r"(?:^|\s)" + plain(c) + r"(?:\s|$)", up):
            return plain(c)
    return None


def name_category(name: str) -> str | None:
    """Η κατηγορία ενός τίτλου πρωταθλήματος Ελλάδας («Πανελλήνιο Πρωτάθλημα Εφήβων» → «ΕΦΗΒΩΝ»).

    Μόνο όταν ό,τι μένει μετά το «Πρωτάθλημα Ελλάδας»/«Πανελλήνιο Πρωτάθλημα» είναι σκέτη κατηγορία
    («Πρωτάθλημα Ελλάδας Ανώμαλου Δρόμου Γυναικών» δεν είναι το ίδιο με το «… Γυναικών»)."""
    up = plain(name)
    m = re.fullmatch(r"(?:ΠΡΩΤΑΘΛΗΜΑ ΕΛΛΑΔΑΣ|ΠΑΝΕΛΛΗΝΙΟ ΠΡΩΤΑΘΛΗΜΑ) (.+)", up)
    return m[1] if m and m[1] in {plain(c) for c in CATEGORIES} else None


def titles_from_events(events: list[dict]) -> list[tuple[str, str, str, str]]:
    """(τμήμα, κατηγορία plain, κατηγορία όπως γράφεται, χρονιά) για κάθε 1η θέση σε Πανελλήνιο Πρωτάθλημα."""
    out = []
    for e in events:
        if e.get("para") or not e.get("sport") or not e.get("end"):
            continue
        title = plain(e.get("title", ""))
        if not _NATIONAL.search(title) or _NOT_NATIONAL.search(title):
            continue
        for line in (e.get("results") or "").splitlines():
            m = _WIN.match(line.strip())
            if not m:
                continue
            cat = category(m[1] or "") or category(e.get("title", ""))
            if not cat:
                continue
            shown = next(c for c in CATEGORIES if plain(c) == cat)
            item = (f"event:{e['sport']}", cat, shown, e["end"][:4])
            if item not in out:
                out.append(item)
    return out


def add_event_titles(sections: dict[str, list[dict]], events: list[dict], skip: set[str] = frozenset()) -> dict:
    """Βάζει στα τρόπαια τους τίτλους από τα αποτελέσματα. Επιστρέφει τις χρονιές σε αναμονή
    {τμήμα: [{"name", "year"}]}: όσες δεν τις έχει (ακόμα) η τροπαιοθήκη/η σταθερή λίστα.

    Ένας τίτλος της τροπαιοθήκης με την ίδια κατηγορία και χρονιά μετρά ως ο ίδιος, όποιο κι αν είναι το
    όνομά του («Πρωτάθλημα Ελλάδας Παίδων» = «Πανελλήνιο Πρωτάθλημα Παίδων»). skip: τμήματα που δεν
    διαβάστηκαν τώρα (κρατούν ό,τι είχαν, και την αναμονή τους)."""
    pending: dict[str, list[dict]] = {}
    for key, cat, shown, year in titles_from_events(events):
        if key in skip:
            continue
        lst = sections.setdefault(key, [])
        same = [t for t in lst if name_category(t["name"]) == cat]
        if any(year in t["years"] for t in same):
            continue  # το έχει ήδη η ΑΣ ΠΑΟΚ (ή η σταθερή λίστα)
        if same:
            target = same[0]
        else:
            name = ("Πρωτάθλημα Ελλάδας " if cat in ("ΑΝΔΡΩΝ", "ΓΥΝΑΙΚΩΝ") else "Πανελλήνιο Πρωτάθλημα ") + shown
            target = {"name": name, "years": []}
            lst.append(target)
        target["years"] = sorted(target["years"] + [year])
        pending.setdefault(key, []).append({"name": target["name"], "year": year})
    return pending


def notify_pending(old: dict, new: dict, labels: dict) -> None:
    """Ειδοποίηση στον διαχειριστή: νέος τίτλος από αποτέλεσμα, και όταν τον γράψει και η ΑΣ ΠΑΟΚ."""
    if DRY:
        return
    def flat(d):
        return {(k, x["name"], x["year"]) for k, v in d.items() for x in v}
    added, confirmed = flat(new) - flat(old), flat(old) - flat(new)
    if not added and not confirmed:
        return
    import notify
    import watchdog
    for key, name, year in sorted(added):
        notify._push([watchdog.TOPIC], f"🏆 Νέος τίτλος: {labels.get(key, key)}",
                     f"{name} {year}: μπήκε στα τρόπαια από το αποτέλεσμα. Αναμένεται και στην τροπαιοθήκη της ΑΣ ΠΑΟΚ.",
                     f"/#/trophies", tag=f"trophy-{key}-{year}")
    for key, name, year in sorted(confirmed):
        notify._push([watchdog.TOPIC], f"✅ Τίτλος επιβεβαιώθηκε: {labels.get(key, key)}",
                     f"{name} {year}: τον έγραψε και η ΑΣ ΠΑΟΚ στην τροπαιοθήκη.", f"/#/trophies",
                     tag=f"trophy-{key}-{year}")


def trophy_block(page_html: str) -> str | None:
    text = clean(page_html)
    i = text.find("ΤΡΟΠΑΙΟΘΗΚΗ")
    if i < 0:
        return None
    j = text.find("ΡΟΗ ΕΙΔΗΣΕΩΝ", i)
    return text[i + len("ΤΡΟΠΑΙΟΘΗΚΗ"):j if j > 0 else None].strip()


def main() -> int:
    previous = json.loads(PATH.read_text(encoding="utf-8")) if PATH.exists() else {}
    sections: dict[str, list[dict]] = {k: [dict(t) for t in v] for k, v in OFFICIAL.items()}
    for k, v in EXTRA.items():
        sections.setdefault(k, []).extend(dict(t) for t in v)
    places: dict[str, list[dict]] = {}
    notes: dict[str, str] = {}
    failures = []
    unread: set[str] = set()
    for pid, key in ACPAOK_PAGES.items():
        try:
            page = json.loads(fetch(ACPAOK_URL.format(id=pid)))
            block = trophy_block((page.get("content") or {}).get("rendered", ""))
        except Exception as e:
            failures.append(f"{key}: {e}")
            print(f"! τρόπαια {key}: {e}", file=sys.stderr)
            unread.add(key)
            if key in previous.get("sections", {}):
                sections[key] = previous["sections"][key]
                if key in previous.get("places", {}):
                    places[key] = previous["places"][key]
            continue
        if not block:
            continue
        t, p, n = parse_trophy_text(block)
        if t and key not in OFFICIAL:
            sections[key] = t
        elif t and key.startswith("event:"):  # ατομικά: και οι τίτλοι μικρών ηλικιών της σελίδας
            have = {x["name"] for x in sections[key]}
            # Οι τίτλοι Ανδρών/Γυναικών είναι ήδη στη σταθερή λίστα· όχι όμως οι «Νέων Ανδρών» κ.λπ.
            sections[key] += [x for x in t if x["name"] not in have
                              and name_category(x["name"]) not in ("ΑΝΔΡΩΝ", "ΓΥΝΑΙΚΩΝ")
                              and not re.search(r"(?<!Νέων )Ανδρών$|(?<!Νέων )Γυναικών$", x["name"])]
        if p:
            places[key] = p
        if n:
            notes[key] = " · ".join(n)
    events_path = OUT_DIR / "events.json"
    events = json.loads(events_path.read_text(encoding="utf-8")).get("events", []) if events_path.exists() else []
    pending = add_event_titles(sections, events, skip=unread)
    for key in unread:  # δεν διαβάστηκε η σελίδα: η αναμονή μένει όπως ήταν
        if key in previous.get("pending", {}):
            pending[key] = previous["pending"][key]
    for key, lst in pending.items():
        print(f"  σε αναμονή (ΑΣ ΠΑΟΚ) {key}: " + "; ".join(f"{x['name']} {x['year']}" for x in lst))
    for key in sections:
        sections[key].sort(key=sort_key)
    for key, lst in sections.items():
        print(f"{key}: " + "; ".join(f"{t['name']} {len(t['years'])}" for t in lst))
    from events import SPORTS
    labels = {f"event:{k}": f"{v['emoji']} {v['name']}" for k, v in SPORTS.items()} | LABELS
    data = {"sections": sections, "places": places, "notes": notes, "labels": labels, "sources": SOURCES,
            "pending": pending}
    if "pending" in previous:  # την πρώτη φορά (χωρίς προηγούμενη αναμονή) καμία ειδοποίηση για τα παλιά
        notify_pending(previous.get("pending", {}), pending, labels)
    if not DRY:
        write_if_changed(PATH, json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    return 1 if failures and len(failures) == len(ACPAOK_PAGES) else 0


if __name__ == "__main__":
    sys.exit(main())
