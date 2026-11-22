#!/usr/bin/env python3
"""Φτιάχνει ημερολόγια iCal (.ics) και δεδομένα ιστοσελίδας με τους αγώνες των τμημάτων του ΠΑΟΚ.

Για κάθε τμήμα γράφει δύο ημερολόγια στο docs/ (εντός και εκτός έδρας) και όλους
τους αγώνες στο docs/matches.json, που διαβάζει η σελίδα docs/index.html.
Όπου η ώρα ενός αγώνα δεν έχει οριστεί ακόμα, ο αγώνας μπαίνει στις 18:00 (ώρα Ελλάδας)
με την ένδειξη «(ώρα αναμένεται)».

Πηγές:
  Ποδόσφαιρο:          ESPN (Super League, Ευρώπη), ΕΠΟ (Κύπελλο Ελλάδας)
  Ποδόσφαιρο γυναικών: ΕΠΟ (Α' Εθνική, Κύπελλο), ESPN (UEFA)
  Μπάσκετ:             esake.gr (Basket League), Euroleague API (EuroCup)
  Μπάσκετ γυναικών:    basket.gr (Women's Basketball League 1)
  Βόλεϊ:               volleyleague.gr (Volley League, League Cup), Data Project της ΕΟΠΕ (Κύπελλο), CEV
  Βόλεϊ γυναικών:      Data Project της ΕΟΠΕ (Volley League Women, Κύπελλο), CEV
  Χάντμπολ:            statistics.handball.org.gr (Handball Premier, Α1 Γυναικών, Κύπελλα), EHF
  Πόλο:                waterpololeague.gr (ανδρών, γυναικών), European Aquatics (ευρωπαϊκά κύπελλα)
  Ποδόσφαιρο σάλας:    epssalas.gr (Futsal Super League· οι ώρες συνήθως από την ΑΣ ΠΑΟΚ)

Γράφει επίσης βαθμολογίες στο docs/standings.json (βλ. standings.py) και στέλνει
ειδοποιήσεις για νέους αγώνες, αλλαγές ώρας και αποτελέσματα (βλ. notify.py),
όταν υπάρχει η μεταβλητή περιβάλλοντος PUSH=1.

Αν μια πηγή αποτύχει, τα αρχεία του τμήματος μένουν όπως ήταν και το script
τερματίζει με σφάλμα, ώστε να φανεί στο GitHub Actions.
Χρησιμοποιεί μόνο τη βασική βιβλιοθήκη της Python.
"""
from __future__ import annotations

import collections
import os
import datetime as dt
import hashlib
import html
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

ATHENS = ZoneInfo("Europe/Athens")
DEFAULT_TIME = dt.time(18, 0)
GAME_LENGTH = dt.timedelta(hours=2)
OUT_DIR = Path(__file__).resolve().parent / "docs"
PAOK = "ΠΑΟΚ"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130 Safari/537.36")

# Τα κλειδιά είναι και ονόματα αρχείων (π.χ. football-home.ics) — μην τα αλλάξεις,
# γιατί χαλάνε οι υπάρχουσες συνδρομές.
SECTIONS = {
    "football": {"emoji": "⚽", "name": "Ποδόσφαιρο", "sport": "Ποδόσφαιρο", "women": False, "live": True,
                 "liveNote": "Έναρξη, κάθε γκολ, ημίχρονο και τελικό (Super League και Ευρώπη)"},
    "football-women": {"emoji": "⚽", "name": "Ποδόσφαιρο Γυναικών", "sport": "Ποδόσφαιρο", "women": True, "live": True,
                       "liveNote": "Έναρξη, κάθε γκολ, ημίχρονο και τελικό (ευρωπαϊκοί αγώνες)"},
    "basketball": {"emoji": "🏀", "name": "Μπάσκετ", "sport": "Μπάσκετ", "women": False, "live": True,
                   "liveNote": "Έναρξη, τέλος κάθε περιόδου και τελικό (Basket League και EuroCup)"},
    "basketball-women": {"emoji": "🏀", "name": "Μπάσκετ Γυναικών", "sport": "Μπάσκετ", "women": True, "live": True,
                         "liveNote": "Έναρξη και τέλος κάθε περιόδου (το τελικό με το επίσημο αποτέλεσμα)"},
    "volley": {"emoji": "🏐", "name": "Βόλεϊ", "sport": "Βόλεϊ", "women": False, "live": True,
               "liveNote": "Έναρξη, τέλος κάθε σετ και τελικό (πρωτάθλημα και κύπελλα Ελλάδας)"},
    "volley-women": {"emoji": "🏐", "name": "Βόλεϊ Γυναικών", "sport": "Βόλεϊ", "women": True, "live": True,
                     "liveNote": "Έναρξη, τέλος κάθε σετ και τελικό (πρωτάθλημα και κύπελλο Ελλάδας)"},
    "handball": {"emoji": "🤾", "name": "Χάντμπολ", "sport": "Χάντμπολ", "women": False, "live": True,
                 "liveNote": "Έναρξη, ημίχρονο και τελικό (ευρωπαϊκοί αγώνες)"},
    "handball-women": {"emoji": "🤾", "name": "Χάντμπολ Γυναικών", "sport": "Χάντμπολ", "women": True, "live": True,
                       "liveNote": "Έναρξη, ημίχρονο και τελικό (ευρωπαϊκοί αγώνες)"},
    "waterpolo": {"emoji": "🤽", "name": "Πόλο", "sport": "Πόλο", "women": False, "live": True,
                  "liveNote": "Έναρξη, τέλος κάθε περιόδου και τελικό"},
    "waterpolo-women": {"emoji": "🤽", "name": "Πόλο Γυναικών", "sport": "Πόλο", "women": True, "live": True,
                        "liveNote": "Έναρξη, τέλος κάθε περιόδου και τελικό"},
    "futsal": {"emoji": "🥅", "name": "Ποδόσφαιρο Σάλας", "sport": "Ποδόσφαιρο Σάλας", "women": False},
}

# Β' ομάδα και ακαδημίες ποδοσφαίρου (paokfc.gr). Στη σελίδα φαίνονται μόνο σε λειτουργία διαχειριστή
# (σελίδα «Ακαδημίες»)· δεν μπαίνουν στην αρχική, στα συνδυαστικά ημερολόγια (api/cal.js) ή στα social.
ACADEMY = {
    "football-b": {"emoji": "⚽", "name": "ΠΑΟΚ Β", "sport": "Ποδόσφαιρο", "women": False, "academy": True,
                   "short": "Β' ομάδα"},
    "football-u19": {"emoji": "⚽", "name": "Κ19", "sport": "Ποδόσφαιρο", "women": False, "academy": True,
                     "short": "Κ19"},
    "football-u17": {"emoji": "⚽", "name": "Κ17", "sport": "Ποδόσφαιρο", "women": False, "academy": True,
                     "short": "Κ17"},
    # Η Κ16 αγωνίζεται στη Super League 2 Κ19 (στο sl2.gr ως «Π.Α.Ο.Κ. Β' Κ19»).
    "football-u16": {"emoji": "⚽", "name": "Κ16", "sport": "Ποδόσφαιρο", "women": False, "academy": True,
                     "short": "Κ16", "league": "Super League 2 Κ19"},
    "football-u15": {"emoji": "⚽", "name": "Κ15", "sport": "Ποδόσφαιρο", "women": False, "academy": True,
                     "short": "Κ15"},
    # Βόλεϊ: πρωταθλήματα της ΕΠΕΣΘ (epesth.gr). «group»: η ομάδα του μενού (αγόρια / κορίτσια).
    # Ποδόσφαιρο, μικρότερες ηλικίες της ΠΑΕ στα πρωταθλήματα υποδομών της ΕΠΣ Μακεδονίας (βλ. EPSM_TEAMS).
    "football-u14": {"emoji": "⚽", "name": "Κ14", "sport": "Ποδόσφαιρο", "women": False, "academy": True,
                     "short": "Κ14", "league": "Κ15 League 1 (ΕΠΣΜ)"},
    "football-u13": {"emoji": "⚽", "name": "Κ13", "sport": "Ποδόσφαιρο", "women": False, "academy": True,
                     "short": "Κ13", "league": "Κ14 League 1 (ΕΠΣΜ)"},
    "football-u13b": {"emoji": "⚽", "name": "Κ13 (2)", "sport": "Ποδόσφαιρο", "women": False, "academy": True,
                      "short": "Κ13 (2)", "league": "Κ14 League 2 (ΕΠΣΜ)"},
    "football-u12": {"emoji": "⚽", "name": "Κ12", "sport": "Ποδόσφαιρο", "women": False, "academy": True,
                     "short": "Κ12", "league": "Κ13 Ειδικής (ΕΠΣΜ)"},
    # Ποδόσφαιρο κοριτσιών: Κ17 στο πανελλήνιο της ΕΠΟ, Κ15 και Κ12 (ΑΣ ΠΑΟΚ) στην ΕΠΣ Μακεδονίας.
    "football-women-u17": {"emoji": "⚽", "name": "Κ17 Νεανίδων", "sport": "Ποδόσφαιρο", "women": True, "academy": True,
                           "short": "Κ17", "group": "Ποδόσφαιρο Κοριτσιών", "league": "Πανελλήνιο Υποδομών Νεανίδων Κ17"},
    "football-women-u15": {"emoji": "⚽", "name": "Κ15 Κοριτσιών", "sport": "Ποδόσφαιρο", "women": True, "academy": True,
                           "short": "Κ15", "group": "Ποδόσφαιρο Κοριτσιών", "league": "Κ15 Γυναικών (ΕΠΣΜ)"},
    "football-women-u15b": {"emoji": "⚽", "name": "Κ15 Κοριτσιών (2)", "sport": "Ποδόσφαιρο", "women": True, "academy": True,
                            "short": "Κ15 (2)", "group": "Ποδόσφαιρο Κοριτσιών", "league": "Κ15 Γυναικών (ΕΠΣΜ)"},
    "football-women-u12": {"emoji": "⚽", "name": "Κ12 Κορασίδων", "sport": "Ποδόσφαιρο", "women": True, "academy": True,
                           "short": "Κ12", "group": "Ποδόσφαιρο Κοριτσιών", "league": "Κ12 Κορασίδων (ΕΠΣΜ)"},
    "volley-u21": {"emoji": "🏐", "name": "Κ21 Αγοριών", "sport": "Βόλεϊ", "women": False, "academy": True,
                   "short": "Κ21", "group": "Βόλεϊ Αγοριών", "league": "Κ21 Αγοριών (ΕΠΕΣΘ)"},
    "volley-u18": {"emoji": "🏐", "name": "Κ18 Αγοριών", "sport": "Βόλεϊ", "women": False, "academy": True,
                   "short": "Κ18", "group": "Βόλεϊ Αγοριών", "league": "Κ18 Αγοριών (ΕΠΕΣΘ)"},
    "volley-women-u20": {"emoji": "🏐", "name": "Κ20 Κοριτσιών", "sport": "Βόλεϊ", "women": True, "academy": True,
                         "short": "Κ20", "group": "Βόλεϊ Κοριτσιών", "league": "Κ20 Κοριτσιών (ΕΠΕΣΘ)"},
    "volley-women-u18": {"emoji": "🏐", "name": "Κ18 Κοριτσιών", "sport": "Βόλεϊ", "women": True, "academy": True,
                         "short": "Κ18", "group": "Βόλεϊ Κοριτσιών", "league": "Κ18 Κοριτσιών (ΕΠΕΣΘ)"},
    "volley-women-u18es1": {"emoji": "🏐", "name": "Κ18 Κοριτσιών ΕΣ 1", "sport": "Βόλεϊ", "women": True, "academy": True,
                            "short": "Κ18 ΕΣ 1", "group": "Βόλεϊ Κοριτσιών", "league": "Κ18 Κοριτσιών Ε.Σ. (ΕΠΕΣΘ)"},
    "volley-women-u18es2": {"emoji": "🏐", "name": "Κ18 Κοριτσιών ΕΣ 2", "sport": "Βόλεϊ", "women": True, "academy": True,
                            "short": "Κ18 ΕΣ 2", "group": "Βόλεϊ Κοριτσιών", "league": "Κ18 Κοριτσιών Ε.Σ. (ΕΠΕΣΘ)"},
    # Μπάσκετ: ΑΣ ΠΑΟΚ στα πρωταθλήματα της ΕΚΑΣΘ (βλ. EKASTH_TEAMS).
    "basketball-u18": {"emoji": "🏀", "name": "Έφηβοι", "sport": "Μπάσκετ", "women": False, "academy": True,
                       "short": "Έφηβοι", "group": "Μπάσκετ Αγοριών", "league": "Εφήβων (ΕΚΑΣΘ)"},
    "basketball-u16": {"emoji": "🏀", "name": "Παίδες", "sport": "Μπάσκετ", "women": False, "academy": True,
                       "short": "Παίδες", "group": "Μπάσκετ Αγοριών", "league": "Παίδων (ΕΚΑΣΘ)"},
    "basketball-u16b": {"emoji": "🏀", "name": "Παίδες 2", "sport": "Μπάσκετ", "women": False, "academy": True,
                        "short": "Παίδες 2", "group": "Μπάσκετ Αγοριών", "league": "Παίδων (ΕΚΑΣΘ)"},
    "basketball-women-u18": {"emoji": "🏀", "name": "Νεάνιδες", "sport": "Μπάσκετ", "women": True, "academy": True,
                             "short": "Νεάνιδες", "group": "Μπάσκετ Κοριτσιών", "league": "Νεανίδων (ΕΚΑΣΘ)"},
    "basketball-women-u16": {"emoji": "🏀", "name": "Κορασίδες", "sport": "Μπάσκετ", "women": True, "academy": True,
                             "short": "Κορασίδες", "group": "Μπάσκετ Κοριτσιών", "league": "Κορασίδων (ΕΚΑΣΘ)"},
    "basketball-women-u16b": {"emoji": "🏀", "name": "Κορασίδες 2", "sport": "Μπάσκετ", "women": True, "academy": True,
                              "short": "Κορασίδες 2", "group": "Μπάσκετ Κοριτσιών", "league": "Κορασίδων (ΕΚΑΣΘ)"},
}
SECTIONS.update(ACADEMY)

# ΑμεΑ σε ομαδικά αθλήματα (ΑΣ ΠΑΟΚ ΑμεΑ). Δεν έχουν πηγή που διαβάζεται (ανακοινώνονται στο Instagram
# @acpaok_amea): οι αγώνες μπαίνουν από τη φόρμα «Νέος αγώνας» και το manual.json. Στη σελίδα μόνο για τον
# διαχειριστή (#/atomika, μαζί με τα ατομικά)· δεν μπαίνουν στην αρχική, στα social ή στα συνδυαστικά ημερολόγια.
# Νέα ομάδα = μία γραμμή εδώ· εμφανίζεται μόνη της στη σελίδα και στη φόρμα.
AMEA = {
    "basketball-amea": {"emoji": "🏀", "name": "Μπάσκετ ΑμεΑ", "sport": "Μπάσκετ", "women": False, "amea": True,
                        "short": "Μπάσκετ"},
}
SECTIONS.update(AMEA)


@dataclass
class Match:
    section: str
    uid: str
    day: dt.date
    time: dt.time | None  # None: η ώρα δεν έχει οριστεί
    home: str
    away: str
    paok_home: bool
    venue: str = ""
    competition: str = ""
    round: str = ""
    score: str = ""  # π.χ. "3-1", μόνο για αγώνες που έχουν γίνει
    tv: str = ""
    tv_url: str = ""  # σύνδεσμος της μετάδοσης (π.χ. YouTube), αν υπάρχει
    url: str = ""
    home_logo: str = ""
    away_logo: str = ""
    # Πού βρίσκεται το ζωντανό σκορ, αν υπάρχει (βλ. live.py και τη σελίδα).
    live: dict | None = None
    # Από πού έρχονται τα στατιστικά (box score) μετά τον αγώνα, όταν το live έχει σβήσει (σκορ από την
    # επίσημη σελίδα ή τον διαχειριστή): ίδια μορφή με το live, μόνο για τη σελίδα αγώνα (βλ. keep_stats).
    stats: dict | None = None
    status: str = ""  # "postponed" | "cancelled" | "abandoned": δεν θα γίνει / δεν ολοκληρώθηκε
    note: str = ""    # π.χ. «πέναλτι 4–3», «μετά από παράταση», ή ο λόγος της αναβολής
    # Σκορ ανά σετ/περίοδο ([γηπεδούχος, φιλοξενούμενος]), από το τελικό του live: μένει μετά τον αγώνα.
    periods: list | None = None

    def start(self) -> dt.datetime:
        return dt.datetime.combine(self.day, self.time or DEFAULT_TIME, ATHENS)

    def to_json(self) -> dict:
        d = asdict(self)
        d["start"] = self.start().isoformat()
        d["timeKnown"] = self.time is not None
        d["paokHome"] = d.pop("paok_home")
        d["homeLogo"] = d.pop("home_logo")
        d["awayLogo"] = d.pop("away_logo")
        d["tvUrl"] = d.pop("tv_url")
        d["nt"] = match_topic_id(self.uid)
        for k in ("live", "stats", "status", "note", "periods"):
            if not d[k]:
                del d[k]
        del d["day"], d["time"]
        return d


GOALS_PATH = Path(__file__).resolve().parent / "goals.json"
GOAL_TAGS = {"πεν": "pen", "αυτ": "og"}


POINTS_SPORTS = ("basketball", "volley")  # σκόρερ με πόντους (όπως στο api/admin.js)


def is_points_section(section: str) -> bool:
    return section.split("-")[0] in POINTS_SPORTS


def goals_fit(goals: dict, score: str) -> bool:
    """Τα γκολ κάθε ομάδας ταιριάζουν με το σκορ (με «n» = πολλά γκολ σε μία γραμμή); μόνο σε αθλήματα με γκολ."""
    parts = re.fullmatch(r"(\d+)-(\d+)", score or "")
    count = lambda side: sum(int(g.get("n") or 1) for g in goals.get(side) or [])  # noqa: E731
    return bool(parts) and [count("home"), count("away")] == [int(parts[1]), int(parts[2])]


def admin_goals() -> dict[str, dict]:
    """Οι σκόρερ της φόρμας του διαχειριστή (api/admin.js, συλλογή «goals»), με το nt του αγώνα."""
    try:
        got = json.loads(fetch(ADMIN_URL))
    except Exception as e:
        print(f"  ! σκόρερ διαχειριστή: {e}", file=sys.stderr)
        return {}
    return {g["nt"]: g for g in got.get("goals", []) if isinstance(g, dict) and g.get("nt")}


def apply_goals(matches: list[dict], path: Path = GOALS_PATH, admin: dict[str, dict] | None = None) -> None:
    """Σκόρερ στο πεδίο «goals» του αγώνα: {"home": [{"min": "45+1", "name": "…", "n": 2, "pen"/"og": true}], "away": […]}.

    Από τη φόρμα του διαχειριστή (admin, με το nt· μετρά πρώτη) και από το goals.json (με το uid). Στα αθλήματα με
    γκολ μπαίνουν μόνο όταν τα γκολ κάθε ομάδας ταιριάζουν με το σκορ, ώστε ένα λάθος (ή αλλαγή του σκορ) να μη
    δείξει λάθος σκόρερ· στο μπάσκετ και στο βόλεϊ (πόντοι) μπαίνουν πάντα, με «points»: true."""
    table = {}
    if path.exists():
        try:
            table = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            print(f"! goals.json: {e}", file=sys.stderr)
    for m in matches:
        a = (admin or {}).get(m.get("nt") or match_topic_id(m["uid"]))
        e = table.get(m["uid"])
        if a:
            goals = {side: [{k: g[k] for k in ("min", "name", "n", "pen", "og") if g.get(k)} for g in a.get(side) or []
                            if isinstance(g, dict) and g.get("name")] for side in ("home", "away")}
            label = f"{m['home']} – {m['away']}"
        elif isinstance(e, dict):
            goals = {}
            for side in ("home", "away"):
                goals[side] = []
                for g in e.get(side) or []:
                    d = {"min": str(g[0]).strip(), "name": str(g[1]).strip()}
                    for t in g[2:]:
                        if t in GOAL_TAGS:
                            d[GOAL_TAGS[t]] = True
                    goals[side].append(d)
            label = e.get("m") or m["uid"]
        else:
            continue
        if is_points_section(m.get("section", "")):
            m["goals"] = {**goals, "points": True}
            continue
        if not goals_fit(goals, m.get("score") or ""):
            print(f"! σκόρερ: {label}: τα γκολ δεν ταιριάζουν με το σκορ «{m.get('score')}»", file=sys.stderr)
            continue
        m["goals"] = goals


def match_topic_id(uid: str) -> str:
    """Σύντομο, σταθερό αναγνωριστικό αγώνα (για τη σελίδα του και τις ειδοποιήσεις του)."""
    return hashlib.sha1(uid.encode()).hexdigest()[:10]


# ---------------------------------------------------------------- βοηθητικά

_FETCHED: dict[tuple, str] = {}


def fetch(url: str, data: list[tuple[str, str]] | None = None, encoding: str = "utf-8") -> str:
    """Κατεβάζει μια σελίδα· την ίδια σελίδα την κατεβάζει μία φορά ανά εκτέλεση."""
    key = (url, tuple(data) if data is not None else None, encoding)
    if key not in _FETCHED:
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, headers={"User-Agent": UA, "Accept-Language": "el,en"})
        with urllib.request.urlopen(req, timeout=60) as r:
            _FETCHED[key] = r.read().decode(encoding, errors="replace")
    return _FETCHED[key]


def fetch_until(url: str, ok: Callable[[str], bool], tries: int = 3) -> str:
    """Όπως το fetch, αλλά ξαναδοκιμάζει αν η σελίδα ήρθε ελλιπής (συμβαίνει στο basket.gr)."""
    import time
    page = fetch(url)
    for _ in range(tries - 1):
        if ok(page):
            break
        time.sleep(8)
        _FETCHED.pop((url, None, "utf-8"), None)
        page = fetch(url)
    return page


# Αρχείο παλιών σεζόν (archive.py backfill): η σεζόν που ζητείται από όσες πηγές έχουν επιλογή σεζόν
# (ESPN, esake.gr). None = κανονική λειτουργία.
ARCHIVE_YEAR: int | None = None


