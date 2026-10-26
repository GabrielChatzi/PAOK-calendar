#!/usr/bin/env python3
"""Φτιάχνει ημερολόγια iCal (.ics) και δεδομένα ιστοσελίδας με τους αγώνες των τμημάτων του ΠΑΟΚ.

Για κάθε τμήμα γράφει δύο ημερολόγια στο docs/ (εντός και εκτός έδρας) και όλους
τους αγώνες στο docs/matches.json, που διαβάζει η σελίδα docs/index.html.
Όπου η ώρα ενός αγώνα δεν έχει οριστεί ακόμα, ο αγώνας μπαίνει στις 18:00 (ώρα Ελλάδας)
με την ένδειξη «(ώρα TBC)».

Πηγές:
  Ποδόσφαιρο:          ESPN (Super League, Ευρώπη), ΕΠΟ (Κύπελλο Ελλάδας)
  Ποδόσφαιρο γυναικών: ΕΠΟ (Α' Εθνική, Κύπελλο)
  Μπάσκετ:             esake.gr (Basket League), Euroleague API (EuroCup)
  Μπάσκετ γυναικών:    basket.gr (Women's Basketball League 1)
  Βόλεϊ:               volleyleague.gr (Volley League, League Cup), Data Project της ΕΟΠΕ (Κύπελλο)
  Βόλεϊ γυναικών:      Data Project της ΕΟΠΕ (Volley League Women, Κύπελλο)
  Χάντμπολ:            statistics.handball.org.gr (Handball Premier, Α1 Γυναικών, Κύπελλα)
  Πόλο:                waterpololeague.gr (ανδρών, γυναικών)

Αν μια πηγή αποτύχει, τα αρχεία του τμήματος μένουν όπως ήταν και το script
τερματίζει με σφάλμα, ώστε να φανεί στο GitHub Actions.
Χρησιμοποιεί μόνο τη βασική βιβλιοθήκη της Python.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import html
import json
import re
import sys
import unicodedata
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
    "football": {"emoji": "⚽", "name": "Ποδόσφαιρο", "sport": "Ποδόσφαιρο", "women": False},
    "football-women": {"emoji": "⚽", "name": "Ποδόσφαιρο Γυναικών", "sport": "Ποδόσφαιρο", "women": True},
    "basketball": {"emoji": "🏀", "name": "Μπάσκετ", "sport": "Μπάσκετ", "women": False},
    "basketball-women": {"emoji": "🏀", "name": "Μπάσκετ Γυναικών", "sport": "Μπάσκετ", "women": True},
    "volley": {"emoji": "🏐", "name": "Βόλεϊ", "sport": "Βόλεϊ", "women": False},
    "volley-women": {"emoji": "🏐", "name": "Βόλεϊ Γυναικών", "sport": "Βόλεϊ", "women": True},
    "handball": {"emoji": "🤾", "name": "Χάντμπολ", "sport": "Χάντμπολ", "women": False},
    "handball-women": {"emoji": "🤾", "name": "Χάντμπολ Γυναικών", "sport": "Χάντμπολ", "women": True},
    "waterpolo": {"emoji": "🤽", "name": "Πόλο", "sport": "Πόλο", "women": False},
    "waterpolo-women": {"emoji": "🤽", "name": "Πόλο Γυναικών", "sport": "Πόλο", "women": True},
}


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
    url: str = ""

    def start(self) -> dt.datetime:
        return dt.datetime.combine(self.day, self.time or DEFAULT_TIME, ATHENS)

    def to_json(self) -> dict:
        d = asdict(self)
        d["start"] = self.start().isoformat()
        d["timeKnown"] = self.time is not None
        d["paokHome"] = d.pop("paok_home")
        del d["day"], d["time"]
        return d


# ---------------------------------------------------------------- βοηθητικά

def fetch(url: str, data: list[tuple[str, str]] | None = None, encoding: str = "utf-8") -> str:
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": UA, "Accept-Language": "el,en"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode(encoding, errors="replace")


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
    return n.startswith("PAOK") or greekish(n).startswith("ΠΑΟΚ")


def tidy_name(name: str) -> str:
    """Αφαιρεί νομικά προθέματα (ΠΑΕ, ΚΑΕ…) και ενοποιεί το όνομα του ΠΑΟΚ."""
    name = re.sub(r"^(?:Π\.?\s?Α\.?\s?Ε\.?|Κ\.?\s?Α\.?\s?Ε\.?)\s+", "", name.strip())
    return PAOK if is_paok(name) else name


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

def volley_matches() -> list[Match]:
    y = season_start_year()
    season = f"{y}-{str(y + 1)[-2:]}"
    url = f"https://www.volleyleague.gr/index.php/season/{season}/regular-season-results-statistics"
    page = fetch(url)

    # Κάθε αγωνιστική ξεκινά με <h3>…</h3>· κάθε αγώνας είναι μια γραμμή με
    # ημερομηνία, ώρα, γήπεδο, γηπεδούχο, σκορ, φιλοξενούμενο.
    row = re.compile(
        r'>(\d{2}/\d{2}/\d{4})</div>\s*'
        r'<div[^>]*>([^<]*)</div>\s*'
        r'<div[^>]*>([^<]*)</div>\s*'
        r'<div[^>]*>\s*<a[^>]*>([^<]*)</a>.*?'
        r'<span class="team-class">([^<]*)</span>.*?'
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

    out = []
    for m in row.finditer(page):
        date_s, time_s, venue, home, score, away = (clean(g) for g in m.groups())
        if not (is_paok(home) or is_paok(away)):
            continue
        head = heading_at(m.start())
        if "αγωνιστική" in head.lower():
            comp, rnd = "Volley League", re.sub(r"\s*-\s*Τέλος.*", "", head)
        else:
            comp, rnd = head.title() if head.isupper() else head, ""
        out.append(Match(
            section="volley",
            uid=f"volley-{season}-{short_hash(comp, rnd, home, away)}",
            day=dt.datetime.strptime(date_s, "%d/%m/%Y").date(), time=parse_time(time_s),
            home=tidy_name(home), away=tidy_name(away),
            paok_home=is_paok(home), venue=venue, competition=comp, round=rnd,
            score="" if score in ("0-0", "-", "") else parse_score(score), url=url,
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


def _parse_dataproject(page: str, section: str, cid: str, comp: str) -> list[Match]:
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
        fields[key][field] = (value.group(1) if value else m.group(3)).strip()

    ids = [(m.start(), m.group(1)) for m in re.finditer(r"MatchStatistics\.aspx\?mID=(\d+)", page)]
    out = []
    for key, f in fields.items():
        home = f.get("Label2") or f.get("Label6") or ""
        away = f.get("Label4") or f.get("Label7") or ""
        if not (is_paok(home) or is_paok(away)):
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
            home=tidy_name(home), away=tidy_name(away), paok_home=is_paok(home),
            venue=f.get("LB_Palasport", ""), competition=comp,
            round=f"{rnd_m.group(1)}η Αγωνιστική" if rnd_m else leg.title(),
            score=score,
            url=(f"{DATAPROJECT}MatchStatistics.aspx?mID={mid}&ID={cid}" if mid
                 else f"{DATAPROJECT}CompetitionMatches.aspx?ID={cid}"),
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
}
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
    base = "https://site.api.espn.com/apis/site/v2/sports/soccer"
    events: dict[str, tuple[str, dict]] = {}
    for league in ESPN_LEAGUES:
        for suffix in ("?fixture=true", ""):
            try:
                data = json.loads(fetch(f"{base}/{league}/teams/{ESPN_TEAM_ID}/schedule{suffix}"))
            except Exception as e:  # ένα λάθος σε μία διοργάνωση δεν ακυρώνει τις άλλες
                print(f"  ! ESPN {league}{suffix}: {e}", file=sys.stderr)
                continue
            for ev in data.get("events", []):
                slug = (ev.get("league") or {}).get("slug") or league
                events.setdefault(ev["id"], (slug, ev))
    if not any(lg == "gre.1" for lg, _ in events.values()):
        raise RuntimeError("Δεν βρέθηκαν αγώνες Super League στο ESPN")

    out = []
    for ev_id, (league, ev) in events.items():
        comp = ev["competitions"][0]
        teams = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in teams or "away" not in teams:
            continue
        name = lambda c: FOOTBALL_NAMES.get(c["team"]["displayName"], c["team"]["displayName"])
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
        venue = (comp.get("venue") or {}).get("fullName", "")
        notes = comp.get("notes") or []
        out.append(Match(
            section="football", uid=f"football-espn-{ev_id}",
            day=local.date(),
            time=dt.time(local.hour, local.minute) if time_known else None,
            home=name(teams["home"]), away=name(teams["away"]),
            paok_home=teams["home"]["team"]["id"] == ESPN_TEAM_ID,
            venue=VENUE_NAMES.get(venue, venue),
            competition=COMPETITION_NAMES.get(league, league),
            round=notes[0].get("headline", "") if notes else "", score=score,
            url=f"https://www.espn.com/soccer/match/_/gameId/{ev_id}",
        ))
    return out


EPO = "https://www.epo.gr"


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
        ))
    if not out:
        raise RuntimeError(f"Δεν βρέθηκαν αγώνες ΠΑΟΚ στο EuroCup {season}")
    return out


def wbl1_matches() -> list[Match]:
    url = "https://www.basket.gr/wbl1/schedule/"
    page = fetch(url)
    out = []
    for block in page.split('<div class="page-schedule" ')[1:]:
        rnd = re.search(r'data-round="([^"]*)"', block)
        info = re.search(r'<div class="info">(.*?)</div>', block, re.S)
        clubs = [clean(c) for c in re.findall(r'<div class="club">(.*?)</div>', block, re.S)]
        points = [clean(p) for p in re.findall(r'<div class="points">(.*?)</div>', block, re.S)]
        if len(clubs) < 2 or not info or not (is_paok(clubs[0]) or is_paok(clubs[1])):
            continue
        text = clean(info.group(1))
        dm = re.search(r"(\d{1,2})\s+(\S+)\s+(\d{4})", text)
        month = greek_month(dm.group(2)) if dm else None
        if not month:
            continue
        when, _, venue = text.partition("|")
        score = f"{points[0]}-{points[1]}" if len(points) >= 2 and all(p.isdigit() for p in points[:2]) else ""
        round_name = html.unescape(rnd.group(1)) if rnd else ""
        out.append(Match(
            section="basketball-women",
            uid=f"basketball-women-wbl1-{short_hash(round_name, clubs[0], clubs[1])}",
            day=dt.date(int(dm.group(3)), month, int(dm.group(1))),
            time=parse_time(when.split(",", 1)[-1] if "," in when else ""),
            home=tidy_name(clubs[0]), away=tidy_name(clubs[1]), paok_home=is_paok(clubs[0]),
            venue=re.sub(r"^\s*Γήπεδο:\s*", "", venue).strip(),
            competition="Women's Basketball League 1", round=round_name, score=score, url=url,
        ))
    if not out:
        raise RuntimeError("Δεν βρέθηκαν αγώνες ΠΑΟΚ στο basket.gr/wbl1")
    return out


# ---------------------------------------------------------------- χάντμπολ

HANDBALL = "http://statistics.handball.org.gr/gr/"


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
    return out


# ---------------------------------------------------------------- πόλο

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
        info = re.search(r"<!-- Quick Info -->(.*)", block, re.S)
        info_divs = [clean(d) for d in re.findall(r"<div[^>]*>([^<]*)</div>", info.group(1))] if info else []
        date_text = next((d for d in info_divs if re.search(r"\d{4}", d)), "")
        dm = re.search(r"(\d{1,2})\s+(\S+)\s+(\d{4})", date_text)
        month = greek_month(dm.group(2)) if dm else None
        if not month:
            continue
        time_text = next((d for d in info_divs if re.fullmatch(r"\d{1,2}:\d{2}", d)), "")
        score = re.search(r'sm:block">\s*<div[^>]*>(.*?)</div>', block, re.S)
        out.append(Match(
            section=section, uid=f"{section}-{link.rsplit('/', 1)[-1]}",
            day=dt.date(int(dm.group(3)), month, int(dm.group(1))), time=parse_time(time_text),
            home=tidy_name(names[0]), away=tidy_name(names[1]), paok_home=is_paok(names[0]),
            competition="Water Polo League" + (" Γυναικών" if women else ""),
            score=parse_score(clean(score.group(1))) if score else "", url=link,
        ))
    if not out:
        raise RuntimeError(f"Δεν βρέθηκαν αγώνες ΠΑΟΚ στο {url}")
    return out


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
        if m.time is None:
            summary += " (ώρα TBC)"
        desc = [x for x in (m.competition, m.round) if x]
        desc = [" – ".join(desc)] if desc else []
        if m.score:
            desc.append(f"Τελικό σκορ: {m.home} {m.score} {m.away}")
        if m.tv:
            desc.append(f"TV: {m.tv}")
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


# ---------------------------------------------------------------- κύριο

SOURCES: dict[str, list[tuple[str, Callable[[], list[Match]]]]] = {
    "football": [("ESPN", football_matches),
                 ("ΕΠΟ Κύπελλο", lambda: epo_matches(5, "football", required=False))],
    "football-women": [("ΕΠΟ Α' Εθνική", lambda: epo_matches(6, "football-women", required=True)),
                       ("ΕΠΟ Κύπελλο", lambda: epo_matches(38, "football-women", required=False))],
    "basketball": [("Basket League", basket_league_matches), ("EuroCup", eurocup_matches)],
    "basketball-women": [("WBL1", wbl1_matches)],
    "volley": [("Volley League", volley_matches),
               ("ΕΟΠΕ", lambda: dataproject_matches("volley"))],
    "volley-women": [("ΕΟΠΕ", lambda: dataproject_matches("volley-women"))],
    "handball": [("ΟΧΕ", lambda: handball_matches("handball"))],
    "handball-women": [("ΟΧΕ", lambda: handball_matches("handball-women"))],
    "waterpolo": [("WPL", lambda: waterpolo_matches("waterpolo"))],
    "waterpolo-women": [("WPL", lambda: waterpolo_matches("waterpolo-women"))],
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
    all_matches: list[dict] = []
    updated: dict[str, str] = dict(previous.get("updated", {}))

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
                failures.append(f"{key} / {label}: {e}")
                print(f"! {key} / {label}: {e}", file=sys.stderr)
        if not ok:
            print(f"  Τα αρχεία για {key} μένουν ως είχαν.", file=sys.stderr)
            all_matches += prev_by_section[key]
            continue
        unique = list({m.uid: m for m in matches}.values())
        info = SECTIONS[key]
        for side, label, keep in (("home", "Εντός έδρας", True), ("away", "Εκτός έδρας", False)):
            subset = [m for m in unique if m.paok_home == keep]
            name = f"ΠΑΟΚ {info['name']} – {label}"
            changed = write_if_changed(OUT_DIR / f"{key}-{side}.ics", build_ics(name, subset, stamp))
            print(f"  {key}-{side}.ics: {len(subset)} αγώνες{' (ενημερώθηκε)' if changed else ''}")
            status[f"{key}-{side}"] = len(subset)
        all_matches += [m.to_json() for m in unique]
        updated[key] = dt.datetime.now(ATHENS).isoformat(timespec="minutes")

    all_matches.sort(key=lambda m: (m["start"], m["uid"]))
    data = {
        "sections": [{"key": k, **v} for k, v in SECTIONS.items()],
        "matches": all_matches,
        "updated": updated,
    }
    # Η ώρα ενημέρωσης αλλάζει σε κάθε εκτέλεση· αποθηκεύουμε μόνο όταν αλλάξουν οι αγώνες.
    write_if_changed(data_path, json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                     ignore=lambda s: json.dumps(json.loads(s).get("matches")))

    # Μία αλλαγή την εβδομάδα κρατά το repo «ενεργό», ώστε το GitHub να μην
    # απενεργοποιήσει το προγραμματισμένο workflow στις περιόδους χωρίς αγώνες.
    iso = dt.date.today().isocalendar()
    status["checked_week"] = f"{iso[0]}-W{iso[1]:02d}"
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")

    if failures:
        print("\nΑποτυχίες:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
