#!/usr/bin/env python3
"""Τρόπαια ανά τμήμα (docs/trophies.json), για τις καρτέλες «Τρόπαια» και τη σελίδα #/trophies.

Πηγές:
  - ΑΣ ΠΑΟΚ (acpaok.gr): η «ΤΡΟΠΑΙΟΘΗΚΗ» στη σελίδα κάθε τμήματος (βόλεϊ, χάντμπολ, ποδόσφαιρο γυναικών,
    σάλας, πάλη, άρση βαρών, κολύμβηση…). Διαβάζεται σε κάθε ενημέρωση, άρα ένας νέος τίτλος μπαίνει μόνος του
    όταν τον γράψει ο σύλλογος.
  - ΠΑΕ (paokfc.gr) και ΚΑΕ (paokbc.gr): σταθερή λίστα εδώ (STATIC), από τις σελίδες τίτλων των δύο ΠΑΕ/ΚΑΕ·
    για νέο τίτλο, μία χρονιά στη λίστα.
  - Ακαδημίες: STATIC, όπου υπάρχουν τεκμηριωμένοι τίτλοι.

Οι διακρίσεις (2η/3η θέση) κρατιούνται χωριστά («places»). Αν μια σελίδα δεν απαντήσει, μένει ό,τι υπήρχε.

    python3 trophies.py         ενημέρωση του docs/trophies.json
    DRY=1 python3 trophies.py   μόνο εμφάνιση
"""
from __future__ import annotations

import json
import os
import re
import sys

from build_calendars import OUT_DIR, clean, fetch, write_if_changed

PATH = OUT_DIR / "trophies.json"
DRY = os.environ.get("DRY") == "1"

# Σελίδες της ΑΣ ΠΑΟΚ (WordPress pages) → τμήμα του PAOKalendar. «event:» = ατομικό άθλημα (events.py).
ACPAOK_PAGES = {
    1188: "volley", 1913: "volley-women", 1920: "handball", 1996: "handball-women", 2025: "football-women",
    2017: "futsal", 2040: "event:wrestling", 2042: "event:weightlifting", 2030: "event:swimming",
    2077: "event:boxing", 2056: "event:taekwondo", 2052: "event:sambo", 2046: "event:cycling", 2037: "event:finswimming",
}
ACPAOK_URL = "https://acpaok.gr/wp-json/wp/v2/pages/{id}?_fields=id,link,content"

# Ποδόσφαιρο και μπάσκετ ανδρών (ΠΑΕ, ΚΑΕ): σταθερά. Σεζόν όπως «1975-76».
STATIC = {
    "football": [
        {"name": "Πρωτάθλημα Ελλάδας", "years": ["1975-76", "1984-85", "2018-19", "2023-24"]},
        {"name": "Κύπελλο Ελλάδας", "years": ["1971-72", "1973-74", "2000-01", "2002-03", "2016-17", "2017-18", "2018-19",
                                             "2020-21"]},
        {"name": "Πρωτάθλημα ΕΠΣ Μακεδονίας", "years": ["1936-37", "1947-48", "1949-50", "1953-54", "1954-55", "1955-56",
                                                       "1956-57"], "note": "Τοπικό, πριν από την Α' Εθνική"},
        {"name": "Πρωτάθλημα ΕΠΣ Μακεδονίας-Θράκης", "years": ["1939-40"], "note": "Τοπικό"},
    ],
    "basketball": [
        {"name": "Πρωτάθλημα Ελλάδας", "years": ["1958-59", "1991-92"]},
        {"name": "Κύπελλο Ελλάδας", "years": ["1983-84", "1994-95", "1998-99"]},
        {"name": "Κύπελλο Κυπελλούχων Ευρώπης (Saporta)", "years": ["1990-91"]},
        {"name": "Κύπελλο Κόρατς", "years": ["1993-94"]},
    ],
    # Ακαδημίες ποδοσφαίρου (Wikipedia, PAOK Academy και PAOK FC (women)).
    "football-u19": [{"name": "Πρωτάθλημα Super League Κ19", "years": ["2002-03", "2006-07", "2013-14", "2017-18", "2018-19",
                                                                        "2019-20", "2020-21", "2025-26"]}],
    "football-u17": [{"name": "Πρωτάθλημα Super League Κ17", "years": ["2012-13", "2015-16", "2019-20", "2021-22", "2023-24",
                                                                        "2024-25"]}],
    "football-u15": [{"name": "Πρωτάθλημα Super League Κ15", "years": ["2014-15", "2016-17", "2018-19", "2022-23", "2023-24",
                                                                        "2024-25"]}],
    "football-women-u17": [{"name": "Πανελλήνιο Πρωτάθλημα Υποδομών Κ17", "years": ["2023", "2024"]}],
}
SOURCES = [
    {"name": "ΑΣ ΠΑΟΚ (τροπαιοθήκη τμημάτων)", "url": "https://acpaok.gr/"},
    {"name": "ΠΑΕ ΠΑΟΚ", "url": "https://www.paokfc.gr/istoria/oi-titloi/"},
    {"name": "ΚΑΕ ΠΑΟΚ", "url": "https://www.paokbc.gr/el/istoria/tropaia"},
    {"name": "Wikipedia (ακαδημίες)", "url": "https://en.wikipedia.org/wiki/PAOK_Academy"},
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


def trophy_block(page_html: str) -> str | None:
    text = clean(page_html)
    i = text.find("ΤΡΟΠΑΙΟΘΗΚΗ")
    if i < 0:
        return None
    j = text.find("ΡΟΗ ΕΙΔΗΣΕΩΝ", i)
    return text[i + len("ΤΡΟΠΑΙΟΘΗΚΗ"):j if j > 0 else None].strip()


def main() -> int:
    previous = json.loads(PATH.read_text(encoding="utf-8")) if PATH.exists() else {}
    sections: dict[str, list[dict]] = {k: [dict(t) for t in v] for k, v in STATIC.items()}
    places: dict[str, list[dict]] = {}
    notes: dict[str, str] = {}
    failures = []
    for pid, key in ACPAOK_PAGES.items():
        try:
            page = json.loads(fetch(ACPAOK_URL.format(id=pid)))
            block = trophy_block((page.get("content") or {}).get("rendered", ""))
        except Exception as e:
            failures.append(f"{key}: {e}")
            print(f"! τρόπαια {key}: {e}", file=sys.stderr)
            if key in previous.get("sections", {}):
                sections[key] = previous["sections"][key]
                if key in previous.get("places", {}):
                    places[key] = previous["places"][key]
            continue
        if not block:
            continue
        t, p, n = parse_trophy_text(block)
        if t:
            sections[key] = t
        if p:
            places[key] = p
        if n:
            notes[key] = " · ".join(n)
    for key in sections:
        sections[key].sort(key=sort_key)
    for key, lst in sections.items():
        print(f"{key}: " + "; ".join(f"{t['name']} {len(t['years'])}" for t in lst))
    from events import SPORTS
    labels = {f"event:{k}": f"{v['emoji']} {v['name']}" for k, v in SPORTS.items()}
    data = {"sections": sections, "places": places, "notes": notes, "labels": labels, "sources": SOURCES}
    if not DRY:
        write_if_changed(PATH, json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    return 1 if failures and len(failures) == len(ACPAOK_PAGES) else 0


if __name__ == "__main__":
    sys.exit(main())