def season_start_year(today: dt.date | None = None) -> int:
    today = today or dt.date.today()
    return today.year if today.month >= 7 else today.year - 1


def clean(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def plain(text: str) -> str:
    """Κεφαλαία χωρίς τόνους/διαλυτικά, για συγκρίσεις."""
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).upper()


# Μερικά site γράφουν ελληνικά ονόματα με λατινικά γράμματα που μοιάζουν (π.χ. «ΠAΟΚ»).
_LOOKALIKE = str.maketrans("ABEZHIKMNOPTYX", "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ")


def greekish(text: str) -> str:
    return text.upper().translate(_LOOKALIKE)


def is_paok(name: str) -> bool:
    n = re.sub(r"[.\s]", "", plain(name))
    n = re.sub(r"^AC(?=PAOK)", "", n)  # «A.C. PAOK» (ΑΣ ΠΑΟΚ) στις ευρωπαϊκές ομοσπονδίες
    return n.startswith("PAOK") or greekish(n).startswith("ΠΑΟΚ")


def tidy_name(name: str) -> str:
    """Αφαιρεί νομικά προθέματα (ΠΑΕ, ΚΑΕ…) και ενοποιεί το όνομα του ΠΑΟΚ."""
    name = re.sub(r"^(?:Π\.?\s?Α\.?\s?Ε\.?|Κ\.?\s?Α\.?\s?Ε\.?)\s+", "", name.strip())
    return PAOK if is_paok(name) else name


def absolute(base: str, src: str) -> str:
    return urllib.parse.urljoin(base, html.unescape(src)) if src else ""


def short_hash(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


_MONTH_PREFIXES = [("ΙΑΝ", 1), ("ΦΕΒ", 2), ("ΜΑΡ", 3), ("ΑΠΡ", 4), ("ΜΑΙ", 5), ("ΙΟΥΝ", 6),
                   ("ΙΟΥΛ", 7), ("ΑΥΓ", 8), ("ΣΕΠ", 9), ("ΟΚΤ", 10), ("ΝΟΕ", 11), ("ΔΕΚ", 12)]


def greek_month(word: str) -> int | None:
    """Μήνας από ελληνική λέξη σε οποιαδήποτε μορφή: «Οκτώβριος», «Οκτωβρίου», «Οκτ»."""
    w = plain(word)
    for prefix, month in _MONTH_PREFIXES:
        if w.startswith(prefix):
            return month
    return None


def parse_time(text: str) -> dt.time | None:
    m = re.search(r"(\d{1,2}):(\d{2})", text)
    if not m:
        return None
    t = dt.time(int(m.group(1)), int(m.group(2)))
    return None if t == dt.time(0, 0) else t  # 00:00 σημαίνει «δεν έχει οριστεί»


def parse_score(text: str) -> str:
    m = re.search(r"(\d+)\s*-\s*(\d+)", text or "")
    return f"{m.group(1)}-{m.group(2)}" if m else ""


# ---------------------------------------------------------------- βόλεϊ

def volley_rows() -> tuple[str, list[dict]]:
    """Όλοι οι αγώνες της σελίδας της Volley League (όχι μόνο του ΠΑΟΚ)."""
    y = season_start_year()
    season = f"{y}-{str(y + 1)[-2:]}"
    url = f"https://www.volleyleague.gr/index.php/season/{season}/regular-season-results-statistics"
    page = fetch(url)

    # Κάθε αγωνιστική ξεκινά με <h3>…</h3>· κάθε αγώνας είναι μια γραμμή με
    # ημερομηνία, ώρα, γήπεδο, γηπεδούχο, σήμα, σκορ, σήμα, φιλοξενούμενο.
    row = re.compile(
        r'>(\d{2}/\d{2}/\d{4})</div>\s*'
        r'<div[^>]*>([^<]*)</div>\s*'
        r'<div[^>]*>([^<]*)</div>\s*'
        r'<div[^>]*>\s*<a[^>]*>([^<]*)</a>\s*</div>\s*'
        r'<div[^>]*>\s*<img src="([^"]*)".*?'
        r'<span class="team-class">([^<]*)</span>.*?'
        r'<img src="([^"]*)".*?'
        r'<a[^>]*>([^<]*)</a>',
        re.S,
    )
    heads = [(m.start(), clean(m.group(1)))
             for m in re.finditer(r"<h3>(.*?)</h3>", page, re.S)]

    def heading_at(pos: int) -> str:
        current = ""
        for start, title in heads:
            if start > pos:
                break
            current = title
        return current

    rows = []
    for m in row.finditer(page):
        date_s, time_s, venue, home, home_logo, score, away_logo, away = (clean(g) for g in m.groups())
        rows.append({
            "date": date_s, "time": time_s, "venue": venue, "home": home, "away": away,
            "home_logo": absolute(url, home_logo), "away_logo": absolute(url, away_logo),
            # Στο βόλεϊ τελικό είναι μόνο το σκορ με 3 σετ για κάποια ομάδα· αλλιώς ο αγώνας παίζεται.
            "score": parse_score(score) if is_volley_final(parse_score(score)) else "",
            "heading": heading_at(m.start()),
        })
    return url, rows


def volley_matches() -> list[Match]:
    url, rows = volley_rows()
    season = re.search(r"season/([^/]+)/", url).group(1)
    out = []
    for r in rows:
        home, away, head = r["home"], r["away"], r["heading"]
        if not (is_paok(home) or is_paok(away)):
            continue
        if "αγωνιστική" in head.lower():
            comp, rnd = "Volley League", re.sub(r"\s*-\s*Τέλος.*", "", head)
        else:
            comp, rnd = head.title() if head.isupper() else head, ""
        out.append(Match(
            section="volley",
            uid=f"volley-{season}-{short_hash(comp, rnd, home, away)}",
            day=dt.datetime.strptime(r["date"], "%d/%m/%Y").date(), time=parse_time(r["time"]),
            home=tidy_name(home), away=tidy_name(away),
            paok_home=is_paok(home), venue=r["venue"], competition=comp, round=rnd,
            score=r["score"], url=url, home_logo=r["home_logo"], away_logo=r["away_logo"],
        ))
    if not out:
        raise RuntimeError("Δεν βρέθηκαν αγώνες ΠΑΟΚ στο volleyleague.gr")
    return out


DATAPROJECT = "https://eope-web.dataproject.com/"


def dataproject_matches(section: str) -> list[Match]:
    """Διοργανώσεις της ΕΟΠΕ (βόλεϊ γυναικών, Κύπελλα) από το Data Project."""
    women = SECTIONS[section]["women"]
    y = season_start_year()
    season = f"{y}-{str(y + 1)[-2:]}"
    home_page = fetch(DATAPROJECT + "MainHome.aspx")
    wanted = []
    for cid, label in re.findall(r'href="CompetitionHome\.aspx\?ID=(\d+)"[^>]*>(.*?)</a>', home_page, re.S):
        name = clean(label)
        up = plain(name)
        if season not in name or ("WOMEN" in up) != women:
            continue
        if not women and not re.search(r"\bMEN\b", up):
            continue  # π.χ. «SUPER CUP» χωρίς φύλο
        if (cid, name) not in wanted:
            wanted.append((cid, name))
    if women and not wanted:
        raise RuntimeError(f"Δεν βρέθηκε διοργάνωση γυναικών {season} στο Data Project")

    out = []
    for cid, comp_name in wanted:
        first = fetch(f"{DATAPROJECT}CompetitionMatches.aspx?ID={cid}")
        pids = sorted(set(re.findall(rf"CompetitionMatches\.aspx\?ID={cid}&amp;PID=(\d+)", first)))
        pages = [first] + [fetch(f"{DATAPROJECT}CompetitionMatches.aspx?ID={cid}&PID={p}")
                           for p in pids[1:]]
        comp = re.sub(rf"\s*{season}\s*", " ", comp_name).strip()
        comp = {"VOLLEY LEAGUE WOMEN": "Volley League Γυναικών"}.get(comp.upper(), comp.title())
        if "CUP" in comp.upper():
            comp = "Κύπελλο Ελλάδας"
        for page in pages:
            out += _parse_dataproject(page, section, cid, comp)
    return out


# Η ΕΟΠΕ (Data Project) γράφει τις ομάδες των γυναικών με λατινικά («PANATHINAIKOS A.O.»). Τα ελληνικά τους
# ονόματα, όπως στο πρόγραμμα της Volley League Γυναικών· ταιριάζουν με τα λατινικά λέξη προς λέξη.
VOLLEY_WOMEN_NAMES = [
    "Παναθηναϊκός Α.Ο.", "Ολυμπιακός Σ.Φ.Π.", "Α.Ε.Κ.", "Α.Σ. Άρης", "Ζ.Α.Ο.Ν.", "Α.Σ. Ελπίς", "Α.Σ.Π. Θέτις",
    "Πανιώνιος", "Ο.Φ.Α. Απολλώνιος", "Α.Ο. Μαρκοπούλου", "Α.Ο. Θήρας",
]


def latin_words(name: str) -> list[str]:
    text = re.sub(r"(?<=[A-Z])\.", "", plain(name))  # «A.E.K.» → «AEK»
    return [w for w in re.findall(r"[A-Z]{3,}", text) if w not in _SLUG_SKIP]


def volley_women_name(name: str) -> str:
    """Το ελληνικό όνομα μιας ομάδας της ΕΟΠΕ, αν ταιριάζει ακριβώς με μία· αλλιώς το όνομα όπως είναι."""
    if is_paok(name) or re.search(r"[Α-Ωα-ω]", name):
        return tidy_name(name)
    mine = latin_words(name)
    same = lambda a, b: a[:5] == b[:5] if min(len(a), len(b)) >= 5 else a == b
    found = {g for g in VOLLEY_WOMEN_NAMES if any(same(a, b) for a in mine for b in greeklish_words(g))}
    return found.pop() if len(found) == 1 else cev_caps(name)


def _parse_dataproject(page: str, section: str, cid: str, comp: str, only_paok: bool = True) -> list[Match]:
    team = volley_women_name if section == "volley-women" else tidy_name
    key_re = re.compile(r'_RADLIST_Legs_(ctrl\d+)_(?:RADLIST_Matches_(ctrl\d+)_)?([A-Za-z0-9_]+)"')
    fields: dict[tuple, dict] = collections.defaultdict(dict)
    first_pos: dict[tuple, int] = {}
    leg_names: dict[str, str] = {}
    for m in re.finditer(r'id="ctl00_Content_Main_\d+_userControl(_RADLIST_Legs_[^"]+")([^>]*)>([^<]*)',
                         page):
        km = key_re.match(m.group(1))
        if not km:
            continue
        leg, match_ctrl, field = km.groups()
        if match_ctrl is None:
            if field == "LYR_LegName":
                tail = page[m.end():m.end() + 600]
                h3 = re.search(r"<h3[^>]*>(.*?)</h3>", tail, re.S) or re.search(r"<h3[^>]*>([^<]*)", tail)
                if h3:
                    leg_names[leg] = clean(h3.group(1))
            continue
        key = (leg, match_ctrl)
        first_pos.setdefault(key, m.start())
        value = re.search(r'value="([^"]*)"', m.group(2))
        if field.startswith("Logo_"):
            logo = re.search(r'url\((?:&quot;|["\'])?([^"&)]+)', m.group(2))
            if logo:
                fields[key][field] = logo.group(1)
            continue
        fields[key][field] = (value.group(1) if value else m.group(3)).strip()

    ids = [(m.start(), m.group(1)) for m in re.finditer(r"MatchStatistics\.aspx\?mID=(\d+)", page)]
    out = []
    for key, f in fields.items():
        home = f.get("Label2") or f.get("Label6") or ""
        away = f.get("Label4") or f.get("Label7") or ""
        if only_paok and not (is_paok(home) or is_paok(away)):
            continue
        when = f.get("LB_DataOra") or f.get("LBL_DataOra_Small") or ""
        dm = re.search(r"(\d{2})/(\d{2})/(\d{4})", when)
        if not dm:
            continue
        mid = next((i for pos, i in ids if pos > first_pos[key]), None)
        sets = (f.get("LB_SetCasa", ""), f.get("LB_SetOspiti", ""))
        score = f"{sets[0]}-{sets[1]}" if all(s.isdigit() for s in sets) and "3" in sets else ""
        leg = leg_names.get(key[0], "")
        rnd_m = re.search(r"MATCH DAY\s*(\d+)", leg, re.I)
        out.append(Match(
            section=section,
            uid=f"{section}-dp{cid}-{mid or short_hash(home, away, leg)}",
            day=dt.date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1))),
            time=parse_time(when.split("-", 1)[-1] if "-" in when else when),
            home=team(home), away=team(away), paok_home=is_paok(home),
            venue=f.get("LB_Palasport", ""), competition=comp,
            round=f"{rnd_m.group(1)}η Αγωνιστική" if rnd_m else leg.title(),
            score=score,
            url=(f"{DATAPROJECT}MatchStatistics.aspx?mID={mid}&ID={cid}" if mid
                 else f"{DATAPROJECT}CompetitionMatches.aspx?ID={cid}"),
            home_logo=f.get("Logo_Home", f.get("Logo_Home_sm", "")),
            away_logo=f.get("Logo_Guest", f.get("Logo_Guest_sm", "")),
        ))
    return out


# ---------------------------------------------------------------- ποδόσφαιρο

ESPN_TEAM_ID = "605"  # PAOK
ESPN_LEAGUES = [
    "gre.1",
    "uefa.champions", "uefa.europa", "uefa.europa.conf",
    "uefa.champions_qual", "uefa.europa_qual", "uefa.europa.conf_qual",
    "all",  # αποτελέσματα από όλες τις διοργανώσεις της σεζόν
]
COMPETITION_NAMES = {
    "gre.1": "Super League",
    "uefa.champions": "Champions League",
    "uefa.europa": "Europa League",
    "uefa.europa.conf": "Conference League",
    "uefa.champions_qual": "Champions League (προκριματικά)",
    "uefa.europa_qual": "Europa League (προκριματικά)",
    "uefa.europa.conf_qual": "Conference League (προκριματικά)",
    "uefa.wchampions": "Women's Champions League",
    "uefa.w.europa": "Women's Europa Cup",
}
ESPN_WOMEN_TEAM_ID = "131834"  # PAOK γυναικών
ESPN_WOMEN_LEAGUES = ["uefa.wchampions", "uefa.w.europa"]
FOOTBALL_NAMES = {
    "PAOK": PAOK, "Olympiacos": "Ολυμπιακός", "AEK Athens": "ΑΕΚ",
    "Panathinaikos": "Παναθηναϊκός", "Aris": "Άρης", "Asteras Tripoli": "Αστέρας Τρίπολης",
    "Atromitos": "Ατρόμητος", "OFI Crete": "ΟΦΗ", "Panetolikos": "Παναιτωλικός",
    "Levadiakos": "Λεβαδειακός", "Volos NFC": "Βόλος", "Kifisia": "Κηφισιά",
    "Iraklis": "Ηρακλής", "Kalamata": "Καλαμάτα", "Panserraikos": "Πανσερραϊκός",
    "Lamia": "Λαμία", "Athens Kallithea": "Καλλιθέα", "AEL": "ΑΕΛ", "Larissa": "ΑΕΛ",
    "Asteras Aktor": "Αστέρας Τρίπολης",
}
VENUE_NAMES = {"Toumba Stadium": "Τούμπα"}


def football_matches() -> list[Match]:
    out = espn_matches("football", ESPN_TEAM_ID, ESPN_LEAGUES)
    if not any(m.live and m.live["league"] == "gre.1" for m in out):
        raise RuntimeError("Δεν βρέθηκαν αγώνες Super League στο ESPN")
    return out


def football_women_europe() -> list[Match]:
    """Ευρωπαϊκές διοργανώσεις UEFA γυναικών (Women's Champions League, Women's Europa Cup)."""
    return espn_matches("football-women", ESPN_WOMEN_TEAM_ID, ESPN_WOMEN_LEAGUES)


def espn_round(text: str) -> str:
    """«2nd Leg - Spartak Myjava win 4-3 on aggregate» → «2ος αγώνας, πρόκριση Spartak Myjava (4-3 συνολικά)»."""
    text = re.sub(r"\b1st Leg\b", "1ος αγώνας", text)
    text = re.sub(r"\b2nd Leg\b", "2ος αγώνας", text)
    return re.sub(r"\s*-\s*(.+?) (?:win|advance) (\d+-\d+) on aggregate", r", πρόκριση \1 (\2 συνολικά)", text)


def espn_matches(section: str, team_id: str, leagues: list[str]) -> list[Match]:
    base = "https://site.api.espn.com/apis/site/v2/sports/soccer"
    events: dict[str, tuple[str, dict]] = {}
    for league in leagues:
        for suffix in ((f"?season={ARCHIVE_YEAR}",) if ARCHIVE_YEAR else ("?fixture=true", "")):
            try:
                data = json.loads(fetch(f"{base}/{league}/teams/{team_id}/schedule{suffix}"))
            except Exception as e:  # ένα λάθος σε μία διοργάνωση δεν ακυρώνει τις άλλες
                print(f"  ! ESPN {league}{suffix}: {e}", file=sys.stderr)
                continue
            for ev in data.get("events", []):
                slug = (ev.get("league") or {}).get("slug") or league
                events.setdefault(ev["id"], (slug, ev))

    out = []
    for ev_id, (league, ev) in events.items():
        comp = ev["competitions"][0]
        teams = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in teams or "away" not in teams:
            continue
        name = lambda c: FOOTBALL_NAMES.get(c["team"]["displayName"], c["team"]["displayName"])
        logo = lambda c: (c["team"].get("logo") or next(
            (l.get("href") for l in c["team"].get("logos", []) if "dark" not in l.get("rel", [])), ""))
        start_utc = dt.datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
        local = start_utc.astimezone(ATHENS)
        time_known = ev.get("timeValid", comp.get("timeValid", True))
        status = (comp.get("status") or {}).get("type", {})
        score = ""
        if status.get("completed"):
            def goals(c):
                s = c.get("score")
                return str(s.get("displayValue", s.get("value", ""))) if isinstance(s, dict) else str(s or "")
            score = f'{goals(teams["home"])}-{goals(teams["away"])}'
        pens = [teams[s].get("shootoutScore") for s in ("home", "away")]
        note = f"πέναλτι {pens[0]}–{pens[1]}" if score and None not in pens else ""
        state_name = status.get("name") or ""
        off = next((v for k, v in ESPN_OFF.items() if k in state_name), "")
        venue = (comp.get("venue") or {}).get("fullName", "")
        notes = comp.get("notes") or []
        out.append(Match(
            section=section, uid=f"{section}-espn-{ev_id}",
            day=local.date(),
            time=dt.time(local.hour, local.minute) if time_known else None,
            home=name(teams["home"]), away=name(teams["away"]),
            paok_home=teams["home"]["team"]["id"] == team_id,
            venue=VENUE_NAMES.get(venue, venue),
            competition=COMPETITION_NAMES.get(league, league),
            round=espn_round(notes[0].get("headline", "") if notes else ""), score=score,
            url=f"https://www.espn.com/soccer/match/_/gameId/{ev_id}",
            home_logo=logo(teams["home"]), away_logo=logo(teams["away"]),
            live={"src": "espn", "league": league, "id": ev_id},
            status="" if score else off, note=note,
        ))
    return out


# Καταστάσεις της ESPN για αγώνες που δεν έγιναν ή δεν ολοκληρώθηκαν.
ESPN_OFF = {"POSTPONED": "postponed", "CANCELED": "cancelled", "ABANDONED": "abandoned", "SUSPENDED": "abandoned"}
STATUS_TEXT = {"postponed": "Αναβλήθηκε", "cancelled": "Ματαιώθηκε", "abandoned": "Διακόπηκε"}

EPO = "https://www.epo.gr"


def strip_age(matches: list[Match], age: str) -> list[Match]:
    """«ΣΚΙΟΥΡΟΙ Κ17» → «ΣΚΙΟΥΡΟΙ»: στις υποδομές της ΕΠΟ όλες οι ομάδες γράφονται με την ηλικία."""
    for m in matches:
        m.home, m.away = (re.sub(rf"\s+{age}$", "", x) for x in (m.home, m.away))
    return matches


def epo_matches(comp_id: int, section: str, required: bool) -> list[Match]:
    """Πρόγραμμα από το epo.gr, για όλες τις φάσεις της τρέχουσας σεζόν.

    Αν η σεζόν δεν έχει δημοσιευτεί ακόμα (συμβαίνει στα Κύπελλα), επιστρέφει κενή λίστα.
    """
    page = fetch(f"{EPO}/el/competition/{comp_id}/matches")
    y = season_start_year()
    selects = re.findall(r'<select[^>]*id="([^"]*)"[^>]*>(.*?)</select>', page, re.S)
    options = {sid: re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)', body) for sid, body in selects}
    seasons = options.get("seasons-options", [])
    if seasons:
        url = next((v for v, label in seasons if clean(label) == f"{y}-{y + 1}"), None)
        if url is None:
            print(f"  ΕΠΟ {comp_id}: η σεζόν {y}-{y + 1} δεν έχει δημοσιευτεί ακόμα")
            return []
        page = fetch(EPO + html.unescape(url))
        selects = re.findall(r'<select[^>]*id="([^"]*)"[^>]*>(.*?)</select>', page, re.S)
        options = {sid: re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)', body) for sid, body in selects}
    stage_urls = []
    for sid, opts in options.items():
        if sid == "seasons-options":
            continue
        for value, _ in opts:
            value = html.unescape(value)
            if re.fullmatch(rf"/el/competition/{comp_id}/.*stage/\d+/group/\d+/matches", value):
                stage_urls.append(value)
    pages = [page] if not stage_urls else [fetch(EPO + u) for u in dict.fromkeys(stage_urls)]

    out, seen = [], set()
    for p in pages:
        for block in p.split("node--type-national-match node--view-mode-teaser")[1:]:
            names = [clean(n) for n in re.findall(r"field--name-name[^>]*>(.*?)</div>", block, re.S)[:2]]
            if len(names) < 2 or not (is_paok(tidy_name(names[0])) or is_paok(tidy_name(names[1]))):
                continue
            when = re.search(r"field--name-field-match-date\">(.*?)</p>", block, re.S)
            dm = re.search(r"(\d{2})/(\d{2})/(\d{4})", clean(when.group(1))) if when else None
            if not dm:
                continue
            comp = re.search(r"field--name-field-competition\">(.*?)</p>", block, re.S)
            stage = re.search(r'<p class="subtitle-2">(.*?)</p>', block, re.S)
            stadium = re.search(r"field--name-field-stadium\">(.*?)</p>", block, re.S)
            score = re.search(r"</div>\s*<h2>(.*?)</h2>", block, re.S)
            home, away = tidy_name(names[0]), tidy_name(names[1])
            logos = [absolute(EPO, x) for x in re.findall(r'field--name-field-icon.*?<img[^>]+src="([^"]+)"', block, re.S)[:2]]
            logos += [""] * (2 - len(logos))
            comp_name = clean(comp.group(1)) if comp else ""
            stage_name = clean(stage.group(1)) if stage else ""
            uid = f"{section}-epo{comp_id}-{short_hash(str(y), stage_name, home, away)}"
            if uid in seen:
                continue
            seen.add(uid)
            out.append(Match(
                section=section, uid=uid,
                day=dt.date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1))),
                time=parse_time(clean(when.group(1)).split(",", 1)[-1]),
                home=home, away=away, paok_home=is_paok(home),
                venue=clean(stadium.group(1)).strip("“”\"") if stadium else "",
                competition=re.sub(r"^Superbet\s+", "", comp_name), round=stage_name,
                score=parse_score(clean(score.group(1))) if score else "",
                url=f"{EPO}/el/competition/{comp_id}/matches",
                home_logo=logos[0], away_logo=logos[1],
            ))
    if required and not out:
        raise RuntimeError(f"Δεν βρέθηκαν αγώνες ΠΑΟΚ στη διοργάνωση {comp_id} της ΕΠΟ")
    return out


