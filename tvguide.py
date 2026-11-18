"""Τηλεοπτικό κανάλι από τα προγράμματα αθλητικών μεταδόσεων, για αγώνες που η πηγή τους δεν το δίνει.

Δύο πηγές, και οι δύο με όλα τα κανάλια (ΕΡΤ, Novasports, Magenta/COSMOTE, ΣΠΟΡ FM TV κ.ά.):

- agones.gr/tv: πίνακας για τις επόμενες 5 μέρες (καρτέλες day_0…day_4 με την ημερομηνία), με ώρα,
  ομάδες, διοργάνωση, κανάλι και εικονίδιο αθλήματος (ποδόσφαιρο, μπάσκετ, άλλο).
- matchmoney.com.gr: «Αθλητικές μεταδόσεις: Το τηλεοπτικό πρόγραμμα» της ημέρας
  (/athlitikes-metadosis/programma-tv-DD-MM-YYYY/), που ανεβαίνει τα μεσάνυχτα, με emoji αθλήματος
  και «Γυναικών» στη διοργάνωση όπου χρειάζεται.

Μπαίνει μόνο σε αγώνα χωρίς κανάλι (ό,τι δίνει η επίσημη πηγή μετρά πρώτο, ο διαχειριστής πάνω από όλα),
την ίδια μέρα, στο ίδιο άθλημα, ανδρών/γυναικών, με τον ίδιο αντίπαλο (ή, αν το όνομα γράφεται
αλλιώς, μοναδικός αγώνας του ΠΑΟΚ εκείνη τη μέρα στο άθλημα, με την ίδια έδρα και την ίδια ώρα).
"""
from __future__ import annotations

import datetime as dt
import html
import re
import sys
import unicodedata

from build_calendars import ATHENS, fetch, is_paok

AGONES_URL = "https://agones.gr/tv"
MATCHMONEY_URL = "https://www.matchmoney.com.gr/athlitikes-metadosis/programma-tv-{d:%d-%m-%Y}/"
WOMEN_RE = re.compile(r"γυναικ|women|\(γ\)|wbl\b|wfl\b", re.I)
_ENTRIES: dict[str, list[dict]] = {}

# Ελληνικά → λατινικά «όπως ακούγονται», για να ταιριάζει το «Manresa» με το «Μανρέσα».
_DIGRAPHS = [("ου", "u"), ("μπ", "b"), ("ντ", "d"), ("γκ", "g"), ("γγ", "g"), ("τσ", "ts"), ("τζ", "tz"),
             ("αι", "e"), ("ει", "i"), ("οι", "i"), ("υι", "i"), ("θ", "th"), ("ψ", "ps"), ("ξ", "x")]
_GREEK = str.maketrans("αβγδεζηικλμνοπρστυφχω", "avgdeziiklmnoprstifho")
_LATIN = [("ou", "u"), ("ph", "f"), ("ck", "k"), ("c", "k"), ("w", "v"), ("y", "i"), ("j", "i"), ("q", "k"),
          ("ai", "e"), ("ei", "i"), ("oi", "i"), ("tch", "ts"), ("ch", "h"), ("sh", "s"), ("ss", "s"), ("ll", "l"),
          ("tt", "t"), ("nn", "n"), ("ee", "i"), ("oo", "u")]


def sound(word: str) -> str:
    w = "".join(c for c in unicodedata.normalize("NFD", word.lower()) if not unicodedata.combining(c)).replace("ς", "σ")
    for a, b in _DIGRAPHS:
        w = w.replace(a, b)
    w = w.translate(_GREEK)
    for a, b in _LATIN:
        w = w.replace(a, b)
    return w


GENERIC = {"ao", "as", "gs", "pae", "kae", "no", "nas", "ofpf", "sfp", "gss", "ase", "asb", "gas", "aep", "aesh",
           "fc", "bc", "vc", "kk", "cd", "cb", "sk", "hb", "rk", "ano", "ne", "ae", "ps", "ok", "ao", "bk", "fk"}


def name_keys(name: str) -> set[str]:
    """Οι λέξεις του ονόματος που ξεχωρίζουν, ως ήχος (πρώτοι 4 χαρακτήρες)."""
    words = re.findall(r"\w+", re.sub(r"(?<=\w)\.(?=\w)", "", name))
    keys = {sound(w)[:4] for w in words}
    return {k for k in keys if len(k) >= 3 and k not in GENERIC and not k.startswith("pao")}


def sport_of(section: str) -> str:
    return section.replace("-women", "")


# ---------------------------------------------------------------- πηγές

