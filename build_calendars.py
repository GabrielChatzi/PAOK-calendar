#!/usr/bin/env python3
"""Φτιάχνει ημερολόγια iCal (.ics) με τους αγώνες του ΠΑΟΚ σε βόλεϊ, ποδόσφαιρο και μπάσκετ.

Για κάθε άθλημα γράφει δύο αρχεία στο docs/: εντός και εκτός έδρας.
Όπου η ώρα ενός αγώνα δεν έχει οριστεί ακόμα, ο αγώνας μπαίνει στις 18:00 (ώρα Ελλάδας)
με την ένδειξη «(ώρα TBC)».

Πηγές:
  Βόλεϊ:       volleyleague.gr (Volley League, League Cup)
  Ποδόσφαιρο:  ESPN (Super League, ευρωπαϊκές διοργανώσεις)
  Μπάσκετ:     esake.gr (Basket League) και Euroleague API (EuroCup)

Αν μια πηγή αποτύχει, τα αρχεία του αθλήματος μένουν όπως ήταν και το script
τερματίζει με σφάλμα, ώστε να φανεί στο GitHub Actions.
Χρησιμοποιεί μόνο τη βασική βιβλιοθήκη της Python.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

ATHENS = ZoneInfo("Europe/Athens")
DEFAULT_TIME = dt.time(18, 0)
GAME_LENGTH = dt.timedelta(hours=2)
OUT_DIR = Path(__file__).resolve().parent / "docs"
PAOK = "ΠΑΟΚ"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130 Safari/537.36")

SPORTS = {
    "volley": {"emoji": "🏐", "name": "Βόλεϊ"},
    "football": {"emoji": "⚽", "name": "Ποδόσφαιρο"},
    "basketball": {"emoji": "🏀", "name": "Μπάσκετ"},
}


@dataclass
class Match:
    sport: str
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


# ---------------------------------------------------------------- βοηθητικά

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "el,en"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def season_start_year(today: dt.date | None = None) -> int:
    today = today or dt.date.today()
    return today.year if today.month >= 7 else today.year - 1


def clean(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


# Μερικά site γράφουν ελληνικά ονόματα με λατινικά γράμματα που μοιάζουν (π.χ. «ΠAΟΚ»).
_LOOKALIKE = str.maketrans("ABEZHIKMNOPTYX", "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ")


def greekish(text: str) -> str:
    return text.upper().translate(_LOOKALIKE)


def is_paok(name: str) -> bool:
    n = greekish(re.sub(r"[.\s]", "", name))
    return n.startswith("ΠΑΟΚ")


def short_hash(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


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
        day = dt.datetime.strptime(date_s, "%d/%m/%Y").date()
        t = None
        tm = re.fullmatch(r"(\d{1,2}):(\d{2})", time_s)
        if tm and (tm.group(1), tm.group(2)) != ("00", "00"):
            t = dt.time(int(tm.group(1)), int(tm.group(2)))
        head = heading_at(m.start())
        if "αγωνιστική" in head.lower():
            comp, rnd = "Volley League", re.sub(r"\s*-\s*Τέλος.*", "", head)
        else:
            comp, rnd = head.title() if head.isupper() else head, ""
        if score in ("0-0", "-", ""):
            score = ""
        out.append(Match(
            sport="volley",
            uid=f"volley-{season}-{short_hash(comp, rnd, home, away)}",
            day=day, time=t,
            home=PAOK if is_paok(home) else home,
            away=PAOK if is_paok(away) else away,
            paok_home=is_paok(home), venue=venue, competition=comp, round=rnd,
            score=score, url=url,
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
        home, away = name(teams["home"]), name(teams["away"])
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
        rnd = ""
        notes = comp.get("notes") or []
        if notes and notes[0].get("headline"):
            rnd = notes[0]["headline"]
        out.append(Match(
            sport="football", uid=f"football-espn-{ev_id}",
            day=local.date(),
            time=dt.time(local.hour, local.minute) if time_known else None,
            home=home, away=away, paok_home=teams["home"]["team"]["id"] == ESPN_TEAM_ID,
            venue=VENUE_NAMES.get(venue, venue),
            competition=COMPETITION_NAMES.get(league, league), round=rnd, score=score,
            url=f"https://www.espn.com/soccer/match/_/gameId/{ev_id}",
        ))
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
    key = greekish(raw).replace("Ϊ", "Ι").replace("Ά", "Α")
    key = re.sub(r"\s+", " ", key)
    for prefix, nice in BASKET_NAMES.items():
        if key.startswith(prefix):
            return nice
    return raw


def latin_title(name: str) -> str:
    """«BOSNA» → «Bosna», αλλά αφήνει όπως είναι ονόματα με πεζά (π.χ. «Ulm»)."""
    return name.title() if name.isupper() and re.search(r"[A-Z]{4}", name) else name
GREEK_MONTHS = {
    "ιανουάριος": 1, "φεβρουάριος": 2, "μάρτιος": 3, "απρίλιος": 4, "μάιος": 5,
    "ιούνιος": 6, "ιούλιος": 7, "αύγουστος": 8, "σεπτέμβριος": 9, "οκτώβριος": 10,
    "νοέμβριος": 11, "δεκέμβριος": 12,
}


def basket_league_matches() -> list[Match]:
    url = f"https://www.esake.gr/el/action/EsaketeamView?idteam={ESAKE_TEAM_ID}&mode=3"
    page = fetch(url)
    out = []
    # Οι αγώνες είναι ομαδοποιημένοι ανά μήνα: «Οκτώβριος <span>2026</span>».
    for section in page.split('<div class="esake-program-series-title">')[1:]:
        hm = re.match(r"\s*([^<]+?)\s*<span>(\d{4})</span>", section)
        if not hm or hm.group(1).strip().lower() not in GREEK_MONTHS:
            continue
        month, year = GREEK_MONTHS[hm.group(1).strip().lower()], int(hm.group(2))
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
            day = dt.date(year, month, int(day_m.group(1)))
            tm = re.search(r"(\d{1,2}):(\d{2})", info[0])
            t = dt.time(int(tm.group(1)), int(tm.group(2))) if tm else None
            if t == dt.time(0, 0):
                t = None
            score = "" if not re.search(r"\d", score) else re.sub(r"\s+", "", score)
            rnd = clean(rnd_m.group(1)) if rnd_m else ""
            rnd = re.sub(r"^0(\d)", r"\1", rnd)
            out.append(Match(
                sport="basketball",
                uid=f"basketball-esake-{gid.group(1) if gid else short_hash(str(day), home, away)}",
                day=day, time=t,
                home=basket_name(home),
                away=basket_name(away),
                paok_home=is_paok(home),
                venue=info[1] if len(info) > 1 else "",
                competition="Basket League", round=rnd, score=score,
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
        names = (local.get("name", ""), road.get("name", ""))
        paok_home = "PAOK" in names[0].upper()
        if not paok_home and "PAOK" not in names[1].upper():
            continue
        start_utc = dt.datetime.fromisoformat(g["utcDate"].replace("Z", "+00:00"))
        when = start_utc.astimezone(ATHENS)
        time_known = g.get("confirmedHour", True)
        score = ""
        if g.get("played"):
            score = f'{g["local"].get("score", "")}-{g["road"].get("score", "")}'
        phase = (g.get("phaseType") or {}).get("name", "")
        rnd = g.get("roundName") or ""
        if phase and phase != "Regular Season":
            rnd = f"{phase} – {rnd}" if rnd else phase
        nice = lambda c: PAOK if "PAOK" in c.get("name", "").upper() else latin_title(
            c.get("editorialName") or c.get("name", ""))
        out.append(Match(
            sport="basketball", uid=f"basketball-eurocup-{g.get('identifier') or g['id']}",
            day=when.date(), time=dt.time(when.hour, when.minute) if time_known else None,
            home=nice(local), away=nice(road), paok_home=paok_home,
            venue=((g.get("venue") or {}).get("name") or "").title(),
            competition="EuroCup", round=rnd, score=score,
            url="https://www.eurocupbasketball.com/",
        ))
    if not out:
        raise RuntimeError(f"Δεν βρέθηκαν αγώνες ΠΑΟΚ στο EuroCup {season}")
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
    for m in sorted(matches, key=lambda m: m.start()):
        emoji = SPORTS[m.sport]["emoji"]
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


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and without_stamp(path.read_text(encoding="utf-8")) == without_stamp(content):
        return False
    path.write_text(content, encoding="utf-8", newline="")
    return True


# ---------------------------------------------------------------- κύριο

SOURCES = {
    "volley": [volley_matches],
    "football": [football_matches],
    "basketball": [basket_league_matches, eurocup_matches],
}


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    status_path = OUT_DIR / "status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    failures = []

    for sport, getters in SOURCES.items():
        matches: list[Match] = []
        ok = True
        for get in getters:
            try:
                found = get()
                print(f"{sport}/{get.__name__}: {len(found)} αγώνες")
                matches += found
            except Exception as e:
                ok = False
                failures.append(f"{sport}/{get.__name__}: {e}")
                print(f"! {sport}/{get.__name__}: {e}", file=sys.stderr)
        if not ok:
            print(f"  Τα αρχεία για {sport} μένουν ως είχαν.", file=sys.stderr)
            continue
        seen, unique = set(), []
        for m in matches:
            if m.uid not in seen:
                seen.add(m.uid)
                unique.append(m)
        info = SPORTS[sport]
        for side, label, keep in (("home", "Εντός έδρας", True), ("away", "Εκτός έδρας", False)):
            subset = [m for m in unique if m.paok_home == keep]
            name = f"ΠΑΟΚ {info['name']} – {label}"
            changed = write_if_changed(OUT_DIR / f"{sport}-{side}.ics",
                                       build_ics(name, subset, stamp))
            print(f"  {sport}-{side}.ics: {len(subset)} αγώνες{' (ενημερώθηκε)' if changed else ''}")
            status[f"{sport}-{side}"] = len(subset)

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
    sys.exit(main())