# ---------------------------------------------------------------- μπάσκετ

ESAKE_TEAM_ID = "0000000C"  # ΠΑΟΚ
# Το esake.gr γράφει τα ονόματα με κεφαλαία και χορηγούς· εδώ τα κάνουμε πιο ευανάγνωστα.
# Το κλειδί είναι η αρχή του ονόματος (κεφαλαία, χωρίς τόνους).
BASKET_NAMES = {
    "ΟΛΥΜΠΙΑΚΟΣ": "Ολυμπιακός", "ΠΑΝΑΘΗΝΑΙΚΟΣ": "Παναθηναϊκός", "ΑΕΚ": "ΑΕΚ",
    "ΑΡΗΣ": "Άρης", "ΗΡΑΚΛΗΣ": "Ηρακλής", "ΠΕΡΙΣΤΕΡΙ": "Περιστέρι",
    "ΠΡΟΜΗΘΕΑΣ": "Προμηθέας Πάτρας", "ΜΑΡΟΥΣΙ": "Μαρούσι", "ΚΑΡΔΙΤΣΑ": "Καρδίτσα",
    "ΔΟΞΑ ΛΕΥΚΑΔΑΣ": "Δόξα Λευκάδας", "ΚΟΛΟΣΣΟΣ": "Κολοσσός Ρόδου", "ΜΥΚΟΝΟΣ": "Μύκονος",
    "ΛΑΥΡΙΟ": "Λαύριο", "ΙΩΝΙΚΟΣ": "Ιωνικός", "ΑΠΟΛΛΩΝ": "Απόλλων Πάτρας",
}


def basket_name(raw: str) -> str:
    if is_paok(raw):
        return PAOK
    if "FALCONS" in raw.upper().replace("Φ", "F"):
        return "Vikos Falcons"
    key = re.sub(r"\s+", " ", greekish(plain(raw)))
    for prefix, nice in BASKET_NAMES.items():
        if key.startswith(prefix):
            return nice
    return raw


def latin_title(name: str) -> str:
    """«BOSNA» → «Bosna», αλλά αφήνει όπως είναι ονόματα με πεζά (π.χ. «Ulm»)."""
    return name.title() if name.isupper() and re.search(r"[A-Z]{4}", name) else name


def basket_league_matches() -> list[Match]:
    url = f"https://www.esake.gr/el/action/EsaketeamView?idteam={ESAKE_TEAM_ID}&mode=3"
    page = fetch(url)
    if ARCHIVE_YEAR:  # παλιά σεζόν: η επιλογή «idchampionship» της σελίδας (π.χ. «Basket League 2019-2020»)
        y = ARCHIVE_YEAR
        champ = next((v for v, label in re.findall(r'<option value="([0-9A-F]{8})"[^>]*>([^<]*)</option>', page)
                      if re.search(rf"{y}\s*-\s*(?:{y + 1}|{(y + 1) % 100:02d})\b", label)), None)
        if not champ:
            raise RuntimeError(f"Δεν βρέθηκε η σεζόν {y}-{y + 1} στο esake.gr")
        url += f"&idchampionship={champ}"
        page = fetch(url)
    out = []
    # Οι αγώνες είναι ομαδοποιημένοι ανά μήνα: «Οκτώβριος <span>2026</span>».
    for section in page.split('<div class="esake-program-series-title">')[1:]:
        hm = re.match(r"\s*([^<]+?)\s*<span>(\d{4})</span>", section)
        month = greek_month(hm.group(1)) if hm else None
        if not month:
            continue
        year = int(hm.group(2))
        for g in re.findall(r'<div class="esake-program-game">(.*?)esake-program-game-hidden-row-toggler',
                            section, re.S):
            rnd_m = re.search(r"<h5>(.*?)</h5>", g, re.S)
            info = [clean(x) for x in
                    re.findall(r'esake-program-game-info[^>]*>(.*?)</div>', g, re.S)]
            spans = [clean(x) for x in re.findall(r"<span>(.*?)</span>",
                     g.split("esake-program-game-final-score", 1)[-1], re.S)]
            gid = re.search(r"idgame=([0-9A-Fa-f]+)", g)
            logos = [absolute("https://www.esake.gr/", x) for x in re.findall(
                r'<img src="([^"]+)"', g.split("esake-program-game-final-score", 1)[-1])[:2]] + ["", ""]
            if len(spans) < 3 or not info:
                continue
            home, score, away = spans[0], spans[1], spans[2]
            if not (is_paok(home) or is_paok(away)):
                continue
            day_m = re.search(r"\b(\d{1,2})\b", info[0])
            if not day_m:
                continue
            rnd = re.sub(r"^0(\d)", r"\1", clean(rnd_m.group(1)) if rnd_m else "")
            out.append(Match(
                section="basketball",
                uid=f"basketball-esake-{gid.group(1) if gid else short_hash(info[0], home, away)}",
                day=dt.date(year, month, int(day_m.group(1))), time=parse_time(info[0]),
                home=basket_name(home), away=basket_name(away), paok_home=is_paok(home),
                venue=info[1] if len(info) > 1 else "",
                competition="Basket League", round=rnd, score=parse_score(score),
                tv=info[2] if len(info) > 2 else "",
                url=(f"https://www.esake.gr/el/action/EsakegameView?idgame={gid.group(1)}&mode=3"
                     if gid else url),
                home_logo=logos[0], away_logo=logos[1],
            ))
    if not out:
        raise RuntimeError("Δεν βρέθηκαν αγώνες ΠΑΟΚ στο esake.gr")
    return out


def eurocup_matches() -> list[Match]:
    season = f"U{season_start_year()}"
    data = json.loads(fetch(
        f"https://api-live.euroleague.net/v2/competitions/U/seasons/{season}/games"))
    games = data.get("data", data) if isinstance(data, dict) else data
    out = []
    for g in games:
        local, road = g["local"]["club"], g["road"]["club"]
        paok_home = "PAOK" in local.get("name", "").upper()
        if not paok_home and "PAOK" not in road.get("name", "").upper():
            continue
        when = dt.datetime.fromisoformat(g["utcDate"].replace("Z", "+00:00")).astimezone(ATHENS)
        score = f'{g["local"].get("score", "")}-{g["road"].get("score", "")}' if g.get("played") else ""
        phase = (g.get("phaseType") or {}).get("name", "")
        rnd = g.get("roundName") or ""
        if phase and phase != "Regular Season":
            rnd = f"{phase} – {rnd}" if rnd else phase
        nice = lambda c: PAOK if "PAOK" in c.get("name", "").upper() else latin_title(
            c.get("editorialName") or c.get("name", ""))
        out.append(Match(
            section="basketball", uid=f"basketball-eurocup-{g.get('identifier') or g['id']}",
            day=when.date(),
            time=dt.time(when.hour, when.minute) if g.get("confirmedHour", True) else None,
            home=nice(local), away=nice(road), paok_home=paok_home,
            venue=((g.get("venue") or {}).get("name") or "").title(),
            competition="EuroCup", round=rnd, score=score,
            url="https://www.eurocupbasketball.com/",
            home_logo=(local.get("images") or {}).get("crest", ""),
            away_logo=(road.get("images") or {}).get("crest", ""),
            live={"src": "euroleague", "season": season, "code": g.get("gameCode")},
        ))
    if not out:
        raise RuntimeError(f"Δεν βρέθηκαν αγώνες ΠΑΟΚ στο EuroCup {season}")
    return out


def basketgr_schedule(url: str, section: str, uid_tag: str, competition: str) -> list[Match]:
    """Οι αγώνες του ΠΑΟΚ σε μια σελίδα προγράμματος του basket.gr (ΕΟΚ): wbl1, risingstars κ.λπ.
    Κάθε αγώνας: <div class="page-schedule"> (μονά ή διπλά εισαγωγικά) με info «ημέρα, ώρα | Γήπεδο: …»,
    club, points, logo, και ίσως σύνδεσμο YouTube. Η αγωνιστική: data-round, ή η τελευταία επικεφαλίδα
    «Nη Αγωνιστική» πριν από τον αγώνα."""
    block_re = re.compile(r"""<div class=["']page-schedule["']""")
    page = fetch_until(url, lambda t: bool(block_re.search(t)) and "ΠΑΟΚ" in t)
    q = r"""["']"""
    parts = block_re.split(page)
    out = []
    heading = ""
    for prev, block in zip(parts, parts[1:]):
        hs = re.findall(r"(\d+)\s*η\s+αγωνιστικ", plain(clean(prev)).lower())
        if hs:
            heading = f"{hs[-1]}η Αγωνιστική"
        rnd = re.search(rf"data-round={q}([^\"']*)", block)
        info = re.search(rf"<div class={q}info{q}>(.*?)</div>", block, re.S)
        clubs = [clean(c) for c in re.findall(rf"<div class={q}club{q}>(.*?)</div>", block, re.S)]
        points = [clean(p) for p in re.findall(rf"<div class={q}points{q}>(.*?)</div>", block, re.S)]
        logos = re.findall(rf"<div class={q}logo{q}><img[^>]+src={q}([^\"']+)", block) + ["", ""]
        youtube = re.search(rf"href={q}(https://(?:www\.)?youtu[^\"']+)", block)
        if len(clubs) < 2 or not info or not (is_paok(clubs[0]) or is_paok(clubs[1])):
            continue
        text = clean(info.group(1))
        dm = re.search(r"(\d{1,2})\s+(\S+)\s+(\d{4})", text)
        month = greek_month(dm.group(2)) if dm else None
        if not month:
            continue
        when, _, venue = text.partition("|")
        score = f"{points[0]}-{points[1]}" if len(points) >= 2 and all(p.isdigit() for p in points[:2]) else ""
        round_name = html.unescape(rnd.group(1)) if rnd else heading
        out.append(Match(
            section=section,
            uid=f"{section}-{uid_tag}-{short_hash(round_name, clubs[0], clubs[1])}",
            day=dt.date(int(dm.group(3)), month, int(dm.group(1))),
            time=parse_time(when.split(",", 1)[-1] if "," in when else ""),
            home=tidy_name(clubs[0]), away=tidy_name(clubs[1]), paok_home=is_paok(clubs[0]),
            venue=re.sub(r"^\s*Γήπεδο:\s*", "", venue).strip(),
            competition=competition, round=round_name if rnd else ekasth_round(heading), score=score, url=url,
            home_logo=logos[0], away_logo=logos[1],
            tv="YouTube" if youtube else "", tv_url=html.unescape(youtube.group(1)) if youtube else "",
        ))
    if not out:
        # Με απόσπασμα της σελίδας γύρω από τον ΠΑΟΚ, για να φαίνεται στο log αν άλλαξε η μορφή της.
        i = page.find("ΠΑΟΚ")
        near = re.sub(r"\s+", " ", page[max(0, i - 1500):i + 300]) if i >= 0 else f"(χωρίς ΠΑΟΚ, {len(page)} χαρακτήρες)"
        raise RuntimeError(f"Δεν βρέθηκαν αγώνες ΠΑΟΚ στο {url}: {near}")
    return out


def wbl1_matches() -> list[Match]:
    return basketgr_schedule("https://www.basket.gr/wbl1/schedule/", "basketball-women", "wbl1",
                             "Women's Basketball League 1")


# Εθνική φάση των Rising Stars της ΕΟΚ (risingstars.basket.gr). Η τοπική φάση είναι στην ΕΚΑΣΘ.
RISING_STARS = {
    "basketball-u16": ("https://risingstars.basket.gr/u16/schedule/", "Gen A Rising Stars U16"),
    "basketball-u18": ("https://risingstars.basket.gr/u18/schedule/", "Rising Stars U18"),
}
_RS_FAILED: set[str] = set()


def rising_stars_matches(section: str) -> list[Match]:
    """Χωρίς να ρίχνει όλο το τμήμα αν αποτύχει: τότε μένουν οι αγώνες της προηγούμενης ενημέρωσης
    (βλ. keep_source_matches), και τα υπόλοιπα (ΕΚΑΣΘ) ενημερώνονται κανονικά."""
    url, comp = RISING_STARS[section]
    try:
        return basketgr_schedule(url, section, "rs", comp)
    except Exception as e:
        print(f"  ! {section} / Rising Stars: {e}", file=sys.stderr)
        _RS_FAILED.add(section)
        return []


def keep_source_matches(previous: list[dict], current: list[Match], tag: str) -> None:
    """Οι αγώνες μιας πηγής που απέτυχε αυτή τη φορά, από την προηγούμενη ενημέρωση."""
    have = {m.uid for m in current}
    for d in previous:
        if f"-{tag}-" in d["uid"] and d["uid"] not in have:
            current.append(match_from_json(d))


# ---------------------------------------------------------------- χάντμπολ

HANDBALL = "http://statistics.handball.org.gr/gr/"


# Σήματα: η ΟΧΕ δεν τα έχει στο statistics.handball.org.gr· τα δείχνει στη σελίδα κάθε πρωταθλήματος στο
# handball.org.gr, μαζί με σύνδεσμο στη σελίδα της ομάδας (λατινικά: «ao-diomidis-argous»), από όπου τα
# ταιριάζουμε με τα ελληνικά ονόματα του προγράμματος.
OXE_SITE = "https://www.handball.org.gr"
OXE_PAGES = {False: "/competitions/protathlimata/handball-premier", True: "/competitions/protathlimata/a1-gynaikon"}
_GREEKLISH = [("ΟΥ", "OU"), ("ΑΙ", "AI"), ("ΕΙ", "EI"), ("ΟΙ", "OI"), ("Θ", "TH"), ("Ξ", "KS"), ("Ψ", "PS"),
              ("Χ", "X"), ("Α", "A"), ("Β", "V"), ("Γ", "G"), ("Δ", "D"), ("Ε", "E"), ("Ζ", "Z"), ("Η", "I"),
              ("Ι", "I"), ("Κ", "K"), ("Λ", "L"), ("Μ", "M"), ("Ν", "N"), ("Ο", "O"), ("Π", "P"), ("Ρ", "R"),
              ("Σ", "S"), ("Τ", "T"), ("Υ", "Y"), ("Φ", "F"), ("Ω", "O")]
_SLUG_SKIP = {"HONDA", "GMC", "OLYMPIC", "DIAGNOSTIC", "AUTOVALUE", "OMILOS"}


def greeklish_words(name: str) -> list[str]:
    text = re.sub(r"(?<=[Α-ΩA-Z])\.", "", plain(name))  # «Α.Ε.Κ.» → «ΑΕΚ», «Χ.Α.Ν.Θ» → «ΧΑΝΘ»
    for g, l in _GREEKLISH:
        text = text.replace(g, l)
    return [w for w in re.findall(r"[A-Z]{3,}", text) if w not in _SLUG_SKIP]


_OXE_LOGOS: dict[bool, list[tuple[list[str], str]]] = {}


def oxe_logo(name: str, women: bool) -> str:
    """Το σήμα μιας ομάδας χάντμπολ από το handball.org.gr, αν ταιριάζει ακριβώς με μία ομάδα."""
    if women not in _OXE_LOGOS:
        _OXE_LOGOS[women] = []
        try:
            page = fetch(OXE_SITE + OXE_PAGES[women])
            for m in re.finditer(r'href="/a1-(?:wo)?men-roster/\d+-([a-z0-9-]+)"[^>]*>\s*(?:<[^>]+>\s*)*?<img[^>]+src="([^"]+)"', page):
                words = [w for w in m.group(1).upper().split("-") if len(w) >= 3 and not w.isdigit() and w not in _SLUG_SKIP]
                _OXE_LOGOS[women].append((words, OXE_SITE + m.group(2) if m.group(2).startswith("/") else m.group(2)))
            if not _OXE_LOGOS[women]:  # η εικόνα πριν από τον σύνδεσμο
                for m in re.finditer(r'<img[^>]+src="(/media/yootheme/cache/[^"]+)"[^>]*>\s*(?:<[^>]+>\s*)*?<a[^>]+href="/a1-(?:wo)?men-roster/\d+-([a-z0-9-]+)"', page):
                    words = [w for w in m.group(2).upper().split("-") if len(w) >= 3 and not w.isdigit() and w not in _SLUG_SKIP]
                    _OXE_LOGOS[women].append((words, OXE_SITE + m.group(1)))
        except Exception as e:
            print(f"  ! σήματα ΟΧΕ: {e}", file=sys.stderr)
    mine = greeklish_words(name)
    found = {logo for words, logo in _OXE_LOGOS[women]
             if any(a[:5] == b[:5] if min(len(a), len(b)) >= 5 else a == b for a in mine for b in words)}
    return found.pop() if len(found) == 1 else ""


def handball_matches(section: str) -> list[Match]:
    women = SECTIONS[section]["women"]
    season_id = str(season_start_year() + 1)  # η ΟΧΕ αριθμεί τη σεζόν 2026-27 ως 2027
    tree = fetch(HANDBALL + "sportevents.asp", encoding="cp1253")
    combos = []
    for block in tree.split("var ap = root.findchild(")[1:]:
        nodes = re.findall(r'new cri\((\d+),"([^"]*)"\)', block)
        if len(nodes) < 4 or nodes[0][0] != season_id:
            continue
        (ap, _), (cat, cat_name), (phase, phase_name), (group, group_name) = nodes[:4]
        up = plain(cat_name)
        if ("ΓΥΝΑΙΚ" in up) != women:
            continue
        # Μόνο τα πρώτα τμήματα: Premier / Α1 και τα Κύπελλα.
        if not ("PREMIER" in up or re.match(r"^[AΑ]1\b", up) or "ΚΥΠΕΛΛΟ" in up or "SUPER CUP" in up):
            continue
        combos.append((ap, cat, phase, group, cat_name, phase_name, group_name))
    if not combos:
        raise RuntimeError(f"Δεν βρέθηκαν διοργανώσεις χάντμπολ για τη σεζόν {season_id}")

    out = []
    for ap, cat, phase, group, cat_name, phase_name, group_name in combos:
        page = fetch(HANDBALL + "agperes.asp", encoding="cp1253", data=[
            ("obj", ap), ("obj", cat), ("obj", phase), ("obj", group),
            ("agper", "x"), ("category", "x"), ("fasi", "x"), ("omilos", "x"), ("B1", "x")])
        up = plain(cat_name)
        if "PREMIER" in up:
            comp = "Handball Premier"
        elif "ΚΥΠΕΛΛΟ" in up:
            comp = "Κύπελλο Ελλάδας"
        elif "SUPER CUP" in up:
            comp = "Super Cup"
        else:
            comp = "Α1 Γυναικών" if women else "Α1 Ανδρών"
        rnd = ""
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
            if "my_tab" in row and "colspan='7'" in row and row.count("<td") == 1:
                rnd = clean(row)  # επικεφαλίδα αγωνιστικής ή γύρου
                continue
            cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            if len(cells) < 6 or not re.match(r"\d{2}/\d{2}/\d{4}", cells[5]):
                continue
            home, away = cells[1], cells[3]
            if not (is_paok(home) or is_paok(away)):
                continue
            dm = re.match(r"(\d{2})/(\d{2})/(\d{4})", cells[5])
            gid = re.search(r"more\((\d+)\)", row)
            label = rnd if not phase_name or phase_name.startswith("Α'") else f"{phase_name.title()} – {rnd}"
            out.append(Match(
                section=section,
                uid=f"{section}-oxe-{gid.group(1) if gid else short_hash(cat, phase, rnd, home, away)}",
                day=dt.date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1))),
                time=parse_time(cells[5][10:]),
                home=tidy_name(home), away=tidy_name(away), paok_home=is_paok(home),
                competition=comp, round=label.strip(" –"), score=parse_score(cells[4]),
                url=HANDBALL + "sportevents.asp",
            ))
    if not out:
        raise RuntimeError("Δεν βρέθηκαν αγώνες ΠΑΟΚ στο χάντμπολ")
    for m in out:
        m.home_logo = m.home_logo or oxe_logo(m.home, women)
        m.away_logo = m.away_logo or oxe_logo(m.away, women)
    return out


# ---------------------------------------------------------------- πόλο

# Το waterpololeague.gr δείχνει το live της ΚΟΕ (σύστημα Microplus) σε κάθε σελίδα αγώνα. Από τον
# σύνδεσμο κρατάμε τους κωδικούς του αγώνα, για το ζωντανό σκορ (api/live.js, live.py).
KOE_LIVE_RE = re.compile(r"live\.koe\.org\.gr/waterpolo/#/match-details/(?:results|startlist|pbp)/"
                         r"([A-Z0-9]+)/(\d+)/([A-Z0-9]+)/(\d+)/(\d+)/(\d+)")