def _text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse_agones(page: str) -> list[dict]:
    days = {m.group(1): dt.datetime.strptime(m.group(2), "%d/%m/%Y").date()
            for m in re.finditer(r'href="#(day_\d+)".*?class="date__date">\s*(\d{2}/\d{2}/\d{4})', page, re.S)}
    out = []
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'<div[^>]*\bid="(day_\d+)"', page)]
    for i, (pos, key) in enumerate(starts):
        day = days.get(key)
        if not day:
            continue
        pane = page[pos:starts[i + 1][0] if i + 1 < len(starts) else len(page)]
        for row in re.findall(r"<tr>(.*?)</tr>", pane, re.S):
            t = re.search(r'ii__localtime">\s*(\d{1,2}:\d{2})', row)
            teams = [_text(x) for x in re.findall(r'class="team_row">.*?<span>(.*?)</span>', row, re.S)]
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            if not t or len(teams) != 2 or len(cells) < 3:
                continue
            icon = re.search(r'class="icon icon-tv ([^"]*)"', row)
            sport = None
            if icon and "fa-futbol" in icon.group(1):
                sport = "football"
            elif icon and "basketball" in icon.group(1):
                sport = "basketball"
            out.append({"day": day, "time": t.group(1), "home": teams[0], "away": teams[1],
                        "competition": _text(cells[-2]), "channel": _text(cells[-1]), "sport": sport, "src": "agones.gr"})
    return out


EMOJI_SPORT = {"⚽": "football", "🏀": "basketball", "🏐": "volley", "🤾": "handball", "🤽": "waterpolo"}


def parse_matchmoney(page: str, day: dt.date) -> list[dict]:
    out = []
    for table in re.findall(r"<table.*?</table>", page, re.S):
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
            cells = [_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            if len(cells) != 3 or not re.fullmatch(r"\d{1,2}[:.]\d{2}", cells[0]):
                continue
            m = re.match(r"(\W*)\s*(.+?)\s+[–-]\s+(.+?)(?:\s+\((.+)\))?$", cells[1])
            if not m:
                continue
            sport = next((v for k, v in EMOJI_SPORT.items() if k in m.group(1)), None)
            out.append({"day": day, "time": cells[0].replace(".", ":"), "home": m.group(2), "away": m.group(3),
                        "competition": m.group(4) or "", "channel": cells[2], "sport": sport, "src": "matchmoney.com.gr"})
    return out


def entries(today: dt.date) -> list[dict]:
    if "all" not in _ENTRIES:
        got = []
        try:
            got += parse_agones(fetch(AGONES_URL))
        except Exception as e:
            print(f"  ! τηλεοπτικά (agones.gr): {e}", file=sys.stderr)
        for d in (today, today + dt.timedelta(days=1)):
            try:
                got += parse_matchmoney(fetch(MATCHMONEY_URL.format(d=d)), d)
            except Exception:
                pass  # η σελίδα της ημέρας ανεβαίνει τα μεσάνυχτα· της επόμενης συνήθως δεν υπάρχει ακόμα
        _ENTRIES["all"] = got
    return _ENTRIES["all"]


# ---------------------------------------------------------------- αντιστοίχιση

def fits(section: str, e: dict) -> bool:
    """Ίδιο άθλημα και ίδια κατηγορία (ανδρών/γυναικών) με το τμήμα."""
    sport, comp = sport_of(section), e["competition"]
    if bool(WOMEN_RE.search(comp)) != section.endswith("-women"):
        return False
    if sport == "futsal":
        return e["sport"] in (None, "football") and re.search(r"futsal|σάλας|σαλας", comp, re.I) is not None
    if e["sport"] == "football" and re.search(r"futsal|σάλας|σαλας", comp, re.I):
        return False
    if e["sport"]:
        return e["sport"] == sport
    return sport not in ("football", "basketball")  # agones.gr: ποδόσφαιρο και μπάσκετ έχουν δικό τους εικονίδιο


def minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def tv(section: str, matches: list, now: dt.datetime | None = None, academy: bool = False) -> None:
    if academy:
        return
    now = now or dt.datetime.now(ATHENS)
    soon = [m for m in matches if not m.score and not m.tv and not m.status and 0 <= (m.day - now.date()).days <= 5]
    if not soon:
        return
    pool = [e for e in entries(now.date()) if fits(section, e) and (is_paok(e["home"]) or is_paok(e["away"]))]
    for m in soon:
        opp_keys = name_keys(m.away if m.paok_home else m.home)
        cands = [e for e in pool if e["day"] == m.day]
        if m.time:
            cands = [e for e in cands if abs(minutes(e["time"]) - (m.time.hour * 60 + m.time.minute)) <= 180]
        # Ο αντίπαλος (σε όποια σειρά κι αν γράφει τις ομάδες η πηγή).
        named = [e for e in cands if opp_keys & (name_keys(e["home"]) | name_keys(e["away"]))]
        if not named:
            # Όνομα γραμμένο αλλιώς (π.χ. «Τσεντεβίτα» / «Cedevita»): μόνο αν είναι ο μοναδικός αγώνας
            # του ΠΑΟΚ εκείνη τη μέρα στο άθλημα, με την ίδια έδρα και, αν ξέρουμε την ώρα, στην ίδια ώρα.
            named = [e for e in cands if is_paok(e["home"]) == m.paok_home
                     and m.time and minutes(e["time"]) == m.time.hour * 60 + m.time.minute]
            if len({(e["home"], e["away"]) for e in named}) != 1:
                continue
        channels = list(dict.fromkeys(e["channel"] for e in named if e["channel"]))
        if channels:
            m.tv = channels[0]
            print(f"  κανάλι από {named[0]['src']}: {m.home} – {m.away} → {m.tv}")