def volley_live(section: str, matches: list[Match]) -> None:
    """Live βόλεϊ από τη Data Project (api/live.js) για τους ελληνικούς αγώνες που δεν έχουν παιχτεί.

    Αγώνες της ΕΟΠΕ (eope-web) έχουν δικό τους κωδικό στο uid· για τους υπόλοιπους (Volley League
    ανδρών, League Cup) η function βρίσκει τον αγώνα του ΠΑΟΚ εκείνης της μέρας στο hvl-web.
    """
    today = dt.datetime.now(ATHENS).date()
    for m in matches:
        if m.score or not m.time or m.live or "-cev-" in m.uid or not -1 <= (m.day - today).days <= 10:
            continue
        side = "h" if m.paok_home else "a"
        dp_id = re.search(r"-dp\d+-(\d+)$", m.uid)
        if dp_id:
            m.live = {"src": "dp", "fed": "eope", "id": dp_id.group(1), "side": side}
        elif section == "volley":
            m.live = {"src": "dp", "fed": "hvl", "day": m.day.isoformat(), "side": side}


# Το widget της Genius Sports που έχει το esake.gr (Basket League)· από εκεί και το live.
GS_BASKET_LEAGUE = "RFJIN037I07QV520B7WEXKV1GYNA31"


def basket_league_live(matches: list[Match]) -> None:
    """Live Basket League από τη Genius Sports (api/live.js βρίσκει τον αγώνα της ημέρας)."""
    today = dt.datetime.now(ATHENS).date()
    for m in matches:
        if not m.time or m.live or "-esake-" not in m.uid or not -1 <= (m.day - today).days <= 10:
            continue
        desc = {"src": "gs", "key": GS_BASKET_LEAGUE, "day": m.day.isoformat(), "side": "h" if m.paok_home else "a"}
        if not m.score:
            m.live = desc
        elif not m.stats:
            m.stats = desc  # τελειωμένος χωρίς live: μόνο τα στατιστικά
    # Ο κωδικός του αγώνα στη Genius: το widget δείχνει μόνο τους κοντινούς αγώνες, άρα χωρίς αυτόν
    # τα στατιστικά ενός παλιότερου αγώνα δεν θα βρίσκονταν πια.
    import live
    for m in matches:
        d = m.stats
        if not d or d.get("src") != "gs" or d.get("id") or not -3 <= (m.day - today).days <= 0:
            continue
        try:
            m.stats = {**d, "id": live.gs_find_id(d)}
            print(f"  στατιστικά Genius: {m.home} – {m.away} → {m.stats['id']}")
        except Exception as e:
            print(f"  ! κωδικός Genius για {m.home} – {m.away}: {e}", file=sys.stderr)


def other_live(section: str, matches: list[Match]) -> None:
    """Live από api/live.js για: μπάσκετ γυναικών (livescore της ΕΟΚ) και ευρωπαϊκά χάντμπολ (EHF)."""
    today = dt.datetime.now(ATHENS).date()
    for m in matches:
        if m.score or not m.time or m.live or not -1 <= (m.day - today).days <= 10:
            continue
        side = "h" if m.paok_home else "a"
        ehf = re.search(r"-ehf-(\d+)$", m.uid)
        if ehf:
            m.live = {"src": "ehf", "id": ehf.group(1)}
        elif section == "basketball-women" and "-wbl1-" in m.uid:
            m.live = {"src": "eok", "day": m.day.isoformat(), "side": side, "comp": "WOMEN"}


# Η συντομότερη διάρκεια ενός αγώνα ανά τμήμα (λεπτά από την έναρξη, με τα διαλείμματα). Νωρίτερα
# δεν δεχόμαστε σκορ ως τελικό, όποια πηγή κι αν το δίνει (βλ. main).
MIN_DURATION = {
    "football": 105, "football-women": 105, "basketball": 95, "basketball-women": 90,
    "volley": 60, "volley-women": 60, "handball": 80, "handball-women": 80,
    "waterpolo": 55, "waterpolo-women": 55, "futsal": 70,
}


def is_volley_final(score: str) -> bool:
    """Στο βόλεϊ τελικό είναι μόνο σκορ με 3 σετ για κάποια ομάδα· αλλιώς ο αγώνας παίζεται."""
    return bool(re.fullmatch(r"3-[0-2]|[0-2]-3", score or ""))


def live_results(section: str, matches: list[Match], now: dt.datetime | None = None) -> None:
    """Το τελικό σκορ από την πηγή live (api/live.js κ.λπ.), όταν η επίσημη σελίδα αργεί να το βάλει.

    Π.χ. η Volley League ενημερώνει τη σελίδα αποτελεσμάτων ώρες μετά τον αγώνα, ενώ η Data Project
    έχει το τελικό αμέσως. Μόνο για αγώνες που ξεκίνησαν πριν από τη συντομότερη διάρκεια του αθλήματος
    και μέσα στις τελευταίες 12 ώρες, και μόνο αν η πηγή λέει «τέλος» (στο βόλεϊ και 3 σετ).
    """
    import live
    now = now or dt.datetime.now(ATHENS)
    shortest = dt.timedelta(minutes=MIN_DURATION.get(section, 60))
    for m in matches:
        if m.score or m.status or not m.live or not m.time:
            continue
        if not (m.start() + shortest <= now <= m.start() + dt.timedelta(hours=12)):
            continue
        get = live.SOURCES.get(m.live.get("src"))
        if not get:
            continue
        try:
            st = get(m.live)
        except Exception as e:
            print(f"  ! τελικό από live για {m.home} – {m.away}: {e}", file=sys.stderr)
            continue
        if st.get("state") != "post":
            continue
        score = f"{st['home']}-{st['away']}"
        if section in ("volley", "volley-women") and not is_volley_final(score):
            continue
        print(f"  τελικό από live: {m.home} – {m.away} {score}")
        m.stats = m.stats or m.live
        m.score, m.live = score, None


def drop_live_scores(section: str, matches: list[Match], now: dt.datetime) -> None:
    """Σκορ πριν από τη συντομότερη δυνατή διάρκεια του αθλήματος είναι το τρέχον ενός αγώνα σε
    εξέλιξη (κάποιες πηγές το δείχνουν στη θέση του τελικού), όχι αποτέλεσμα."""
    shortest = dt.timedelta(minutes=MIN_DURATION.get(section, 60))
    for m in matches:
        if m.score and m.time and m.start() > now - shortest:
            print(f"  σκορ αγώνα σε εξέλιξη, όχι τελικό: {m.home} – {m.away} {m.score}")
            m.score = ""


def koe_live(url: str) -> dict | None:
    try:
        m = KOE_LIVE_RE.search(fetch(url))
    except Exception as e:
        print(f"  ! live ΚΟΕ για {url}: {e}", file=sys.stderr)
        return None
    if not m:
        return None
    return dict(zip(("cat", "gara", "tur", "gru", "a", "b"), m.groups()), src="koe")


def waterpolo_matches(section: str) -> list[Match]:
    women = SECTIONS[section]["women"]
    yy = season_start_year() % 100
    slug = f"wpl-{'women-' if women else ''}{yy:02d}-{(yy + 1) % 100:02d}"
    url = f"https://waterpololeague.gr/championship/{slug}/fixtures"
    page = fetch(url)
    out = []
    parts = re.split(r'<a href="(https://waterpololeague\.gr/fixture/[^"]+)" class="block">', page)
    for link, body in zip(parts[1::2], parts[2::2]):
        block = body.split("</a>", 1)[0]
        names = [clean(n) for n in re.findall(r'font-heading text-xs">(.*?)</div>', block, re.S)]
        if len(names) < 2 or not (is_paok(names[0]) or is_paok(names[1])):
            continue
        logos = re.findall(r'data-twic-src="([^"]+)"', block)[:2] + ["", ""]
        info = re.search(r"<!-- Quick Info -->(.*)", block, re.S)
        info_divs = [clean(d) for d in re.findall(r"<div[^>]*>([^<]*)</div>", info.group(1))] if info else []
        date_text = next((d for d in info_divs if re.search(r"\d{4}", d)), "")
        dm = re.search(r"(\d{1,2})\s+(\S+)\s+(\d{4})", date_text)
        month = greek_month(dm.group(2)) if dm else None
        if not month:
            continue
        time_text = next((d for d in info_divs if re.fullmatch(r"\d{1,2}:\d{2}", d)), "")
        score = re.search(r'sm:block">\s*<div[^>]*>(.*?)</div>', block, re.S)
        day = dt.date(int(dm.group(3)), month, int(dm.group(1)))
        # Σε αγώνα σε εξέλιξη το ίδιο σημείο δείχνει «LIVE» και το τρέχον σκορ: δεν είναι τελικό.
        score_text = parse_score(clean(score.group(1))) if score and "LIVE" not in score.group(0) else ""
        # Live μόνο για τους κοντινούς αγώνες (μία σελίδα ανά αγώνα).
        live = koe_live(link) if not score_text and -1 <= (day - dt.datetime.now(ATHENS).date()).days <= 10 else None
        out.append(Match(
            section=section, uid=f"{section}-{link.rsplit('/', 1)[-1]}",
            day=day, time=parse_time(time_text),
            home=tidy_name(names[0]), away=tidy_name(names[1]), paok_home=is_paok(names[0]),
            competition="Water Polo League" + (" Γυναικών" if women else ""),
            score=score_text, url=link,
            home_logo=logos[0], away_logo=logos[1], live=live,
        ))
    if not out:
        raise RuntimeError(f"Δεν βρέθηκαν αγώνες ΠΑΟΚ στο {url}")
    return out


# Ευρωπαϊκά κύπελλα πόλο (European Aquatics). Το επίσημο πρόγραμμα στο europeanaquatics.org
# διαβάζει τα δεδομένα από το API της Microplus, με ένα δημόσιο token που δίνει το ίδιο API.
EA_API = "https://ea.microplustimingservices.com/api/wp"
EA_SCHEDULE_PAGE = "https://europeanaquatics.org/sports/water-polo/club-competitions/schedule/"
EA_ROUNDS = [("Qualification Round", "Προκριματικά"), ("Group Stage", "Φάση ομίλων"),
             ("Quarterfinals", "Προημιτελικά"), ("Quarter-finals", "Προημιτελικά"),
             ("Semifinals", "Ημιτελικά"), ("Semi-finals", "Ημιτελικά"), ("Final Four", "Final Four"),
             ("Final", "Τελικός"), ("Group", "Όμιλος"), ("Gruppo", "Όμιλος")]
EA_ABBREVIATIONS = {"AC", "AN", "AS", "ASC", "BVSC", "CC", "CN", "CSM", "GS", "HAVK", "OSC", "PVK", "RN",
                    "SC", "SK", "SS", "UVSE", "VK", "VSK", "WPC", "ZVL", "ZF", "FTC", "KSZ"}
_EA: dict[str, dict] = {}


def ea_data() -> dict:
    """Πρόγραμμα και διοργανώσεις της σεζόν (μία φορά ανά εκτέλεση, και για τα δύο τμήματα)."""
    if not _EA:
        code = f"EACLUB{(season_start_year() + 1) % 100:02d}"
        headers = {"User-Agent": UA, "Origin": "https://ea.microplustimingservices.com"}

        def get(url: str, token: str | None = None) -> dict:
            h = dict(headers, **({"Authorization": f"Bearer {token}"} if token else {}))
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        token = get(f"{EA_API}/site/token")["data"]["token"]
        _EA["schedule"] = get(f"{EA_API}/{code}/get/schedule/*/*/*/*/*", token)["Schedule"]
        _EA["events"] = get(f"{EA_API}/{code}/get/events/*", token)["Events"]
        _EA["get"] = lambda path: get(f"{EA_API}/{code}/get/{path}", token)  # για τις βαθμολογίες ομίλων
    return _EA


def ea_team(name: str) -> str:
    if is_paok(name.replace("AC ", "")):
        return PAOK
    # «POLAR BEARS EDE» → «Polar Bears Ede»· συντομογραφίες (CN, VK) και ονόματα με αριθμούς μένουν ως έχουν.
    return " ".join(w if w in EA_ABBREVIATIONS or re.search(r"\d", w) else w.capitalize() for w in name.split())


def ea_round(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    for en, el in EA_ROUNDS:
        text = text.replace(en, el)
    return text.replace("Προκριματικά Όμιλος", "Προκριματικά, Όμιλος").replace("ομίλων Όμιλος", "ομίλων, Όμιλος")


def european_waterpolo_matches(section: str) -> list[Match]:
    """Αγώνες του ΠΑΟΚ στα ευρωπαϊκά κύπελλα (Champions League, Euro Cup, Conference Cup…).

    Η ώρα στην πηγή είναι τοπική της πισίνας (με τη ζώνη της)· μετατρέπεται σε ώρα Ελλάδας.
    Χωρίς ευρωπαϊκή συμμετοχή επιστρέφει κενή λίστα.
    """
    cat = "ASF" if SECTIONS[section]["women"] else "ASM"
    data = ea_data()
    names = {(e["GaraCatCode"], e["GaraCode"]): e["GaraDescrEng"] for e in data["events"]}
    out = []
    for x in data["schedule"]:
        if x.get("OraCatCode") != cat:
            continue
        a, b = x.get("OraTeamNameA") or "", x.get("OraTeamNameB") or ""
        if not (x.get("OraTeamCodeA") == "PAOK" or x.get("OraTeamCodeB") == "PAOK" or is_paok(a.replace("AC ", ""))
                or is_paok(b.replace("AC ", ""))):
            continue
        day = dt.datetime.strptime(x["OraMatchDate"], "%d/%m/%Y").date()
        local = parse_time(x.get("OraTime") or "") or parse_time((x.get("OraDescr") or "").split("-")[-1])
        time = None
        if local:
            tz = re.match(r"([+-])(\d{2}):(\d{2})", x.get("TimeZone") or "+01:00")
            offset = dt.timedelta(hours=int(tz.group(2)), minutes=int(tz.group(3))) * (1 if tz.group(1) == "+" else -1)
            start = dt.datetime.combine(day, local, dt.timezone(offset)).astimezone(ATHENS)
            day, time = start.date(), start.time()
        home, away = ea_team(a), ea_team(b)
        finished = x.get("OraStatus") == 2
        out.append(Match(
            section=section,
            uid=f"{section}-ea-{x.get('OraCodPub')}-{cat}{x.get('OraGaraCode')}-{x.get('OraTurCode')}-"
                f"{x.get('OraTeamCodeA')}-{x.get('OraTeamCodeB')}",
            day=day, time=time, home=home, away=away, paok_home=home == PAOK,
            venue=x.get("OraVenue") or "",
            competition=names.get((cat, x.get("OraGaraCode")), "Ευρωπαϊκό κύπελλο"),
            round=ea_round(x.get("OraMatchDescrEng") or ""),
            score=f"{x['OraResA']}-{x['OraResB']}" if finished else "",
            url=EA_SCHEDULE_PAGE,
            live=None if finished else {"src": "ea", "code": f"EACLUB{(season_start_year() + 1) % 100:02d}", "cat": cat,
                                        "gara": str(x.get("OraGaraCode")), "tur": str(x.get("OraTurCode")),
                                        "gru": str(x.get("OraGruCode") or ""),
                                        "a": x.get("OraTeamCodeA"), "b": x.get("OraTeamCodeB")},
        ))
    return out


# ---------------------------------------------------------------- χάντμπολ: EHF

# Τα ευρωπαϊκά κύπελλα του χάντμπολ. Κάθε διοργάνωση έχει δικό της site· η λίστα αγώνων
# έρχεται από το API του (λίγοι αγώνες ανά σελίδα, προς τα πίσω και προς τα μπρος).
EHF_COMPETITIONS = [("ehfcl", "EHF Champions League"), ("ehfel", "EHF European League"),
                    ("ehfec", "EHF European Cup")]
EHF_ROUNDS = [(r"Qualification Round (\d+)", r"Προκριματικά, \1ος γύρος"), (r"^Round (\d+)$", r"\1ος γύρος"),
              (r"Last 16", "Φάση των 16"), (r"Quarter-?finals?", "Προημιτελικά"), (r"Semi-?finals?", "Ημιτελικά"),
              (r"Group Phase", "Όμιλοι"), (r"Main Round", "Κύρια φάση"), (r"Play-?offs?", "Play-off"),
              (r"Final Four|EHF FINAL4|Finals", "Final Four")]


def ehf_round(match: dict) -> str:
    comp = match.get("comp") or {}
    text = ((comp.get("round") or {}).get("name") or "").strip()
    for pattern, greek in EHF_ROUNDS:
        text = re.sub(pattern, greek, text)
    group = ((comp.get("group") or {}).get("name") or "").strip()
    return f"{text}, Όμιλος {group}" if group else text


def ehf_matches(section: str) -> list[Match]:
    """Αγώνες του ΠΑΟΚ στις διοργανώσεις της EHF όπου συμμετέχει (κοιτάζει τη λίστα συλλόγων)."""
    gender = "women" if SECTIONS[section]["women"] else "men"
    y = season_start_year()
    season = f"{y}-{(y + 1) % 100:02d}"
    out = []
    for sub, name in EHF_COMPETITIONS:
        base = f"https://{sub}.eurohandball.com"
        try:
            clubs = fetch(f"{base}/{gender}/{season}/clubs/")
            if "PAOK" not in plain(clean(clubs)):
                continue
        except urllib.error.HTTPError as e:
            # Η σελίδα συλλόγων πέφτει κάποιες φορές· τότε ψάχνουμε κατευθείαν στους αγώνες.
            print(f"  ! {base} clubs: {e}", file=sys.stderr)
        page = fetch(f"{base}/{gender}/{season}/matches/")
        comp_id = re.search(r'data-competition-id="([^"]+)"', page)
        content_id = re.search(r'data-currentcontentid="(\d+)"', page)
        if not comp_id or not content_id:
            raise RuntimeError(f"Δεν βρέθηκε η λίστα αγώνων στο {base}")
        api = f"{base}/umbraco/api/competitionmatchesapi"
        q = f"contentId={content_id.group(1)}&competitionId={comp_id.group(1)}"
        first = json.loads(fetch(f"{api}/GetInitMatches?{q}"))["matches"]
        found = {m["matchID"]: m for m in first}
        # Η λίστα είναι από τον νεότερο στον παλαιότερο: προς τα μπρος από τον πρώτο, προς τα πίσω από τον τελευταίο.
        for future in (True, False):
            batch = first
            for _ in range(100):
                if not batch:
                    break
                anchor = (batch[0] if future else batch[-1])["matchID"]
                try:
                    batch = json.loads(fetch(f"{api}/GetMatches?{q}&matchId={anchor}"
                                             f"&futureMatches={'true' if future else 'false'}"))["matches"]
                except urllib.error.HTTPError:
                    break  # τέλος της λίστας
                batch = [m for m in batch if m["matchID"] not in found]
                found.update({m["matchID"]: m for m in batch})
        for m in found.values():
            home_t, away_t = m["homeTeam"]["team"], (m.get("guestTeam") or {}).get("team") or {}
            if not (is_paok(home_t.get("fullName", "")) or is_paok(away_t.get("fullName", ""))):
                continue
            date = m["venue"]["date"]
            if not date.get("hasDate") or date["utc"].startswith("9999"):
                continue
            utc = dt.datetime.fromisoformat(date["utc"][:19] + "+00:00")
            if date.get("hasTime"):
                start = utc.astimezone(ATHENS)
                day, time = start.date(), start.time()
            else:
                day, time = utc.date(), None
            place = m["venue"].get("place") or {}
            score, note = "", ""
            if m.get("isFinished"):
                hs, gs = m["homeTeam"]["score"], m["guestTeam"]["score"]
                score = f'{hs["goals"]}-{gs["goals"]}'
                if hs.get("goalsPenaltyShotout") or gs.get("goalsPenaltyShotout"):
                    note = f'πέναλτι {hs.get("goalsPenaltyShotout") or 0}–{gs.get("goalsPenaltyShotout") or 0}'
                elif hs.get("goalsExtraTime1") or gs.get("goalsExtraTime1"):
                    note = "μετά από παράταση"
            link = m.get("url") or ""
            out.append(Match(
                section=section, uid=f"{section}-ehf-{m['matchID']}", day=day, time=time,
                home=tidy_name(home_t["fullName"]), away=tidy_name(away_t["fullName"]),
                paok_home=is_paok(home_t["fullName"]),
                venue=", ".join(x for x in (place.get("hallName"), place.get("cityName")) if x),
                competition=name, round=ehf_round(m), score=score,
                url=link if link.startswith("http") else base + link,
                home_logo=home_t.get("logoSmall") or "", away_logo=away_t.get("logoSmall") or "",
                note=note,
            ))
    return out


# ---------------------------------------------------------------- βόλεϊ: CEV

# Το παλιό site της CEV (www-old.cev.eu) έχει ακόμα το πλήρες πρόγραμμα των κυπέλλων.
# Κάθε διοργάνωση και σεζόν έχει αριθμό (ID)· βρίσκονται μία φορά ανά σεζόν και κρατιούνται
# στο docs/sources.json.
CEV = "https://www-old.cev.eu/Competition-Area/"
CEV_COMPETITIONS = [("Champions League", "Champions League"), ("Volleyball Cup", "CEV Cup"),
                    ("Challenge Cup", "Challenge Cup")]
CEV_ROUNDS = {"32nd Finals": "Φάση των 64", "16th Finals": "Φάση των 32", "8th Finals": "Φάση των 16",
              "4th Finals": "Προημιτελικά", "Play Off": "Play-off", "Semi Finals": "Ημιτελικά",
              "Finals": "Τελικοί", "Final": "Τελικός"}
CEV_LEGS = {"Home Matches": "1ος αγώνας", "Away Matches": "2ος αγώνας"}
# Χώρα (κωδικός στη σημαία της ομάδας) → ζώνη ώρας. Οι υπόλοιπες χώρες είναι σε ώρα Κεντρικής Ευρώπης.
COUNTRY_TZ = {
    "GRE": "Europe/Athens", "CYP": "Asia/Nicosia", "ROU": "Europe/Bucharest", "BUL": "Europe/Sofia",
    "TUR": "Europe/Istanbul", "UKR": "Europe/Kyiv", "MDA": "Europe/Chisinau", "FIN": "Europe/Helsinki",
    "EST": "Europe/Tallinn", "LAT": "Europe/Riga", "LTU": "Europe/Vilnius", "ISR": "Asia/Jerusalem",
    "POR": "Europe/Lisbon", "GBR": "Europe/London", "ENG": "Europe/London", "SCO": "Europe/London",
    "IRL": "Europe/Dublin", "ISL": "Atlantic/Reykjavik", "FAR": "Atlantic/Faroe", "AZE": "Asia/Baku",
    "GEO": "Asia/Tbilisi", "ARM": "Asia/Yerevan", "RUS": "Europe/Moscow", "BLR": "Europe/Minsk",
}
SOURCES_CACHE = Path(__file__).resolve().parent / "docs" / "sources.json"


def cev_title(page: str) -> str:
    text = re.sub(r"\s+", " ", clean(re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)))
    m = re.search(r"Calendar Search Login (.{5,90}?) Men Women Home", text)
    return m.group(1).strip() if m else ""


def cev_competitions() -> dict[str, str]:
    """Αριθμοί των κυπέλλων της τρέχουσας σεζόν: {"1949": "CEV Volleyball Cup 2027 | Men", …}."""
    year = str(season_start_year() + 1)  # η CEV ονομάζει τη σεζόν με το δεύτερο έτος
    cache = json.loads(SOURCES_CACHE.read_text(encoding="utf-8")) if SOURCES_CACHE.exists() else {}
    known = cache.setdefault("cev", {})
    if year in known and len(known[year]) >= 6:
        return known[year]
    start = max([int(i) for comps in known.values() for i in comps] + [1900])
    found, misses, i = dict(known.get(year, {})), 0, start
    while misses < 120 and len(found) < 6 and i < start + 600:
        i += 1
        try:
            title = cev_title(fetch(f"{CEV}CompetitionView.aspx?ID={i}"))
        except Exception:
            title = ""
        if re.search(rf"(Champions League|Volleyball Cup|Challenge Cup)\D*{year} \| (Men|Women)$", title):
            found[str(i)], misses = title, 0
        else:
            misses += 1
    known[year] = found
    SOURCES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return found


def cev_tidy(name: str) -> str:
    """«C.S. Arcada GALATI» → «C.S. Arcada Galati»."""
    return PAOK if is_paok(name) else cev_caps(name)


def cev_caps(name: str) -> str:
    return " ".join(w.capitalize() if len(w) > 3 and w.isalpha() and w.isupper() and w != "PAOK" else w
                    for w in name.split())


_CEV_TZ: dict[str, str] = {}


def cev_team_tz(team_id: str, comp_id: str) -> ZoneInfo:
    if team_id not in _CEV_TZ:
        page = fetch(f"{CEV}CompetitionTeamDetails.aspx?TeamID={team_id}&ID={comp_id}")
        flag = re.search(r"Flags_100/([A-Z]{3})_100", page)
        _CEV_TZ[team_id] = COUNTRY_TZ.get(flag.group(1) if flag else "", "Europe/Paris")
    return ZoneInfo(_CEV_TZ[team_id])


def cev_matches(section: str) -> list[Match]:
    gender = "Women" if SECTIONS[section]["women"] else "Men"
    out: dict[str, Match] = {}
    for comp_id, title in sorted(cev_competitions().items()):
        if not title.endswith(f"| {gender}"):
            continue
        competition = next((g for k, g in CEV_COMPETITIONS if k in title), title)
        first = fetch(f"{CEV}CompetitionView.aspx?ID={comp_id}")
        participants = first[first.find("Participating Teams"):]
        if "PAOK" not in plain(clean(participants)):
            continue
        # Κάθε φάση (προκριματικά, κύρια, τελική) είναι άλλη σελίδα με δικό της PID.
        pids = sorted({int(x) for x in re.findall(r"MatchPage\.aspx\?mID=\d+&(?:amp;)?ID=\d+&(?:amp;)?CID=\d+&(?:amp;)?PID=(\d+)", first)})
        pages = [first] + [fetch(f"{CEV}CompetitionView.aspx?ID={comp_id}&PID={pid}")
                           for pid in range(min(pids or [0]) - 1, max(pids or [0]) + 4) if pids]
        for page in pages:
            tabs = re.findall(r'class="rtsLink RTB_Championship[^"]*"[^>]*><span class="rtsOut"><span class="rtsIn"><span class="rtsTxt">([^<]+)<', page)
            views = re.findall(r'<div id="Content_Left_(\d+)" class="rmpView', page)
            round_of = dict(zip(views, tabs))
            legs = {(v, n): name.strip() for v, n, name in re.findall(
                r'_Content_Left_(\d+)_userControl_RADLIST_Legs_ctrl(\d+)_LB_LegName"[^>]*>([^<]+)<', page)}
            parts = re.split(r'<div id="ctl00_Content_Left_(\d+)_userControl_RADLIST_Legs_ctrl(\d+)_RADLIST_Matches_ctrl\d+_div_match"', page)
            for view, leg_no, body in zip(parts[1::3], parts[2::3], parts[3::3]):
                spans = {k: clean(v) for k, v in re.findall(r'<span id="[^"]*_(LB_[A-Za-z0-9]+|Label\d+)"[^>]*>(.*?)</span>', body, re.S)}
                home, away = spans.get("Label2", ""), spans.get("Label4", "")
                if not (is_paok(home) or is_paok(away)):
                    continue
                mid = re.search(r"MatchPage\.aspx\?mID=(\d+)", body).group(1)
                when = re.search(r"(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", spans.get("LB_DataOra", ""))
                if not when:
                    continue  # «Match not yet scheduled»
                day = dt.date(int(when.group(3)), int(when.group(2)), int(when.group(1)))
                time = None
                if when.group(4):
                    host = re.search(r"Teams_WebLogo_32_32\.aspx\?ID=(\d+)", body)
                    tz = ATHENS if is_paok(home) or not host else cev_team_tz(host.group(1), comp_id)
                    start = dt.datetime(day.year, day.month, day.day, int(when.group(4)), int(when.group(5)), tzinfo=tz).astimezone(ATHENS)
                    day, time = start.date(), start.time()
                sets = (spans.get("LB_SetCasa", "0"), spans.get("LB_SetOspiti", "0"))
                done = is_volley_final(f"{sets[0]}-{sets[1]}") and day < dt.date.today() + dt.timedelta(days=1)
                leg_name = legs.get((view, leg_no)) or ""
                round_name = CEV_ROUNDS.get(round_of.get(view, ""), round_of.get(view, ""))
                out[mid] = Match(
                    section=section, uid=f"{section}-cev-{mid}", day=day, time=time,
                    home=cev_tidy(home), away=cev_tidy(away), paok_home=is_paok(home),
                    venue=cev_caps(spans.get("LB_Palasport", "")), competition=competition,
                    round=", ".join(x for x in (round_name, CEV_LEGS.get(leg_name, "")) if x),
                    score=f"{sets[0]}-{sets[1]}" if done else "",
                    url=f"{CEV}MatchPage.aspx?mID={mid}&ID={comp_id}",
                )
    return list(out.values())


# ---------------------------------------------------------------- ποδόσφαιρο σάλας

# Η Futsal Super League (ΕΠΣ Σάλας) δημοσιεύει το πρόγραμμα με το WordPress/SportsPress, που
# έχει δημόσιο API. Η πηγή δίνει μόνο την ημερομηνία κάθε αγωνιστικής, χωρίς ώρα· την ώρα (και
# την πραγματική μέρα) τη συμπληρώνουν οι ανακοινώσεις της ΑΣ ΠΑΟΚ (club.py).
EPS = "https://epssalas.gr/wp-json/sportspress/v2/"


def eps_json(path: str):
    return json.loads(fetch(EPS + path))


def futsal_ids() -> tuple[int, int]:
    """(διοργάνωση, σεζόν) της Futsal Super League για την τρέχουσα σεζόν."""
    y = season_start_year()
    leagues = eps_json("leagues?per_page=100&_fields=id,name")
    league = next(l["id"] for l in leagues
                  if "FUTSAL SUPER LEAGUE" in l["name"].upper() and "PLAY" not in l["name"].upper())
    seasons = eps_json("seasons?per_page=100&_fields=id,name")
    season = next(x["id"] for x in seasons if x["name"].replace(" ", "") in (f"{y}-{y + 1}", f"{y}-{(y + 1) % 100:02d}"))
    return league, season


def eps_name(text: str) -> str:
    """Χωρίς αστερίσκους, και με ελληνικά γράμματα όπου έχουν γραφτεί λατινικά (π.χ. «ΠΑΝΑΘHΝΑΪΚΟΣ»)."""
    words = clean(html.unescape(text)).replace("*", " ").split()
    return " ".join(w.translate(_LOOKALIKE) if re.search(r"[Α-Ωά-ώΆ-Ώ]", w) else w for w in words)


def futsal_matches() -> list[Match]:
    league, season = futsal_ids()
    teams = eps_json(f"teams?leagues={league}&seasons={season}&per_page=100&_fields=id,title,featured_media")
    names = {t["id"]: eps_name(t["title"]["rendered"]) for t in teams}
    media_ids = ",".join(str(t["featured_media"]) for t in teams if t.get("featured_media"))
    media = {}
    if media_ids:
        try:  # τα σήματα είναι στο κανονικό API του WordPress, όχι του SportsPress
            media = {m["id"]: m.get("source_url", "") for m in json.loads(fetch(
                EPS.replace("sportspress/v2/", "wp/v2/") + f"media?include={media_ids}&per_page=100&_fields=id,source_url"))}
        except Exception as e:
            print(f"  ! σήματα ΕΠΣ Σάλας: {e}", file=sys.stderr)
    logos = {t["id"]: media.get(t.get("featured_media"), "") for t in teams}
    paok_id = next((i for i, n in names.items() if is_paok(n)), None)
    if paok_id is None:
        raise RuntimeError("Δεν βρέθηκε ο ΠΑΟΚ στη Futsal Super League")
    events, page = [], 1
    while page < 10:
        batch = eps_json(f"events?leagues={league}&seasons={season}&per_page=100&page={page}"
                         f"&_fields=id,date,link,title,teams,results")
        events += batch
        if len(batch) < 100:
            break
        page += 1
    mine = sorted((e for e in events if paok_id in e["teams"] and len(e["teams"]) == 2), key=lambda e: e["date"])
    out = []
    for n, e in enumerate(mine, 1):
        home_id, away_id = e["teams"]
        # Τα ονόματα από τον τίτλο του αγώνα, που ακολουθεί τις αλλαγές ονομάτων· αλλιώς από τη λίστα ομάδων.
        title = re.split(r"\s+vs\s+", html.unescape(e["title"]["rendered"]), maxsplit=1)
        home_name, away_name = (eps_name(title[0]), eps_name(title[1])) if len(title) == 2 else (
            names.get(home_id, ""), names.get(away_id, ""))
        start = dt.datetime.fromisoformat(e["date"])
        goals = [(e["results"].get(str(t)) or {}).get("goals", "") if isinstance(e["results"].get(str(t)), dict) else ""
                 for t in (home_id, away_id)]
        out.append(Match(
            section="futsal", uid=f"futsal-eps-{e['id']}", day=start.date(),
            time=parse_time(start.strftime("%H:%M")),
            home=tidy_name(home_name), away=tidy_name(away_name),
            paok_home=home_id == paok_id, competition="Futsal Super League", round=f"{n}η αγωνιστική",
            score=f"{goals[0]}-{goals[1]}" if all(str(g).isdigit() for g in goals) else "",
            url=e["link"], home_logo=logos.get(home_id, ""), away_logo=logos.get(away_id, ""),
        ))
    return out


# ---------------------------------------------------------------- Β' ομάδα και ακαδημίες (paokfc.gr)

PAOKFC = "https://www.paokfc.gr/"
PAOKFC_LOGO = PAOKFC + "wp-content/themes/paokv2/images/logo-paok-small.png"
# Ο φάκελος κάθε ομάδας στο «Πρόγραμμα και αποτελέσματα» του paokfc.gr.
# Η Κ16 δεν είχε σελίδα τον Νοέμβριο του 2026: αν εμφανιστεί φάκελος που ξεκινά με «k16», τον βρίσκουμε μόνοι μας.
PAOKFC_TEAMS = {"football-b": "paok-b-nchc", "football-u19": "k20-nchc",
                "football-u17": "k17-nchc", "football-u16": "k16", "football-u15": "k15-nchc"}  # Β και Κ16: sl2.gr


def paokfc_team(links: dict[str, dict[str, str]], section: str) -> dict[str, str]:
    """Οι σελίδες της ομάδας: με το ακριβές όνομα φακέλου ή με το πρόθεμά του."""
    team = PAOKFC_TEAMS[section]
    if team in links:
        return links[team]
    return next((v for k, v in sorted(links.items()) if k.startswith(team + "-")), {})
# Οι διοργανώσεις όπως τις γράφει η πηγή → όπως τις δείχνουμε (ανά ομάδα).
PAOKFC_COMPETITIONS = {
    "Super League 2": "Super League 2",
    "Super League": "Super League {age}",
    "Κύπελλο": "Κύπελλο {age}",
    "Greek Cup": "Κύπελλο {age}",
    "Youth League": "UEFA Youth League",
}
# Η πηγή γράφει μερικές ομάδες με λατινικά ή με άλλο όνομα.
PAOKFC_NAMES = {
    "ASTERAS AKTOR": "Αστέρας Τρίπολης", "ASTERAS AKTOR B": "Αστέρας Τρίπολης Β",
    "ATHENS KALLITHEA": "Καλλιθέα", "ΠΟΤ ΗΡΑΚΛΗΣ": "Ηρακλής", "ΑΠΣ ΖΑΚΥΝΘΟΣ": "Ζάκυνθος", "OLYMPIAKOS": "Ολυμπιακός",
    "OLYMPIACOS": "Ολυμπιακός", "PANATHINAIKOS": "Παναθηναϊκός", "AEK": "ΑΕΚ", "ARIS": "Άρης",
    "KIFISIA": "Κηφισιά", "VOLOS": "Βόλος", "LEVADIAKOS": "Λεβαδειακός", "OFI": "ΟΦΗ",
    "ATROMITOS": "Ατρόμητος", "PANETOLIKOS": "Παναιτωλικός", "PANSERRAIKOS": "Πανσερραϊκός",
    "KALAMATA": "Καλαμάτα", "AEL": "ΑΕΛ", "IRAKLIS": "Ηρακλής",
}


def paokfc_name(raw: str) -> str:
    """Όνομα αντιπάλου όπως το δείχνουμε: ελληνικά όπου γίνεται, «Β» αντί για λατινικό «B»."""
    name = re.sub(r"\s+", " ", raw).strip()
    if plain(name) in PAOKFC_NAMES:
        return PAOKFC_NAMES[plain(name)]
    words = []
    for w in name.split(" "):
        # Ελληνική λέξη με λατινικό γράμμα που μοιάζει («Eλλάς», «Ολυμπιακός B»).
        if re.search(r"[Α-Ωα-ωΆ-ώ]", w) or (w in ("B", "Β") and words and re.search(r"[Α-Ωα-ωΆ-ώ]", words[-1])):
            w = "".join(_LOOKALIKE_ONE.get(c, c) for c in w)
        words.append(w)
    return " ".join(words)


_LOOKALIKE_ONE = dict(zip("ABEZHIKMNOPTYX", "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ"))


# ---- Super League 2 (sl2.gr): η ΠΑΟΚ Β και η Κ16 (Πρωτάθλημα Νέων Κ19 της Super League 2).
# Το site τα παίρνει από ανοιχτό API (sportsdata.gr): διοργανώσεις, αγώνες με ώρα, γήπεδο, κανάλι,
# σκορ, και βαθμολογίες. Οι αγώνες χωρίς ορισμένη μέρα έχουν μόνο την ημερομηνία της αγωνιστικής.
SL2_API = "https://www.sl2.gr/api/sportsdata/v1/"
SL2_NAMES = {plain(k): v for k, v in {
    "ΑΕΛ": "ΑΕΛ", "Α.Ε.Λ.": "ΑΕΛ", "ΑΕΛ NOVIBET": "ΑΕΛ",
    "ΑΠΟΛΛΩΝ ΚΑΛ.": "Απόλλων Καλαμαριάς", "ΑΠΟΛΛΩΝ ΚΑΛΑΜΑΡΙΑΣ": "Απόλλων Καλαμαριάς",
    "ΝΕΣΤΟΣ ΧΡΥΣ.": "Νέστος Χρυσούπολης", "ΝΕΣΤΟΣ ΧΡΥΣΟΥΠΟΛΗΣ": "Νέστος Χρυσούπολης",
    "ΝΙΚΗ ΒΟΛΟΥ": "Νίκη Βόλου", "ΠΑΝΘΡΑΚΙΚΟΣ": "Πανθρακικός", "ΠΑΝΣΕΡΡΑΪΚΟΣ": "Πανσερραϊκός",
    "ΑΝΑΓ. ΚΑΡΔΙΤΣΑΣ": "Αναγέννηση Καρδίτσας", "ΑΝΑΓΕΝΝΗΣΗ ΚΑΡΔΙΤΣΑΣ": "Αναγέννηση Καρδίτσας",
    "ΕΛΛΑΣ ΣΥΡΟΥ": "Ελλάς Σύρου", "ΖΑΚΥΝΘΟΣ": "Ζάκυνθος", "ATHENS KALLITHEA": "Καλλιθέα",
    "ΜΑΡΚΟ": "Μαρκό", "Γ.Σ. ΜΑΡΚΟ": "Μαρκό", "ΠΑΝΙΩΝΙΟΣ": "Πανιώνιος", "ΠΥΡΓΟΣ": "ΠΑΣ Πύργος",
    "ΟΛΥΜΠΙΑΚΟΣ Β'": "Ολυμπιακός Β", "ASTERAS AKTOR Β'": "Αστέρας Τρίπολης Β",
}.items()}
SL2_TV = {"ERT": "ΕΡΤ", "Superbet": "Superbet TV", "SL2 YouTube": "YouTube (SL2)"}


def sl2_json(path: str):
    return json.loads(fetch(SL2_API + path))


def sl2_name(raw: str) -> str:
    """«ΝΙΚΗ ΒΟΛΟΥ Κ19» → «Νίκη Βόλου»· όσα δεν ξέρουμε μένουν όπως τα γράφει η πηγή (χωρίς την κατηγορία)."""
    name = re.sub(r"\s+", " ", re.sub(r"\s+Κ\d{2}\s*$", "", raw)).strip()
    return SL2_NAMES.get(plain(name), name)


def sl2_competitions(section: str, today: dt.date | None = None) -> list[dict]:
    """Οι διοργανώσεις της σεζόν όπου παίζει η ομάδα: για την ΠΑΟΚ Β το επαγγελματικό πρωτάθλημα (και
    κύπελλα του), για την Κ16 ο όμιλος της Κ19 με τον ΠΑΟΚ."""
    today = today or dt.date.today()
    start = season_start_year(today)
    season = f"{start}-{start + 1}"
    out = []
    for c in sl2_json("competitions"):
        if c.get("season") != season:
            continue
        pro = "Επαγγελματικό" in (c.get("championship_el") or "")
        if (section == "football-b" and pro) or (section == "football-u16" and c.get("youth_type") == "u19"):
            out.append(c)
    return out


def sl2_matches(section: str, today: dt.date | None = None) -> list[Match]:
    today = today or dt.date.today()
    comps = sl2_competitions(section, today)
    if not comps:
        raise RuntimeError("δεν βρέθηκαν διοργανώσεις της σεζόν")
    out = []
    for c in comps:
        for x in sl2_json(f"competitions/{c['slug']}/matches"):
            home_paok, away_paok = is_paok(x["home_team"]["name_el"]), is_paok(x["away_team"]["name_el"])
            if home_paok == away_paok:
                continue
            day = x.get("date") or x.get("matchday_date")
            if not day:
                continue
            day = dt.date.fromisoformat(day)
            time = parse_time(x["time"]) if x.get("date") and x.get("time") else None
            score = ""
            if x.get("status") == "finished" and x.get("home_score") is not None and x.get("away_score") is not None:
                score = f"{x['home_score']}-{x['away_score']}"
            status = {"postponed": "postponed", "cancelled": "cancelled", "abandoned": "abandoned"}.get(x.get("status") or "", "")
            if not x.get("date") and day < today and not score:
                continue  # η αγωνιστική πέρασε χωρίς να οριστεί μέρα: αναβολή, δεν ξέρουμε πότε
            opp = x["away_team"] if home_paok else x["home_team"]
            if c.get("is_cup"):
                comp = re.sub(r"\s*\d{4}\s*-\s*\d{4}\s*$", "", c["title_el"]).strip()
            else:
                comp = SECTIONS[section].get("league") or "Super League 2"
            logo = lambda t: ((t.get("logo") or {}).get("thumb") or "") if not is_paok(t["name_el"]) else ""
            out.append(Match(
                section=section, uid=f"{section}-sl2-{x['id']}", day=day, time=time,
                home=PAOK if home_paok else sl2_name(opp["name_el"]), away=sl2_name(opp["name_el"]) if home_paok else PAOK,
                paok_home=home_paok, venue=(x.get("venue_el") or "").strip(" -"), competition=comp,
                round=x.get("matchday_el") or "", score=score, status=status,
                tv=SL2_TV.get(x.get("channel") or "", x.get("channel") or ""),
                home_logo=logo(x["home_team"]), away_logo=logo(x["away_team"])))
    return out


# ---- Βόλεϊ ακαδημίες: Ένωση Πετοσφαιρικών Σωματείων Θεσσαλονίκης (epesth.gr)
# Η μέρα, η ώρα και το γήπεδο είναι στα PDF προγράμματος (σελίδα «Προγράμματα»), τα σκορ και οι βαθμολογίες
# στις σελίδες των κατηγοριών (π.χ. /k18-agorion-2026-2027/), ανά αγωνιστική. Τα ενώνουμε ανά αγωνιστική και
# αντίπαλο. Τα PDF γίνονται κείμενο με το pdftotext (poppler-utils, βλ. update.yml).
EPESTH = "https://epesth.gr/"
# page: η σελίδα της κατηγορίας ({season} = «2026-2027»)· pdf: τι γράφει το όνομα του PDF· team: πώς γράφεται ο ΠΑΟΚ.
EPESTH_TEAMS = {
    "volley-u21": {"page": "k21-agorion-{season}", "pdf": "Κ21-ΑΓΟΡΙΩΝ", "team": "ΠΑΟΚ"},
    "volley-u18": {"page": "k18-agorion-{season}", "pdf": "Κ18-ΑΓΟΡΙΑ", "team": "ΠΑΟΚ"},
    "volley-women-u20": {"page": "k20-koritsion-{season}", "pdf": "Κ20-ΚΟΡΙΤΙΣΩΝ", "team": "ΠΑΟΚ"},
    "volley-women-u18": {"page": "k18-koritsion-{season}", "pdf": "Κ18-ΚΟΡΙΤΙΣΩΝ.pdf", "team": "ΠΑΟΚ"},
    "volley-women-u18es1": {"page": "k18-koritsion-e-s-{season}", "pdf": "Κ18-ΚΟΡΙΤΙΣΩΝ-Ε", "team": "ΠΑΟΚ 1"},
    "volley-women-u18es2": {"page": "k18-koritsion-e-s-{season}", "pdf": "Κ18-ΚΟΡΙΤΙΣΩΝ-Ε", "team": "ΠΑΟΚ 2"},
}
# Τα αρχικά των σωματείων (ΑΣ, ΝΓΣΘ…) φεύγουν: «ΑΣ ΑΡΗΣ» → «ΑΡΗΣ».
EPESTH_PREFIXES = {"ΑΣ", "ΝΓΣΘ", "ΟΠΑΘ", "ΑΜΟ", "ΑΣΕΓ", "ΑΠΣ", "ΑΕΣΕ"}
EPESTH_ROW = re.compile(
    r"^\s*\S+\s+(\d{1,2})/(\d{1,2})/(\d{4})\s+(.+?)\s{2,}(\d{1,2})[:.](\d{2})\s+(.+?)\s+-\s+(.+?)(?:\s{2,}.*)?$")


def epesth_season(today: dt.date | None = None) -> str:
    start = season_start_year(today or dt.date.today())
    return f"{start}-{start + 1}"


def epesth_name(raw: str) -> str:
    words = re.sub(r"\s+", " ", raw).strip().split(" ")
    while len(words) > 1 and words[0] in EPESTH_PREFIXES and not words[1].isdigit():
        words = words[1:]
    return " ".join(words)


def epesth_pdf_text(url: str) -> str:
    """Το κείμενο ενός PDF με τις στήλες στη θέση τους (pdftotext -layout)."""
    import subprocess
    import tempfile
    import urllib.request
    # Τα ονόματα των PDF έχουν ελληνικά (και «΄»): η διεύθυνση θέλει κωδικοποίηση.
    req = urllib.request.Request(urllib.parse.quote(url, safe=":/%?=&"), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(r.read())
        f.flush()
        out = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, timeout=60)
    if out.returncode:
        raise RuntimeError(f"pdftotext: {out.stderr.decode(errors='replace').strip()}")
    return out.stdout.decode("utf-8", errors="replace")


def epesth_fixtures(text: str, team: str) -> list[dict]:
    """Οι αγώνες της ομάδας σε ένα PDF προγράμματος: αγωνιστική, μέρα, ώρα, γήπεδο, γηπεδούχος, φιλοξενούμενος."""
    out, rnd = [], None
    for line in text.splitlines():
        head = re.match(r"^\s*(\d+)η\s+Αγωνιστική", line)
        if head:
            rnd = int(head.group(1))
            continue
        m = EPESTH_ROW.match(line)
        if not m or rnd is None:
            continue
        d, mo, y, venue, hh, mm, home, away = m.groups()
        home, away = home.strip(), away.strip()
        if team not in (home, away):
            continue
        out.append({"round": rnd, "day": dt.date(int(y), int(mo), int(d)), "time": dt.time(int(hh) % 24, int(mm)),
                    "venue": venue.strip(), "home": home, "away": away})
    return out


def epesth_tables(page: str) -> list[list[list[str]]]:
    return [[[clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
             for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)]
            for t in re.findall(r"<table[^>]*>(.*?)</table>", page, re.S)]


def epesth_results(page: str, team: str) -> list[dict]:
    """Τα σκορ της ομάδας από τη σελίδα της κατηγορίας: πίνακες «Nη Αγωνιστική | Σκορ» με «ΓΗΠ-ΦΙΛ | 3-1»."""
    out = []
    for rows in epesth_tables(page):
        if not rows or not rows[0]:
            continue
        head = re.match(r"(\d+)η\s+αγωνιστική", rows[0][0], re.I)
        if not head:
            continue
        for r in rows[1:]:
            if len(r) < 2 or "-" not in r[0]:
                continue
            home, away = (x.strip() for x in r[0].split("-", 1))
            if team not in (home, away):
                continue
            score = re.match(r"^(\d)\s*-\s*(\d)$", r[1])
            out.append({"round": int(head.group(1)), "home": home, "away": away,
                        "score": f"{score.group(1)}-{score.group(2)}" if score else ""})
    return out


def epesth_same(a: str, b: str) -> bool:
    """Ίδιος αντίπαλος στο PDF και στη σελίδα («ΝΓΣΘ ΗΡΑΚΛΗΣ 1908» / «ΗΡΑΚΛΗΣ», «ΠΗΓΣΑΣΟΣ» / «ΠΗΓΑΣΟΣ»)."""
    wa = {w[:5] for w in plain(a).split() if len(w) > 2 and not w.isdigit()}
    wb = {w[:5] for w in plain(b).split() if len(w) > 2 and not w.isdigit()}
    return bool(wa & wb)


_EPESTH_CRESTS: list[tuple[set, set, str]] | None = None
# Συντομογραφίες του προγράμματος που δεν μοιάζουν με το όνομα στη σελίδα των σωματείων.
EPESTH_CREST_ALIAS = {"ΕΟΣ": "ΕΟ ΣΤΑΥΡΟΥΠΟΛΗΣ"}


def epesth_words(name: str) -> list[str]:
    """Λέξεις ονόματος σωματείου, κεφαλαία, χωρίς τόνους και τελείες («Α.Ε.Ν. ΠΑΝΟΡΑΜΑΤΟΣ» → ΑΕΝ, ΠΑΝΟΡΑΜΑΤΟΣ),
    με τα λατινικά που μοιάζουν ως ελληνικά («AΡΗΣ» → «ΑΡΗΣ»)."""
    t = "".join(_LOOKALIKE_ONE.get(c, c) for c in plain(name.replace(".", "")).upper())
    return [w for w in re.findall(r"[Α-ΩA-Z0-9]+", t) if not w.isdigit()]


def epesth_crest(name: str) -> str:
    """Το σήμα του σωματείου από τη σελίδα «Τα σωματεία της ΕΠΕΣΘ» (ένα κατέβασμα ανά εκτέλεση). Ταιριάζει
    με όλες τις λέξεις (2 πόντοι η καθεμία) και με τα πρώτα 5 γράμματα (1)· μόνο μοναδικός νικητής."""
    global _EPESTH_CRESTS
    if _EPESTH_CRESTS is None:
        _EPESTH_CRESTS = []
        try:
            page = fetch(EPESTH + "ta-somateia-tis-epesth/")
            for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
                imgs = [u for u in re.findall(r'<img[^>]+src="([^"]+)"', row)
                        if "/uploads/" in u and not re.search(r"/(Ball\w*|Bala)\.\w+$", u)]
                cells = [clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
                cells = [c for c in cells if c and not c.strip(" .").isdigit()]
                if imgs and cells:
                    words = epesth_words(cells[0])
                    _EPESTH_CRESTS.append((set(words), {w[:5] for w in words if len(w) > 3},
                                           urllib.parse.quote(imgs[0], safe=":/%")))
        except Exception as e:
            print(f"  ! σήματα ΕΠΕΣΘ: {e}", file=sys.stderr)
    words = epesth_words(EPESTH_CREST_ALIAS.get(name.strip(), name))
    if not words:
        return ""
    scored = []
    for full, prefixes, url in _EPESTH_CRESTS:
        score = 2 * len(set(words) & full) + len({w[:5] for w in words if len(w) > 3} & prefixes)
        if score:
            scored.append((score, url))
    scored.sort(reverse=True)
    if not scored or (len(scored) > 1 and scored[1][0] == scored[0][0]):
        return ""
    return scored[0][1]


def epesth_matches(section: str, today: dt.date | None = None) -> list[Match]:
    today = today or dt.date.today()
    cfg, season = EPESTH_TEAMS[section], epesth_season(today)
    team = cfg["team"]
    listing = fetch(EPESTH + "programmata/")
    pdfs = sorted({u for u in re.findall(r'href="(https://epesth\.gr/wp-content/uploads/[^"]+\.pdf)"', listing)
                   if cfg["pdf"] in urllib.parse.unquote(u)})
    fixtures = []
    for u in pdfs:
        try:
            fixtures += epesth_fixtures(epesth_pdf_text(u), team)
        except Exception as e:
            print(f"  ! {section}: {urllib.parse.unquote(u).rsplit('/', 1)[-1]}: {e}", file=sys.stderr)
    try:
        results = epesth_results(fetch(EPESTH + cfg["page"].format(season=season) + "/"), team)
    except Exception as e:
        print(f"  ! {section}: σελίδα κατηγορίας: {e}", file=sys.stderr)
        results = []
    if not fixtures and not results:
        raise RuntimeError("δεν βρέθηκαν αγώνες της ομάδας")
    comp = SECTIONS[section].get("league") or SECTIONS[section]["name"]
    out, used = [], set()
    for f in fixtures:
        home = f["home"] == team
        opp = f["away"] if home else f["home"]
        score = ""
        for i, r in enumerate(results):
            if i not in used and r["round"] == f["round"] and (r["home"] == team) == home \
                    and epesth_same(r["away"] if home else r["home"], opp):
                score, _ = r["score"], used.add(i)
                break
        name = epesth_name(opp)
        out.append(Match(
            section=section, uid=f"{section}-{season[:4]}-{short_hash(str(f['round']), 'h' if home else 'a', plain(name))}",
            day=f["day"], time=f["time"], home=PAOK if home else name, away=name if home else PAOK, paok_home=home,
            venue=f["venue"], competition=comp, round=f"{f['round']}η αγωνιστική", score=score,
            home_logo="" if home else epesth_crest(name), away_logo=epesth_crest(name) if home else ""))
    return out


# ---- ΕΠΣ Μακεδονίας (ποδόσφαιρο υποδομών): το πρόγραμμα βγαίνει κάθε εβδομάδα σε ανακοίνωση
# («Πρόγραμμα αγώνων υποδομών …», article.asp?code=…) και τα αποτελέσματα της τελευταίας αγωνιστικής στη σελίδα
# βαθμολογίας κάθε κατηγορίας. Δεν υπάρχει όλο το πρόγραμμα της σεζόν σε ένα σημείο, οπότε κρατάμε όσα βρίσκουμε
# στο docs/epsm.json (ποιες ανακοινώσεις διαβάστηκαν, οι αγώνες τους, τα σκορ) και τα συμπληρώνουμε σε κάθε εκτέλεση.
EPSM = "https://www.epsm.gr/"
EPSM_FIRST = 14860  # η πρώτη ανακοίνωση της σεζόν 2026-27 (όμιλοι υποδομών 1/10/2026)
EPSM_STATE = OUT_DIR / "epsm.json"
# Ανά τμήμα: κατηγορία στο πρόγραμμα (χωρίς κενά/παύλες), κατηγορία στη βαθμολογία, όνομα ομάδας.
EPSM_TEAMS = {
    "football-u14": {"cat": "Κ15LEAGUE1", "table": "Κ15 LEAGUE 1", "team": "ΠΑΕ ΠΑΟΚ Κ14"},
    "football-u13": {"cat": "Κ14LEAGUE1", "table": "Κ14 LEAGUE 1", "team": "ΠΑΕ ΠΑΟΚ Κ13 (1)"},
    "football-u13b": {"cat": "Κ14LEAGUE2", "table": "Κ14 LEAGUE 2", "team": "ΠΑΕ ΠΑΟΚ Κ13 (2)"},
    "football-u12": {"cat": "Κ13ΕΙΔΙΚΗ", "table": "Κ13 ΕΙΔΙΚΗΣ 1ος ΟΜΙΛΟΣ", "team": "ΠΑΕ ΠΑΟΚ Κ12"},
    "football-women-u15": {"cat": "Κ15ΓΥΝΑΙΚΩΝ", "table": "Κ15 ΓΥΝΑΙΚΩΝ", "team": "ΑΣ ΠΑΟΚ (1)"},
    "football-women-u15b": {"cat": "Κ15ΓΥΝΑΙΚΩΝ", "table": "Κ15 ΓΥΝΑΙΚΩΝ", "team": "ΑΣ ΠΑΟΚ (2)"},
    "football-women-u12": {"cat": "Κ12ΚΟΡΑΣΙΔΩΝ", "table": "Κ12 ΚΟΡΑΣΙΔΩΝ", "team": "ΑΣ ΠΑΟΚ"},
}
GREEK_MONTHS_GEN = {"ΙΑΝΟΥΑΡΙΟΥ": 1, "ΦΕΒΡΟΥΑΡΙΟΥ": 2, "ΜΑΡΤΙΟΥ": 3, "ΑΠΡΙΛΙΟΥ": 4, "ΜΑΙΟΥ": 5, "ΙΟΥΝΙΟΥ": 6,
                    "ΙΟΥΛΙΟΥ": 7, "ΑΥΓΟΥΣΤΟΥ": 8, "ΣΕΠΤΕΜΒΡΙΟΥ": 9, "ΟΚΤΩΒΡΙΟΥ": 10, "ΝΟΕΜΒΡΙΟΥ": 11, "ΔΕΚΕΜΒΡΙΟΥ": 12}
_EPSM: dict = {}


def epsm_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("–", "-")).strip()


def epsm_cat(line: str) -> str:
    """«ΚΑΤΗΓΟΡΙΑ Κ-15 LEAGUE1 (2012 και νεότεροι)» → «Κ15LEAGUE1»."""
    t = re.sub(r"\(.*?\)", "", line.replace("ΚΑΤΗΓΟΡΙΑ", ""))
    return re.sub(r"[\s\-–]", "", plain(t).upper())


def epsm_program(page: str) -> list[dict]:
    """Οι αγώνες μιας ανακοίνωσης προγράμματος: κατηγορία, αγωνιστική, μέρα, ώρα, γήπεδο, σημείωση."""
    i = page.find("ΠΡΟΓΡΑΜΜΑ")
    if i < 0:
        return []
    lines = [clean(x) for x in re.split(r"<br\s*/?>", page[i:].split("</p>")[0]) if clean(x)]
    out, day, cat, rnd = [], None, "", ""
    for n, line in enumerate(lines):
        u = plain(line).upper()
        m = re.match(r"(ΔΕΥΤΕΡΑΣ|ΤΡΙΤΗΣ|ΤΕΤΑΡΤΗΣ|ΠΕΜΠΤΗΣ|ΠΑΡΑΣΚΕΥΗΣ|ΣΑΒΒΑΤΟΥ|ΚΥΡΙΑΚΗΣ)\s*(\d{1,2})\s*([Α-Ω]+)\s*(\d{4})", u)
        if m and m.group(3) in GREEK_MONTHS_GEN:
            day = dt.date(int(m.group(4)), GREEK_MONTHS_GEN[m.group(3)], int(m.group(2)))
            continue
        if u.startswith("ΚΑΤΗΓΟΡΙΑ"):
            cat, rnd = epsm_cat(line), ""
            continue
        m = re.search(r"\((\d+)η\s*αγωνιστικη\)", plain(line).lower())
        if m:
            rnd = m.group(1)
            continue
        if not day or " - " not in line.replace("–", "-") or u.startswith(("ΓΗΠΕΔΟ", "ΓΙΑΤΡΟΣ", "ΡΕΠΟ")):
            continue
        rest = re.split(r"\s*-{3,}\s*", line.replace("–", "-"), maxsplit=1)
        teams, note = rest[0], (rest[1].strip(" -") if len(rest) > 1 else "")
        if teams.count(" - ") != 1:
            continue
        home, away = (epsm_name(x) for x in teams.split(" - "))
        when, venue, time = day, "", None
        nxt = lines[n + 1] if n + 1 < len(lines) else ""
        v = re.match(r"Γήπεδο:\s*(.*?)\s*-?\s*ώρα:\s*(\d{1,2})[.:](\d{2})", nxt)
        if v:
            venue, time = v.group(1).strip(" -"), dt.time(int(v.group(2)), int(v.group(3)))
        moved = re.search(r"(\d{1,2})-(\d{1,2})-(\d{4})", note)
        if moved:
            when = dt.date(int(moved.group(3)), int(moved.group(2)), int(moved.group(1)))
        status = "cancelled" if "ΜΑΤΑΙΩ" in plain(note).upper() else "postponed" if "ΑΝΑΒΟΛ" in plain(note).upper() else ""
        out.append({"cat": cat, "round": rnd, "day": when.isoformat(), "time": time.strftime("%H:%M") if time else "",
                    "home": home, "away": away, "venue": venue, "status": status})
    return out


def epsm_rounds(page: str) -> list[dict]:
    """Το «Αναλυτικό πρόγραμμα» μιας κατηγορίας (table_ypodomon_analytika.asp): όλες οι αγωνιστικές της σεζόν
    με τους αγώνες τους και το σκορ όσων έγιναν, χωρίς ημερομηνίες («Α - Β 4 - 1» ή «Α - Β -»)."""
    page = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", "", page)
    tokens = [re.sub(r"\s+", " ", t).strip() for t in html.unescape(re.sub(r"<[^>]+>", "|", page)).split("|")]
    tokens = [t for t in tokens if t]
    out, rnd = [], ""
    for i, t in enumerate(tokens):
        if t == "ΑΓΩΝΙΣΤΙΚΗ" and i >= 2 and tokens[i - 1] == "η" and tokens[i - 2].isdigit():
            rnd = tokens[i - 2]
            continue
        if not rnd:
            continue
        t = t.replace("–", "-")
        m = re.match(r"^(.+?) - (.+?)(?:\s+(\d+)\s*-\s*(\d+)|\s+-)$", t)
        if m:
            out.append({"round": rnd, "home": epsm_name(m.group(1)), "away": epsm_name(m.group(2)),
                        "score": f"{m.group(3)}-{m.group(4)}" if m.group(3) else ""})
    return out


def epsm_is_program(page: str) -> bool:
    """Ο τίτλος της ανακοίνωσης (λίγο πριν από το «Γραφείο Τύπου») είναι «Πρόγραμμα … υποδομών …»."""
    text = clean(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", "", page))
    i = text.find("Γραφείο Τύπου")
    return i > 0 and bool(re.search(r"Πρόγραμμα[^.]{0,40}υποδομών", text[max(0, i - 160):i]))


def epsm_table_url(cat: str, page: str = "") -> str:
    page = page or ("table.asp" if cat.startswith("Κ17") else "table_ypodomon.asp")
    return EPSM + page + "?" + urllib.parse.urlencode({"diorganosi": cat})


def epsm_state(path: Path | None = None) -> dict:
    """Διαβάζει τις νέες ανακοινώσεις και τα νέα σκορ μία φορά ανά εκτέλεση και τα κρατά στο docs/epsm.json."""
    if "state" in _EPSM:
        return _EPSM["state"]
    path = path or EPSM_STATE
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    state.setdefault("scanned", EPSM_FIRST - 1)
    state.setdefault("programs", {})
    state.pop("results", None)
    listing = fetch(EPSM + "program.asp")
    latest = max([int(c) for c in re.findall(r"article\.asp\?code=(\d+)", listing)] + [state["scanned"]])
    # Οι ανακοινώσεις έχουν αύξοντα αριθμό: διαβάζουμε όσες δεν έχουμε δει (τίτλος «Πρόγραμμα … υποδομών»).
    for code in range(state["scanned"] + 1, latest + 1):
        try:
            page = fetch(f"{EPSM}article.asp?code={code}")
        except Exception as e:  # π.χ. ανακοίνωση που σβήστηκε: την προσπερνάμε
            print(f"  ! ΕΠΣΜ ανακοίνωση {code}: {e}", file=sys.stderr)
            state["scanned"] = code
            continue
        if epsm_is_program(page):
            state["programs"][str(code)] = epsm_program(page)
        state["scanned"] = code
    if path == EPSM_STATE and os.environ.get("EPSM_SAVE", "1") == "1":
        path.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    _EPSM["state"] = state
    return state


def epsm_matches(section: str, state: dict | None = None, rounds: list[dict] | None = None) -> list[Match]:
    """Οι αγώνες από το αναλυτικό πρόγραμμα της κατηγορίας (όλη η σεζόν, με σκορ) και μέρα, ώρα και γήπεδο από
    τις εβδομαδιαίες ανακοινώσεις. Αγωνιστική χωρίς ανακοίνωση ακόμα: η μέρα της αγωνιστικής αν είναι γνωστή από
    άλλους αγώνες, αλλιώς μία εβδομάδα μετά την προηγούμενη γνωστή, χωρίς ώρα."""
    cfg = EPSM_TEAMS[section]
    state = state or epsm_state()
    if rounds is None:
        rounds = epsm_rounds(fetch(epsm_table_url(cfg["table"], "table_ypodomon_analytika.asp")))
    rows: dict[tuple[str, str], dict] = {}
    round_day: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for code in sorted(state["programs"], key=int):  # οι νεότερες ανακοινώσεις διορθώνουν τις παλιότερες
        for g in state["programs"][code]:
            if g["cat"] != cfg["cat"]:
                continue
            rows[(g["home"], g["away"])] = g
            if g["round"] and not g["status"]:
                round_day[g["round"]][g["day"]] += 1
    known = {r: dt.date.fromisoformat(c.most_common(1)[0][0]) for r, c in round_day.items()}
    comp = SECTIONS[section]["league"]
    out = []
    for g in rounds:
        if cfg["team"] not in (g["home"], g["away"]):
            continue
        home = g["home"] == cfg["team"]
        opp = g["away"] if home else g["home"]
        rnd = int(g["round"])
        info = rows.get((g["home"], g["away"]))
        if info:
            day, time = dt.date.fromisoformat(info["day"]), dt.time.fromisoformat(info["time"]) if info["time"] else None
        elif g["round"] in known:
            day, time = known[g["round"]], None
        else:
            before = [int(r) for r in known if int(r) < rnd]
            if not before:
                continue
            last = max(before)
            day, time = known[str(last)] + dt.timedelta(days=7 * (rnd - last)), None
        status = "" if g["score"] else (info or {}).get("status", "")
        out.append(Match(
            section=section, uid=f"{section}-epsm-{short_hash(str(season_start_year()), g['round'], 'h' if home else 'a', opp)}",
            day=day, time=time, home=PAOK if home else opp, away=opp if home else PAOK, paok_home=home,
            venue=(info or {}).get("venue", ""), competition=comp, round=f"{rnd}η αγωνιστική", score=g["score"],
            status=status, url=epsm_table_url(cfg["table"], "table_ypodomon_analytika.asp")))
    if not out:
        raise RuntimeError("δεν βρέθηκαν αγώνες της ομάδας στο αναλυτικό πρόγραμμα της ΕΠΣΜ")
    return out


# ---- ΕΚΑΣΘ (μπάσκετ Θεσσαλονίκης): το MatchCenter της ένωσης (ekasth.gr/champs/matchcenter8) δίνει JSON με
# όλες τις διοργανώσεις («channels»), και ανά διοργάνωση ομίλους με βαθμολογία και όλες τις αγωνιστικές.
EKASTH = "https://ekasth.gr/champs/matchcenter8/"
# Ανά τμήμα: (λέξη στο όνομα της διοργάνωσης, όνομα ομάδας). Η πρώτη είναι το πρωτάθλημα (για τη βαθμολογία).
EKASTH_TEAMS = {
    "basketball-u18": [("ΕΦΗΒΩΝ", "ΑΣ ΠΑΟΚ"), ("RISING STARS U18", "ΑΣ ΠΑΟΚ")],
    "basketball-u16": [("ΠΑΙΔΩΝ", "ΑΣ ΠΑΟΚ 1"), ("GEN A RISING STARS U16", "ΑΣ ΠΑΟΚ 1")],
    "basketball-u16b": [("ΠΑΙΔΩΝ", "ΑΣ ΠΑΟΚ 2")],
    "basketball-women-u18": [("ΝΕΑΝΙΔΩΝ", "ΑΣ ΠΑΟΚ")],
    "basketball-women-u16": [("ΚΟΡΑΣΙΔΩΝ", "ΠΑΟΚ ΑΣ 1"), ("W RISING STARS U16", "ΑΣ ΠΑΟΚ")],
    "basketball-women-u16b": [("ΚΟΡΑΣΙΔΩΝ", "ΠΑΟΚ ΑΣ 2")],
}
_EKASTH: dict = {}


def ekasth_json(action: str, **params) -> dict:
    key = (action, tuple(sorted(params.items())))
    if key not in _EKASTH:
        _EKASTH[key] = json.loads(fetch(EKASTH + "bgapi.php?" + urllib.parse.urlencode({"action": action, **params})))
    return _EKASTH[key]


def ekasth_channel(word: str) -> dict:
    """Η διοργάνωση με αυτό το όνομα («ΠΑΙΔΩΝ 2026-2027»)· το «RISING STARS U18» δεν πιάνει το «GEN A …»."""
    chans = ekasth_json("channels").get("channels", [])
    found = [c for c in chans if re.sub(r"\s*\d{4}-\d{4}$", "", c["name"].replace("ΕΚΑΣΘ ", "")).strip() == word] or \
        [c for c in chans if c["name"].startswith(word + " ")]
    if not found:
        raise RuntimeError(f"δεν βρέθηκε η διοργάνωση {word}")
    return ekasth_json("channel", ch=found[0]["id"])


def ekasth_logo(url: str | None) -> str:
    return absolute(EKASTH, url) if url else ""


def ekasth_round(md: str) -> str:
    """«1η ΑΓΩΝΙΣΤΙΚΗ», «1 ΑΓΩΝΙΣΤΙΚΗ», «7η Αγωνιστική» → «1η αγωνιστική»."""
    m = re.match(r"\s*(\d+)\s*η?\s*αγωνιστικη\s*$", plain(md or "").lower())
    return f"{m.group(1)}η αγωνιστική" if m else (md or "")


EKASTH_PHASES = {"ΦΑΣΗ ΤΩΝ": "Φάση των", "ΗΜΙΤΕΛΙΚΗ ΦΑΣΗ": "Ημιτελική φάση", "ΠΡΟΗΜΙΤΕΛΙΚΗ ΦΑΣΗ": "Προημιτελική φάση",
                 "ΤΕΛΙΚΗ ΦΑΣΗ": "Τελική φάση", "ΤΕΛΙΚΗ": "Τελική", "ΤΕΛΙΚΟΣ": "Τελικός"}


def ekasth_phase(name: str) -> str:
    """«ΠΡΟΚΡΙΜΑΤΙΚΗ ΦΑΣΗ · ΦΑΣΗ ΤΩΝ 8» → «Φάση των 8» (με τόνους· αλλιώς ως έχει)."""
    t = (name or "").split(" · ")[-1].strip()
    for k, v in EKASTH_PHASES.items():
        if t == k or t.startswith(k + " "):
            return v + t[len(k):]
    return t


def ekasth_matches(section: str) -> list[Match]:
    out = []
    for i, (word, team) in enumerate(EKASTH_TEAMS[section]):
        try:
            ch = ekasth_channel(word)
        except Exception as e:
            if i == 0:
                raise
            print(f"  ! {section}: {word}: {e}", file=sys.stderr)
            continue
        comp = SECTIONS[section]["league"] if i == 0 else word.title() + " (ΕΚΑΣΘ)"
        for g in ch.get("groups", []):
            for md in g.get("matchdays", []):
                for x in md.get("games", []):
                    h, a = x["home"], x["away"]
                    if team not in (h["name"], a["name"]):
                        continue
                    home = h["name"] == team
                    opp = a if home else h
                    when = dt.datetime.fromisoformat(x["date"]).astimezone(ATHENS)
                    known = (when.hour, when.minute) not in ((0, 0), (0, 1), (0, 2))
                    done = x.get("state") == "Completed" and h.get("score") is not None and a.get("score") is not None
                    phase = "" if i == 0 else ekasth_phase(g["name"])
                    out.append(Match(
                        section=section, uid=f"{section}-ek-{x['id']}", day=when.date(), time=when.time() if known else None,
                        home=PAOK if home else opp["name"], away=opp["name"] if home else PAOK, paok_home=home,
                        venue=x.get("stadium") or "",
                        competition=comp, round=", ".join(p for p in (phase, ekasth_round(md.get("name", ""))) if p),
                        score=f"{h['score']}-{a['score']}" if done else "",
                        url=f"{EKASTH}game.html?id={x['id']}",
                        home_logo="" if home else ekasth_logo(opp.get("logo")),
                        away_logo=ekasth_logo(opp.get("logo")) if home else ""))
    if not out:
        raise RuntimeError("δεν βρέθηκαν αγώνες της ομάδας")
    return out


def paokfc_fetch(url: str) -> str:
    """Το paokfc.gr απαντά 403 στο urllib της Python (έλεγχος για bots) αλλά όχι στο curl."""
    key = (url, None, "utf-8")
    if key not in _FETCHED:
        import subprocess
        r = subprocess.run(["curl", "-sSL", "--fail", "--max-time", "60", "-A", UA,
                            "-H", "Accept: text/html,application/xhtml+xml", "-H", "Accept-Language: el,en", url],
                           capture_output=True, timeout=90)
        if r.returncode:
            raise RuntimeError(f"curl {url}: {r.stderr.decode(errors='replace').strip()}")
        _FETCHED[key] = r.stdout.decode("utf-8", errors="replace")
    return _FETCHED[key]


def paokfc_links(season: str) -> dict[str, dict[str, str]]:
    """Οι σελίδες (πρόγραμμα, αποτελέσματα, βαθμολογία) κάθε ομάδας για τη σεζόν. Τα ονόματά τους
    διαφέρουν από ομάδα σε ομάδα (π.χ. «k20-programma-16-nch», «apotelesmata-u15»), οπότε τα
    βρίσκουμε από το μενού της σελίδας της σεζόν."""
    page = paokfc_fetch(f"{PAOKFC}programma-kai-apotelesmata/{season}/")
    out: dict[str, dict[str, str]] = {}
    for team, slug in re.findall(rf'href="[^"]*/programma-kai-apotelesmata/{season}/([a-z0-9-]+)/([a-z0-9-]+)/?"', page):
        kind = ("results" if "apotelesmata" in slug else "fixtures" if "programma" in slug
                else "table" if "vathmologia" in slug else "")
        if kind:
            out.setdefault(team, {}).setdefault(kind, f"{PAOKFC}programma-kai-apotelesmata/{season}/{team}/{slug}/")
    return out


def paokfc_items(page: str) -> list[dict]:
    """Οι αγώνες μιας σελίδας προγράμματος ή αποτελεσμάτων του paokfc.gr (δύο μορφές HTML)."""
    out = []
    for cls, body in re.findall(r'<li class="(home|away)\s[^"]*">(.*?)</li>', page, re.S):
        live = re.sub(r"<!--.*?-->", "", body, flags=re.S)
        info = re.search(r"<span>([^<|]+?)\s*\|\s*([^<]*)</span>", live)
        if not info:
            continue
        planned = re.search(r"<span>[^<|]+\|\s*(\d{2}\.\d{2}\.\d{4})", body)  # και μέσα σε σχόλιο
        when = re.search(r"(\d{2})\.(\d{2})\.(\d{4})(?:\s*,\s*(\d{1,2}:\d{2}))?", info.group(2))
        names = [clean(x) for x in re.findall(r'class="(?:one-third rival-team|rival-teamname|home-teamname)">(.*?)</', live, re.S)]
        names = [n for n in names if n and not is_paok(n)]
        if not names:
            continue
        logos = [u for u in re.findall(r'<img[^>]+src="([^"]+)"', live) if "logo-paok-small" not in u]
        us = re.search(r'<span class="paok-score[^"]*">\s*(\d+)\s*</span>', live)
        them = re.search(r'<span class="rival-score[^"]*">\s*(\d+)\s*</span>', live)
        link = re.search(r'href="(https://www\.paokfc\.gr/matches/[^"#]+)', body)
        out.append({
            "home": cls == "home", "competition": clean(info.group(1)), "opponent": names[0],
            "logo": logos[0] if logos else "",
            "day": dt.date(int(when.group(3)), int(when.group(2)), int(when.group(1))) if when else
                   dt.datetime.strptime(planned.group(1), "%d.%m.%Y").date() if planned else None,
            "time": parse_time(when.group(4)) if when and when.group(4) else None,
            "dated": bool(when),
            "score": (int(us.group(1)), int(them.group(1))) if us and them else None,
            "url": link.group(1).rstrip("/") + "/" if link else "",
        })
    return out


def paokfc_matches(section: str, today: dt.date | None = None) -> list[Match]:
    """Β' ομάδα και ακαδημίες από το «Πρόγραμμα και αποτελέσματα» του paokfc.gr.

    Ο αγώνας χωρίς ανακοινωμένη ημερομηνία («Ημερομηνία: N/A») μπαίνει στην ημερομηνία της αγωνιστικής
    που γράφει η πηγή στο κρυφό της σχόλιο, χωρίς ώρα. Αν αυτή έχει περάσει χωρίς αποτέλεσμα, ο αγώνας
    έχει μετατεθεί και δεν ξέρουμε ακόμα πότε: δεν τον δείχνουμε μέχρι να οριστεί."""
    today = today or dt.date.today()
    season = f"{season_start_year(today)}-{season_start_year(today) + 1}"
    links = paokfc_team(paokfc_links(season), section)
    if not links.get("fixtures") and not links.get("results"):
        raise RuntimeError(f"δεν βρέθηκαν οι σελίδες της ομάδας για τη σεζόν {season}")
    age = SECTIONS[section]["name"]
    start = season_start_year(today)
    out: dict[tuple, Match] = {}
    for kind in ("fixtures", "results"):
        if not links.get(kind):
            continue
        page = paokfc_fetch(links[kind])
        for it in paokfc_items(page):
            if not it["day"]:
                continue
            if not dt.date(start, 7, 1) <= it["day"] < dt.date(start + 1, 7, 1):
                # Λάθος έτος στην πηγή (π.χ. «27.09.2006»): η μέρα και ο μήνας της σεζόν μετρούν.
                it["day"] = it["day"].replace(year=start if it["day"].month >= 7 else start + 1)
            if not it["dated"] and it["day"] < today and not it["score"]:
                continue
            opp = paokfc_name(it["opponent"])
            comp = PAOKFC_COMPETITIONS.get(it["competition"], it["competition"]).format(age=age)
            if SECTIONS[section].get("league") and it["competition"] in ("Super League", "Super League 2"):
                comp = SECTIONS[section]["league"]
            score = ""
            if it["score"]:
                us, them = it["score"]
                score = f"{us}-{them}" if it["home"] else f"{them}-{us}"
            # Η πηγή δείχνει κάθε λίστα δύο φορές και τον αγώνα που μόλις έγινε και στα δύο:
            # ένας αγώνας ανά μέρα, έδρα και αντίπαλο, με το αποτέλεσμα όπου υπάρχει.
            key = (it["day"], it["home"], plain(opp))
            if key in out and (out[key].score or not score):
                continue
            # Αναγνωριστικό από διοργάνωση, έδρα και αντίπαλο (όχι από τη μέρα): μένει ίδιο όταν
            # ορίζεται ή αλλάζει η ημερομηνία, ώστε να μη χάνονται οι ειδοποιήσεις του αγώνα.
            uid = f"{section}-{start}-{short_hash(comp, 'h' if it['home'] else 'a', plain(opp))}"
            if any(m.uid == uid and k[0] != it["day"] for k, m in out.items()):
                uid += f"-{it['day']:%m%d}"  # δεύτερος αγώνας με τον ίδιο αντίπαλο στην ίδια έδρα
            out[key] = Match(
                section=section, uid=uid, day=it["day"], time=it["time"],
                home=PAOK if it["home"] else opp, away=opp if it["home"] else PAOK, paok_home=it["home"],
                competition=comp, score=score, url=it["url"] if score else "",
                home_logo=PAOKFC_LOGO if it["home"] else it["logo"], away_logo=it["logo"] if it["home"] else PAOKFC_LOGO)
    return list(out.values())


# ---------------------------------------------------------------- iCal

def ics_escape(s: str) -> str:
    return (s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
             .replace("\n", "\\n"))


def fold(line: str) -> str:
    raw, parts = line.encode("utf-8"), []
    while len(raw) > 75:
        cut = 75
        while cut > 0 and (raw[cut] & 0xC0) == 0x80:
            cut -= 1
        parts.append(raw[:cut].decode("utf-8"))
        raw = b" " + raw[cut:]
    parts.append(raw.decode("utf-8"))
    return "\r\n".join(parts)


VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Athens
BEGIN:DAYLIGHT
TZOFFSETFROM:+0200
TZOFFSETTO:+0300
TZNAME:EEST
DTSTART:19700329T030000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0300
TZOFFSETTO:+0200
TZNAME:EET
DTSTART:19701025T040000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE""".split("\n")


def build_ics(cal_name: str, matches: list[Match], stamp: str) -> str:
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//PAOK-calendar//EL",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(cal_name)}", "X-WR-TIMEZONE:Europe/Athens",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H",
        *VTIMEZONE,
    ]
    for m in sorted(matches, key=lambda m: (m.start(), m.uid)):
        emoji = SECTIONS[m.section]["emoji"]
        middle = f" {m.score} " if m.score else " – "
        summary = f"{emoji} {m.home}{middle}{m.away}"
        if m.status:
            word = unicodedata.normalize("NFD", STATUS_TEXT.get(m.status, m.status).upper())
            summary = f"{''.join(c for c in word if not unicodedata.combining(c))}: {summary}"  # ελληνικά κεφαλαία χωρίς τόνο
        if m.note and m.score:
            summary += f" ({m.note})"
        if m.time is None:
            summary += " (ώρα αναμένεται)"
        desc = [x for x in (m.competition, m.round) if x]
        desc = [" – ".join(desc)] if desc else []
        if m.score:
            desc.append(f"Τελικό σκορ: {m.home} {m.score} {m.away}" + (f" ({m.note})" if m.note else ""))
        elif m.status:
            desc.append(STATUS_TEXT.get(m.status, m.status) + (f": {m.note}" if m.note else ""))
        if m.tv or m.tv_url:
            desc.append(f"TV: {m.tv or 'Live streaming'}" + (f" {m.tv_url}" if m.tv_url else ""))
        if m.time is None:
            desc.append("Η ώρα δεν έχει οριστεί ακόμα (προσωρινά 18:00). "
                        "Θα ενημερωθεί αυτόματα όταν ανακοινωθεί.")
        start = m.start()
        lines += [
            "BEGIN:VEVENT",
            f"UID:{m.uid}@paok-calendar",
            f"DTSTAMP:{stamp}",
            f"DTSTART;TZID=Europe/Athens:{start:%Y%m%dT%H%M%S}",
            f"DTEND;TZID=Europe/Athens:{start + GAME_LENGTH:%Y%m%dT%H%M%S}",
            f"SUMMARY:{ics_escape(summary)}",
        ]
        if m.status == "cancelled":
            lines.append("STATUS:CANCELLED")
        if m.venue:
            lines.append(f"LOCATION:{ics_escape(m.venue)}")
        if desc:
            lines.append(f"DESCRIPTION:{ics_escape(chr(10).join(desc))}")
        if m.url:
            lines.append(f"URL:{m.url}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def without_stamp(text: str) -> str:
    return re.sub(r"^DTSTAMP:.*$", "", text, flags=re.M)


def write_if_changed(path: Path, content: str, ignore: Callable[[str], str] = without_stamp) -> bool:
    old = path.read_bytes().decode("utf-8") if path.exists() else None  # χωρίς μετατροπή \r\n
    if old is not None and ignore(old) == ignore(content):
        return False
    path.write_text(content, encoding="utf-8", newline="")
    return True


# ---------------------------------------------------------------- χειροκίνητοι αγώνες

MANUAL_PATH = Path(__file__).resolve().parent / "manual.json"


def manual_matches(section: str, official: list[Match]) -> list[Match]:
    """Αγώνες που ανακοινώθηκαν αλλά δεν έχουν μπει ακόμα στην επίσημη πηγή (manual.json).

    Μόλις η πηγή δημοσιεύσει αγώνα του ΠΑΟΚ την ίδια μέρα (±1) με την ίδια έδρα, ο χειροκίνητος
    αγνοείται, οπότε το manual.json δεν χρειάζεται καθάρισμα.
    """
    if not MANUAL_PATH.exists():
        return []
    out = []
    for e in json.loads(MANUAL_PATH.read_text(encoding="utf-8")):
        if e.get("section") != section:
            continue
        if e.get("status"):
            # Αναβολή/ματαίωση που ανακοινώθηκε (π.χ. από την ΑΣ ΠΑΟΚ) για αγώνα της επίσημης πηγής:
            # σημειώνεται στον αγώνα της ίδιας μέρας, δεν προστίθεται νέος.
            day = dt.date.fromisoformat(e["date"])
            for m in official:
                if m.day == day and not m.score and ("home" not in e or m.paok_home == is_paok(e["home"])):
                    m.status, m.note = e["status"], e.get("reason", m.note)
            continue
        day = dt.date.fromisoformat(e["date"])
        paok_home = is_paok(e["home"])
        same = [m for m in official if abs((m.day - day).days) <= 1 and m.paok_home == paok_home]
        if same:
            # "fix_time": η ώρα της καταχώρισης διορθώνει λάθος ώρα της πηγής (π.χ. το ESPN μία ώρα αργότερα).
            if e.get("fix_time") and e.get("time"):
                for m in same:
                    if m.day == day:
                        m.time = parse_time(e["time"])
            continue
        out.append(Match(
            section=section, uid=f"{section}-manual-{short_hash(e['date'], e['home'], e['away'])}",
            day=day, time=parse_time(e.get("time", "")), home=tidy_name(e["home"]), away=tidy_name(e["away"]),
            paok_home=paok_home, venue=e.get("venue", ""), competition=e.get("competition", ""),
            round=e.get("round", ""), url=e.get("url", ""),
            score=parse_score(e.get("score", "")),  # π.χ. "2-1" (γηπεδούχος-φιλοξενούμενος), για αγώνα που έγινε
        ))
    return out


# ---------------------------------------------------------------- καταχωρίσεις του διαχειριστή

ADMIN_URL = "https://paokalendar.gr/api/admin"
_ADMIN: dict = {}


def admin_entries() -> dict[str, dict]:
    """Ό,τι έγραψε ο διαχειριστής από τη σελίδα του αγώνα (api/admin.js), ανά αγώνα (nt)."""
    if "entries" not in _ADMIN:
        try:
            got = json.loads(fetch(ADMIN_URL))
            _ADMIN["entries"] = {e["nt"]: e for e in got.get("entries", [])}
            _ADMIN["live"] = {e["nt"]: e for e in got.get("live", [])}
            _ADMIN["custom"] = got.get("custom", [])
            _ADMIN["info"] = {e["nt"]: e for e in got.get("info", [])}
        except Exception as e:
            print(f"  ! καταχωρίσεις διαχειριστή: {e}", file=sys.stderr)
            _ADMIN["entries"] = {}
            _ADMIN["live"] = {}
            _ADMIN["custom"] = []
            _ADMIN["info"] = {}
    return _ADMIN["entries"]


def custom_matches(section: str, official: list[Match]) -> list[Match]:
    """Οι αγώνες που έβαλε ο διαχειριστής από τη φόρμα «Νέος αγώνας» (api/admin.js, συλλογή custom).

    Όπως στο manual.json: αν η πηγή έχει αγώνα του ΠΑΟΚ την ίδια μέρα (±1) με την ίδια έδρα, μετρά
    εκείνος. Το σκορ της φόρμας περνά στον αγώνα της πηγής όταν εκείνη δεν έχει ακόμα αποτέλεσμα."""
    admin_entries()
    out = []
    for d in _ADMIN.get("custom", []):
        if d.get("section") != section:
            continue
        try:
            m = match_from_json(d)
        except (KeyError, ValueError) as e:
            print(f"  ! αγώνας φόρμας {d.get('uid')}: {e}", file=sys.stderr)
            continue
        m.score = d.get("score", "")
        same = [o for o in official if "-custom-" not in o.uid and abs((o.day - m.day).days) <= 1 and o.paok_home == m.paok_home]
        if same:
            for o in same:
                if m.score and not o.score and o.day == m.day:
                    o.score = m.score
            continue
        out.append(m)
    return out


def apply_live_finals(section: str, matches: list[Match]) -> None:
    """Το τελικό που έστειλε το live.py, για αγώνες χωρίς ακόμα σκορ από την επίσημη πηγή: έτσι το
    πρόγραμμα και οι εικόνες αποτελεσμάτων το έχουν λίγα λεπτά μετά τη λήξη."""
    admin_entries()
    live = _ADMIN.get("live", {})
    for m in matches:
        e = live.get(match_topic_id(m.uid))
        if not e or m.status:
            continue
        final = f"{int(e['home'])}-{int(e['away'])}"
        if not m.score:
            m.score = final
        if e.get("periods") and m.score == final and not m.periods:
            m.periods = [[int(a), int(b)] for a, b in e["periods"]]


def carry_scores(section: str, previous: list[dict], current: list[Match], now: dt.datetime) -> None:
    """Ένα τελικό σκορ δεν χάνεται αν η πηγή πάψει να το δείχνει (π.χ. η σελίδα του βόλεϊ περνά στην
    επόμενη αγωνιστική μετά τα μεσάνυχτα): κρατιέται από την προηγούμενη ενημέρωση."""
    shortest = dt.timedelta(minutes=MIN_DURATION.get(section, 60))
    before = {p["uid"]: p for p in previous}
    for m in current:
        p = before.get(m.uid)
        if p and p.get("score") and not m.score and not m.status and m.start() <= now - shortest:
            print(f"  σκορ από την προηγούμενη ενημέρωση: {m.home} – {m.away} {p['score']}")
            m.score = p["score"]
            m.note = m.note or p.get("note", "")


def keep_stats(previous: list[dict], current: list[Match]) -> None:
    """Τα στατιστικά μένουν στη σελίδα αγώνα και μετά το τέλος: όταν το live σβήσει (σκορ από την επίσημη
    σελίδα ή τον διαχειριστή), κρατάμε από πού έρχονταν, από αυτή ή την προηγούμενη ενημέρωση."""
    before = {p["uid"]: p for p in previous}
    for m in current:
        if m.live or not m.score:
            m.stats = None if m.live else m.stats
            continue
        p = before.get(m.uid) or {}
        prev = p.get("stats") or p.get("live")
        if prev and (not m.stats or (prev.get("id") and not m.stats.get("id") and prev.get("src") == m.stats.get("src"))):
            m.stats = prev


def carry_periods(previous: list[dict], current: list[Match]) -> None:
    """Τα σετ/περίοδοι μένουν από την προηγούμενη ενημέρωση (το live τα δίνει μόνο μία φορά)."""
    before = {p["uid"]: p for p in previous}
    for m in current:
        p = before.get(m.uid)
        if p and p.get("periods") and not m.periods and m.score and p.get("score") == m.score:
            m.periods = p["periods"]


def apply_admin(section: str, matches: list[Match]) -> None:
    """Το τελικό σκορ του διαχειριστή έχει προτεραιότητα από κάθε αυτόματη πηγή."""
    entries = admin_entries()
    for m in matches:
        e = entries.get(match_topic_id(m.uid))
        if not e or not e.get("final"):
            continue
        m.score = f"{int(e['home'])}-{int(e['away'])}"
        m.note = str(e.get("note") or m.note)[:80]
        m.stats = m.stats or m.live
        m.live = None


def apply_info(section: str, matches: list[Match]) -> None:
    """Πληροφορίες του διαχειριστή (κανάλι, σύνδεσμος μετάδοσης, ώρα, γήπεδο), πάνω από τις πηγές."""
    admin_entries()
    info = _ADMIN.get("info", {})
    for m in matches:
        e = info.get(match_topic_id(m.uid))
        if not e:
            continue
        if e.get("tv"):
            m.tv = str(e["tv"])[:60]
        if e.get("tvUrl"):
            m.tv_url = str(e["tvUrl"])[:300]
        if e.get("venue"):
            m.venue = str(e["venue"])[:80]
        if e.get("time") and parse_time(e["time"]):
            m.time = parse_time(e["time"])


GENERIC_WORDS = {"ΑΟ", "ΑΣ", "ΓΣ", "ΠΑΕ", "ΚΑΕ", "ΤΑΑ", "ΣΦΠ", "ΝΟ", "ΟΑ", "ΑΕ", "ΑΘ", "FC", "BC", "VC", "WFC", "ΓΑΣ"}


def name_words(name: str) -> frozenset[str]:
    """Οι λέξεις ενός ονόματος ομάδας, χωρίς τόνους, τελείες και γενικές συντομογραφίες (Α.Ο., ΠΑΕ…)."""
    text = greekish(plain(re.sub(r"(?<=\b\w)\.(?=\w\.)|(?<=\b\w\.\w)\.", "", name)))
    return frozenset(w[:6] for w in re.findall(r"[A-ZΑ-Ω0-9]+", text) if w not in GENERIC_WORDS and len(w) > 1)


def fill_logos(matches: list[dict]) -> None:
    """Σήμα για ομάδες που η πηγή του αγώνα δεν το δίνει (π.χ. ΕΟΠΕ, αγώνες από το manual.json), από άλλον
    αγώνα της ίδιας ομάδας στο ίδιο άθλημα (ανδρών ή γυναικών). Μόνο αν το όνομα ταιριάζει σε ένα σήμα."""
    sport = lambda sec: sec.replace("-women", "")
    known: dict[str, list[tuple[frozenset, str]]] = {}
    for m in matches:
        for side in ("home", "away"):
            if m.get(f"{side}Logo") and not is_paok(m[side]):
                known.setdefault(sport(m["section"]), []).append((name_words(m[side]), m[f"{side}Logo"]))
    for m in matches:
        for side in ("home", "away"):
            if m.get(f"{side}Logo") or is_paok(m[side]):
                continue
            words = name_words(m[side])
            if not words:
                continue
            found = {logo for w, logo in known.get(sport(m["section"]), []) if words <= w or w <= words}
            if len(found) == 1:
                m[f"{side}Logo"] = found.pop()


def match_from_json(d: dict) -> Match:
    start = dt.datetime.fromisoformat(d["start"]).astimezone(ATHENS)
    return Match(section=d["section"], uid=d["uid"], day=start.date(), time=start.time() if d.get("timeKnown") else None,
                 home=d["home"], away=d["away"], paok_home=d["paokHome"], venue=d.get("venue", ""),
                 competition=d.get("competition", ""), round=d.get("round", ""), score=d.get("score", ""),
                 tv=d.get("tv", ""), tv_url=d.get("tvUrl", ""), url=d.get("url", ""),
                 home_logo=d.get("homeLogo", ""), away_logo=d.get("awayLogo", ""),
                 status=d.get("status", ""), note=d.get("note", ""), stats=d.get("stats"))


def keep_friendlies(previous: list[dict], current: list[Match]) -> None:
    """Οι φιλικοί αγώνες έρχονται μόνο από ανακοινώσεις, που δεν διαβάζονται μετά τη μέρα τους:
    κρατάμε τους παλιούς από τα προηγούμενα δεδομένα (με το αποτέλεσμά τους), για όλη τη σεζόν."""
    have = {m.uid for m in current}
    cutoff = dt.date(season_start_year(), 6, 1)
    for d in previous:
        if "-friendly-" in d["uid"] and d["uid"] not in have and d["start"][:10] >= cutoff.isoformat():
            current.append(match_from_json(d))


# Το ίδιο γήπεδο γράφεται αλλιώς σε κάθε πηγή: ένα όνομα για όλα.
VENUE_ALIASES = [
    (re.compile(r"(PAOK|ΠΑΟΚ)\s*(SPORTS?\s*ARENA|PALACE SPORT)|ΠΑΛΑΤΑΚΙ|Γυμναστήριο Πυλαίας", re.I), "PAOK Sports Arena"),
    (re.compile(r"^(ΤΟΥΜΠΑ|Τούμπα|Toumba( Stadium)?)$", re.I), "Τούμπα"),
    (re.compile(r"^ΑΛΕΞΑΝΔΡΕΙΟ", re.I), "Αλεξάνδρειο"),
]
CLOSED_RE = re.compile(r"ΚΕΚΛΕΙΣΜΕΝΩΝ ΤΩΝ ΘΥΡΩΝ|κεκλεισμένων των θυρών", re.I)


def normalize_venue(venue: str) -> str:
    v = (venue or "").strip()
    closed = bool(CLOSED_RE.search(v))
    for rx, name in VENUE_ALIASES:
        if rx.search(v):
            v = name
            break
    return v + (" (κεκλεισμένων των θυρών)" if closed and "κεκλεισμένων" not in v else "")


def drop_shadow_friendlies(matches: list[Match]) -> list[Match]:
    """Μια ανακοίνωση της ΑΣ ΠΑΟΚ μπορεί να μοιάζει με φιλικό («προετοιμασία», «τουρνουά») ενώ είναι
    ο επίσημος αγώνας της μέρας. Ένα τμήμα δεν παίζει φιλικό την ίδια μέρα με επίσημο αγώνα: τότε
    το «φιλικό» είναι διπλό και φεύγει."""
    official_days = {m.day for m in matches if "-friendly-" not in m.uid}
    out = []
    for m in matches:
        if "-friendly-" in m.uid and m.day in official_days:
            print(f"  διπλό φιλικό (ίδια μέρα με επίσημο): {m.home} – {m.away} {m.day}")
            continue
        out.append(m)
    return out


def carry_uids(previous: list[dict], current: list[Match]) -> None:
    """Όταν η επίσημη πηγή δημοσιεύσει έναν αγώνα που είχε μπει χειροκίνητα ή από την ΑΣ ΠΑΟΚ,
    ο αγώνας κρατά το παλιό αναγνωριστικό: ίδιος σύνδεσμος, ίδιες ειδοποιήσεις, ίδια εγγραφή
    στο ημερολόγιο, και καμία διπλή ειδοποίηση «νέος αγώνας»."""
    temp = ("-manual-", "-acpaok-")
    now = {m.uid for m in current}
    before = {p["uid"] for p in previous}
    orphans = [p for p in previous if any(t in p["uid"] for t in temp) and p["uid"] not in now]
    for m in current:
        if m.uid in before or any(t in m.uid for t in temp):
            continue
        for p in orphans:
            if abs((dt.date.fromisoformat(p["start"][:10]) - m.day).days) <= 1 and p["paokHome"] == m.paok_home:
                m.uid = p["uid"]
                orphans.remove(p)
                break


# ---------------------------------------------------------------- κύριο

SOURCES: dict[str, list[tuple[str, Callable[[], list[Match]]]]] = {
    "football": [("ESPN", football_matches),
                 ("ΕΠΟ Κύπελλο", lambda: epo_matches(5, "football", required=False))],
    "football-women": [("ΕΠΟ Α' Εθνική", lambda: epo_matches(6, "football-women", required=True)),
                       ("ΕΠΟ Κύπελλο", lambda: epo_matches(38, "football-women", required=False)),
                       ("UEFA (ESPN)", football_women_europe)],
    "basketball": [("Basket League", basket_league_matches), ("EuroCup", eurocup_matches)],
    "basketball-women": [("WBL1", wbl1_matches)],
    "volley": [("Volley League", volley_matches),
               ("ΕΟΠΕ", lambda: dataproject_matches("volley")),
               ("CEV", lambda: cev_matches("volley"))],
    "volley-women": [("ΕΟΠΕ", lambda: dataproject_matches("volley-women")),
                     ("CEV", lambda: cev_matches("volley-women"))],
    "handball": [("ΟΧΕ", lambda: handball_matches("handball")),
                 ("EHF", lambda: ehf_matches("handball"))],
    "handball-women": [("ΟΧΕ", lambda: handball_matches("handball-women")),
                       ("EHF", lambda: ehf_matches("handball-women"))],
    "waterpolo": [("WPL", lambda: waterpolo_matches("waterpolo")),
                  ("European Aquatics", lambda: european_waterpolo_matches("waterpolo"))],
    "futsal": [("Futsal Super League", futsal_matches)],
    "waterpolo-women": [("WPL", lambda: waterpolo_matches("waterpolo-women")),
                        ("European Aquatics", lambda: european_waterpolo_matches("waterpolo-women"))],
    **{key: [("paokfc.gr", lambda key=key: paokfc_matches(key))] for key in PAOKFC_TEAMS},
    # ΠΑΟΚ Β και Κ16 από το επίσημο site της Super League 2 (το paokfc.gr μπλοκάρει, και δεν έχει την Κ16).
    "football-b": [("sl2.gr", lambda: sl2_matches("football-b"))],
    "football-u16": [("sl2.gr", lambda: sl2_matches("football-u16"))],
    **{key: [("epesth.gr", lambda key=key: epesth_matches(key))] for key in EPESTH_TEAMS},
    **{key: [("ekasth.gr", lambda key=key: ekasth_matches(key))] for key in EKASTH_TEAMS},
    **{key: [("ekasth.gr", lambda key=key: ekasth_matches(key)),
             ("risingstars.basket.gr", lambda key=key: rising_stars_matches(key))] for key in RISING_STARS},
    **{key: [("epsm.gr", lambda key=key: epsm_matches(key))] for key in EPSM_TEAMS},
    "football-women-u17": [("ΕΠΟ Υποδομών Κ17", lambda: strip_age(epo_matches(56, "football-women-u17", required=True), "Κ17"))],
    # ΑμεΑ: μόνο οι αγώνες της φόρμας και του manual.json.
    **{key: [] for key in AMEA},
}


def main(only: list[str] | None = None) -> int:
    OUT_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    status_path = OUT_DIR / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    data_path = OUT_DIR / "matches.json"
    previous = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else {}
    prev_by_section = collections.defaultdict(list)
    for m in previous.get("matches", []):
        prev_by_section[m["section"]].append(m)

    failures: list[str] = []
    checks: list[str] = []  # διαφορές με την ΑΣ ΠΑΟΚ, για το issue «Αγώνες προς έλεγχο»
    all_matches: list[dict] = []
    updated: dict[str, str] = dict(previous.get("updated", {}))
    refreshed: set[str] = set()

    for key, getters in SOURCES.items():
        if only and key not in only:
            all_matches += prev_by_section[key]
            continue
        matches: list[Match] = []
        ok = True
        for label, get in getters:
            try:
                found = get()
                print(f"{key} / {label}: {len(found)} αγώνες")
                matches += found
            except Exception as e:
                ok = False
                # Β' ομάδα και ακαδημίες: η πηγή (paokfc.gr) μπλοκάρει κατά διαστήματα τα αυτόματα αιτήματα
                # (Cloudflare). Μένουν τα προηγούμενα δεδομένα, χωρίς να «κοκκινίζει» όλη η ενημέρωση.
                if key not in ACADEMY:
                    failures.append(f"{key} / {label}: {e}")
                print(f"! {key} / {label}: {e}", file=sys.stderr)
        if not ok and key in ACADEMY:
            # Ακαδημίες: όταν το paokfc.gr δεν απαντά, κρατάμε τους προηγούμενους αγώνες αλλά
            # περνάμε κανονικά τις χειροκίνητες καταχωρίσεις (manual.json) και του διαχειριστή.
            print(f"  {key}: οι προηγούμενοι αγώνες, μαζί με τις χειροκίνητες καταχωρίσεις.", file=sys.stderr)
            matches = [match_from_json(p) for p in prev_by_section[key]
                       if "-manual-" not in p["uid"] and "-custom-" not in p["uid"]]
            ok = True
        if not ok:
            print(f"  Τα αρχεία για {key} μένουν ως είχαν.", file=sys.stderr)
            all_matches += prev_by_section[key]
            continue
        unique = list({m.uid: m for m in matches}.values())
        unique += manual_matches(key, unique)
        unique += custom_matches(key, unique)
        try:
            import club  # δεύτερη πηγή: ανακοινώσεις της ΑΣ ΠΑΟΚ
            unique += club.reconcile(key, unique, checks, SECTIONS[key]["name"])
        except Exception as e:
            print(f"  ! ΑΣ ΠΑΟΚ / {key}: {e}", file=sys.stderr)
        carry_uids(prev_by_section[key], unique)
        carry_scores(key, prev_by_section[key], unique, dt.datetime.now(ATHENS))
        carry_periods(prev_by_section[key], unique)
        keep_stats(prev_by_section[key], unique)  # πριν από το live, ώστε ο κωδικός Genius να μη ζητείται ξανά
        keep_friendlies(prev_by_section[key], unique)
        if key in _RS_FAILED:
            keep_source_matches(prev_by_section[key], unique, "rs")
        unique[:] = drop_shadow_friendlies(unique)
        for m in unique:
            m.venue = normalize_venue(m.venue)
        drop_live_scores(key, unique, dt.datetime.now(ATHENS))
        if key in ("volley", "volley-women"):
            volley_live(key, unique)
        if key == "basketball":
            basket_league_live(unique)
        other_live(key, unique)
        live_results(key, unique)
        try:
            import club  # αποτέλεσμα από την ΑΣ ΠΑΟΚ, όπου η επίσημη πηγή αργεί
            club.results(key, unique)
            club.tv(key, unique)
        except Exception as e:
            print(f"  ! ΑΣ ΠΑΟΚ, αποτελέσματα / {key}: {e}", file=sys.stderr)
        try:
            import tvguide  # κανάλι από τα προγράμματα αθλητικών μεταδόσεων, όπου λείπει
            tvguide.tv(key, unique, academy=key in ACADEMY)
        except Exception as e:
            print(f"  ! τηλεοπτικά / {key}: {e}", file=sys.stderr)
        # Ό,τι έγραψε ο διαχειριστής μετρά τελευταίο, πάνω από όλα.
        apply_live_finals(key, unique)
        apply_admin(key, unique)
        apply_info(key, unique)
        keep_stats(prev_by_section[key], unique)
        info = SECTIONS[key]
        for side, label, keep in (("home", "Εντός έδρας", True), ("away", "Εκτός έδρας", False)):
            subset = [m for m in unique if m.paok_home == keep]
            name = f"{info['name'] if info['name'].startswith(PAOK) else PAOK + ' ' + info['name']} – {label}"
            changed = write_if_changed(OUT_DIR / f"{key}-{side}.ics", build_ics(name, subset, stamp))
            print(f"  {key}-{side}.ics: {len(subset)} αγώνες{' (ενημερώθηκε)' if changed else ''}")
            status[f"{key}-{side}"] = len(subset)
        all_matches += [m.to_json() for m in unique]
        updated[key] = dt.datetime.now(ATHENS).isoformat(timespec="minutes")
        refreshed.add(key)

    import notify
    import standings

    fill_logos(all_matches)
    apply_goals(all_matches, admin=admin_goals())
    all_matches.sort(key=lambda m: (m["start"], m["uid"]))
    data = {
        "sections": [{"key": k, **v} for k, v in SECTIONS.items()],
        "matches": all_matches,
        "updated": updated,
    }

    def without_updated(text: str) -> str:
        d = json.loads(text)
        d.pop("updated", None)
        return json.dumps(d, sort_keys=True)

    # Η ώρα ενημέρωσης αλλάζει σε κάθε εκτέλεση· αποθηκεύουμε μόνο όταν αλλάξει κάτι άλλο.
    write_if_changed(data_path, json.dumps(data, ensure_ascii=False, indent=1) + "\n", ignore=without_updated)

    # Ειδοποιήσεις για νέους αγώνες, αλλαγές ώρας και αποτελέσματα.
    notify.send_changes(previous.get("matches", []), all_matches, refreshed)

    # Βαθμολογίες· αν μία αποτύχει, μένει η προηγούμενη.
    st_path = OUT_DIR / "standings.json"
    old_st = json.loads(st_path.read_text(encoding="utf-8")) if st_path.exists() else {}
    new_st = dict(old_st)
    for key, get in standings.STANDINGS.items():
        if only and key not in only:
            continue
        try:
            tables = get()
            new_st[key] = tables
            summary = ", ".join(f"{t['title']} ({len(t['rows'])} ομάδες)" for t in tables)
            print(f"{key} / βαθμολογία: {summary}")
        except Exception as e:
            if key not in ACADEMY:
                failures.append(f"{key} / βαθμολογία: {e}")
            print(f"! {key} / βαθμολογία: {e}", file=sys.stderr)
    write_if_changed(st_path, json.dumps(new_st, ensure_ascii=False, indent=1) + "\n",
                     ignore=lambda s: json.dumps(json.loads(s), sort_keys=True))

    # Μία αλλαγή την εβδομάδα κρατά το repo «ενεργό», ώστε το GitHub να μην
    # απενεργοποιήσει το προγραμματισμένο workflow στις περιόδους χωρίς αγώνες.
    iso = dt.date.today().isocalendar()
    status["checked_week"] = f"{iso[0]}-W{iso[1]:02d}"
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")

    checks_path = Path(__file__).resolve().parent / "checks.md"
    if checks:
        checks_path.write_text(
            "Διαφορές ανάμεσα στο πρόγραμμα των επίσημων πηγών και στις ανακοινώσεις της ΑΣ ΠΑΟΚ "
            "(acpaok.gr). Η λίστα ενημερώνεται σε κάθε ενημέρωση του προγράμματος και το issue "
            "κλείνει μόνο του όταν δεν μένει καμία διαφορά.\n\n" + "\n".join(checks) + "\n", encoding="utf-8")
        print("\nΈλεγχοι:\n" + "\n".join(checks))
    elif checks_path.exists():
        checks_path.unlink()

    if failures:
        print("\nΑποτυχίες:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
