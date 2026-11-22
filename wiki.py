"""Παλιές σεζόν του ποδοσφαίρου από τη Wikipedia («1985–86 PAOK FC season»), για το archive.py.

Οι σελίδες σεζόν της αγγλικής Wikipedia (από το 1968-69) έχουν κάθε αγώνα σε πρότυπο «football box» με
ημερομηνία, ομάδες, σκορ, γήπεδο και σκόρερ, κάτω από επικεφαλίδες ανά διοργάνωση, και στο infobox την τελική
θέση και πού έφτασε η ομάδα σε κάθε κύπελλο. Τα φιλικά μένουν έξω.

Το περιεχόμενο της Wikipedia είναι CC BY-SA: η σελίδα του αρχείου γράφει την πηγή με σύνδεσμο.
Η Wikipedia θέλει περιγραφικό User-Agent και λογικό ρυθμό: ένα αίτημα τη φορά, με επανάληψη σε 429.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=wikitext&redirects=1&page="
UA = "PAOKalendar/1.0 (https://paokalendar.gr; info@paokalendar.gr)"
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}


def page_title(year: int) -> str:
    end = f"{year + 1}" if year == 1999 else f"{(year + 1) % 100:02d}"
    return f"{year}–{end} PAOK FC season"


def page_url(year: int) -> str:
    return "https://en.wikipedia.org/wiki/" + urllib.parse.quote(page_title(year).replace(" ", "_"))


def fetch_wikitext(year: int) -> str | None:
    req = urllib.request.Request(API + urllib.parse.quote(page_title(year)), headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode())
            time.sleep(1.5)
            if "error" in d:
                return None
            return d["parse"]["wikitext"]["*"]
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            time.sleep(10 * (attempt + 1))
    return None


# ---------------------------------------------------------------- wikitext

def templates(text: str, names: re.Pattern) -> list[tuple[int, str]]:
    """Τα πρότυπα {{name …}} (με ό,τι φωλιασμένο έχουν), με τη θέση τους."""
    out = []
    for m in re.finditer(r"\{\{\s*(" + names.pattern + r")\s*[|\n]", text, re.I):
        depth, i = 0, m.start()
        while i < len(text) - 1:
            two = text[i:i + 2]
            if two == "{{":
                depth += 1
                i += 2
                continue
            if two == "}}":
                depth -= 1
                i += 2
                if depth == 0:
                    break
                continue
            i += 1
        out.append((m.start(), text[m.start() + 2:i - 2]))
    return out


def params(body: str) -> dict[str, str]:
    """Οι παράμετροι ενός προτύπου (|κλειδί = τιμή), με τα | μέσα σε {{ }} και [[ ]] να μη χωρίζουν."""
    parts, depth, cur = [], 0, ""
    i = 0
    while i < len(body):
        two = body[i:i + 2]
        if two in ("{{", "[["):
            depth += 1
            cur += two
            i += 2
            continue
        if two in ("}}", "]]"):
            depth -= 1
            cur += two
            i += 2
            continue
        if body[i] == "|" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += body[i]
        i += 1
    parts.append(cur)
    out = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out


def plain(t: str) -> str:
    """Κείμενο χωρίς σημάνσεις wiki: [[α|β]] → β, χωρίς ref, σχόλια, πρότυπα, ''' και HTML."""
    t = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>|<!--.*?-->", "", t or "", flags=re.S)
    t = re.sub(r"\{\{\s*(?:flagicon|fbaicon|flag icon)[^{}]*\}\}", "", t, flags=re.I)
    t = re.sub(r"\{\{\s*(?:colou?r)\s*\|[^|{}]*\|([^{}]*)\}\}", r"\1", t, flags=re.I)
    t = re.sub(r"\{\{\s*(?:tooltip|abbr|nowrap)\s*\|([^|{}]*)(?:\|[^{}]*)?\}\}", r"\1", t, flags=re.I)
    for _ in range(3):
        t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\s*([^\]]*)\]", r"\1", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("'''", "").replace("''", "").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", t).strip(" ,;")


def parse_date(v: str) -> dt.date | None:
    m = re.search(r"\{\{\s*(?:start date|dts|date)\s*\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", v, re.I)
    if m:
        return dt.date(int(m[1]), int(m[2]), int(m[3]))
    t = plain(v).lower()
    m = re.search(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", t) or None
    if m and m[2] in MONTHS:
        return dt.date(int(m[3]), MONTHS[m[2]], int(m[1]))
    m = re.search(r"([a-z]+)\s+(\d{1,2}),?\s+(\d{4})", t)
    if m and m[1] in MONTHS:
        return dt.date(int(m[3]), MONTHS[m[1]], int(m[2]))
    return None


def parse_goals(v: str) -> list[dict]:
    """«[[X|Χ]] {{goal|30||87|pen.}} <br> {{goal|54}}» → [{"name": "Χ", "min": "30"}, …]· χωρίς λεπτό: ένα γκολ
    για κάθε {{goal}}. Χωρίς όνομα (όπως συχνά για τον αντίπαλο): name «»."""
    out = []
    for seg in re.split(r"<br\s*/?>|\n\s*\*|\n|,\s*(?=\{\{\s*goal)", v or "", flags=re.I):
        goals = re.findall(r"\{\{\s*goal\s*((?:\|[^{}]*)?)\}\}", seg, re.I)
        if not goals:
            continue
        name = plain(re.sub(r"\{\{\s*goal[^{}]*\}\}", "", seg, flags=re.I)).strip("* ")
        for g in goals:
            bits = [b.strip() for b in g.strip("|").split("|")] if g.strip("|") else []
            if not bits:
                out.append({"name": name})
                continue
            # {{goal|30|pen.|87}}: λεπτά με προαιρετική σημείωση μετά από το καθένα
            i = 0
            while i < len(bits):
                mm = re.match(r"^(\d{1,3})(?:\+(\d{1,2}))?$", bits[i])
                if not mm:
                    i += 1
                    continue
                d = {"name": name, "min": bits[i]}
                note = bits[i + 1].lower() if i + 1 < len(bits) else ""
                if note.startswith("pen"):
                    d["pen"] = True
                elif note.startswith("o.g") or note.startswith("og"):
                    d["og"] = True
                out.append(d)
                i += 2 if note and not re.match(r"^\d", note) else 1
    return out


# Επικεφαλίδα → διοργάνωση. None: δεν μπαίνει (φιλικά, πίνακες κ.λπ.).
def competition(heading: str) -> str | None:
    h = heading.lower()
    if re.search(r"friendl|pre-season|preseason|exhibition|tournament", h):
        return None
    if "super cup" in h:
        return "Σούπερ Καπ Ελλάδας"
    if re.search(r"league cup", h):
        return "Λιγκ Καπ"
    if re.search(r"greek (football )?cup|cup of greece|^cup$|greek cup", h):
        return "Κύπελλο Ελλάδας"
    for key, name in (("conference league", "UEFA Conference League"), ("europa league", "UEFA Europa League"),
                      ("champions league", "UEFA Champions League"), ("cup winners", "Κύπελλο Κυπελλούχων"),
                      ("european cup", "Κύπελλο Πρωταθλητριών"), ("uefa cup", "Κύπελλο UEFA"), ("intertoto", "Κύπελλο Intertoto"),
                      ("fairs", "Κύπελλο Εκθέσεων"), ("balkans cup", "Βαλκανικό Κύπελλο")):
        if key in h:
            return name
    if re.search(r"play-?off", h) and re.search(r"league|ethniki|championship", h):
        return "Πρωτάθλημα (πλέι οφ)"
    if re.search(r"super league|alpha ethniki|a ethniki|first national|national division|league|championship", h):
        return "Πρωτάθλημα"
    return None


ROUND_WORDS = {"final": "Τελικός", "semi-final": "Ημιτελικός", "semi-finals": "Ημιτελικός", "quarter-final": "Προημιτελικός",
               "quarter-finals": "Προημιτελικός", "group stage": "Όμιλος", "round of 16": "Φάση των 16",
               "round of 32": "Φάση των 32", "first round": "1ος γύρος", "second round": "2ος γύρος",
               "third round": "3ος γύρος", "play-off round": "Πλέι οφ"}


def round_label(v: str) -> str:
    t = plain(v)
    if re.fullmatch(r"\d{1,2}", t):
        return f"{t}η αγωνιστική"
    low = t.lower()
    t = re.sub(r"\b1st leg\b", "1ος αγώνας", t, flags=re.I)
    t = re.sub(r"\b2nd leg\b", "2ος αγώνας", t, flags=re.I)
    t = re.sub(r"\breplay\b", "επαναληπτικός", t, flags=re.I)
    for k, g in sorted(ROUND_WORDS.items(), key=lambda x: -len(x[0])):
        if low.startswith(k):
            return g + t[len(k):]
    return t[:40]


def season_matches(text: str, year: int) -> list[dict]:
    """Οι επίσημοι αγώνες της σελίδας, σε μορφή αρχείου (όπως το matches.json, χωρίς ζωντανά πεδία)."""
    heads = [(m.start(), len(m[1]), m[2].strip()) for m in re.finditer(r"^(={2,5})\s*(.+?)\s*\1\s*$", text, re.M)]
    boxes = templates(text, re.compile(r"football ?box(?: collapsible)?|footballbox(?: collapsible)?"))
    out, seen = [], set()
    for pos, body in boxes:
        p = params(body)
        # Η διοργάνωση: η πιο κοντινή επικεφαλίδα (από το πιο βαθύ επίπεδο προς τα πάνω) που λέει κάτι.
        stack: dict[int, str] = {}
        for hp, lvl, h in heads:
            if hp > pos:
                break
            stack[lvl] = h
            for deeper in [k for k in stack if k > lvl]:
                del stack[deeper]
        comp = None
        for lvl in sorted(stack, reverse=True):
            c = competition(plain(stack[lvl]))
            if c or re.search(r"friendl|pre-season", stack[lvl], re.I):
                comp = c
                break
        rnd = plain(p.get("round", ""))
        if not comp or re.search(r"friendl|exhibition", rnd, re.I):
            continue
        day = parse_date(p.get("date", ""))
        t1, t2 = plain(p.get("team1", "")), plain(p.get("team2", ""))
        sc = re.search(r"(\d+)\s*[–\-−]\s*(\d+)", plain(p.get("score", "")))
        if not day or not t1 or not t2 or "PAOK" not in (t1 + t2).upper():
            continue
        paok_home = "PAOK" in t1.upper()
        home = "ΠΑΟΚ" if paok_home else t1
        away = t2 if paok_home else "ΠΑΟΚ"
        key = (day, home, away)
        if key in seen:
            continue
        seen.add(key)
        m = {
            "uid": "football-wiki-" + hashlib.sha1(f"{day}|{t1}|{t2}".encode()).hexdigest()[:12],
            "section": "football", "start": f"{day.isoformat()}T12:00:00+02:00", "timeKnown": False,
            "home": home, "away": away, "paokHome": paok_home, "competition": comp,
            "round": round_label(p.get("round", "")), "venue": plain(p.get("stadium", "")) or plain(p.get("location", "")),
            "score": f"{sc[1]}-{sc[2]}" if sc else "", "url": page_url(year), "source": "wikipedia",
        }
        g1, g2 = parse_goals(p.get("goals1", "")), parse_goals(p.get("goals2", ""))
        if sc and (g1 or g2):
            m["goals"] = {"home": g1, "away": g2}
        out.append(m)
    return out


RESULT_WORDS = [(r"^winners?$|^champions?$|^1st$", "Πρωταθλητής"), (r"^runners?-up$|^2nd$", "2η θέση")]
STAGE_WORDS = {"winners": "Κατάκτηση", "runners-up": "Φιναλίστ", "semi-finals": "Ημιτελικά", "quarter-finals": "Προημιτελικά",
               "round of 16": "Φάση των 16", "round of 32": "Φάση των 32", "group stage": "Όμιλοι", "first round": "1ος γύρος",
               "second round": "2ος γύρος", "third round": "3ος γύρος", "fourth round": "4ος γύρος", "fifth round": "5ος γύρος",
               "play-off round": "Πλέι οφ", "final": "Τελικός", "additional round": "Επιπλέον γύρος",
               "knockout phase play-offs": "Πλέι οφ νοκ άουτ", "league phase": "Φάση πρωταθλήματος",
               "knockout round play-offs": "Πλέι οφ νοκ άουτ"}


def greek_result(t: str, league: bool) -> str:
    t = plain(t)
    t = re.sub(r"\[\[[^\]]*\]\]", "", t).strip()
    low = t.lower()
    m = re.match(r"^(\d{1,2})(?:st|nd|rd|th) (qualifying )?round\b", low)
    if m:
        return f"{m[1]}ος {'προκριματικός ' if m[2] else ''}γύρος"
    m = re.match(r"^(first|second|third|fourth) qualifying round", low)
    if m:
        return f"{['first', 'second', 'third', 'fourth'].index(m[1]) + 1}ος προκριματικός γύρος"
    m = re.match(r"^(\d{1,2})(?:st|nd|rd|th)\b(.*)$", low)
    if m and league and m[1] == "1" and not m[2].strip():
        return "Πρωταθλητής"
    if m:
        rest = re.sub(r"\((\d{1,2})(?:st|nd|rd|th) in regular season\)", r"(\1η στην κανονική περίοδο)", t[len(m[0]) - len(m[2]):])
        rest = re.sub(r"\((\d{1,2})(?:st|nd|rd|th) at play-?offs\)", r"(\1η στα πλέι οφ)", rest, flags=re.I)
        return f"{m[1]}η θέση{rest}".strip()
    if league and low in ("winners", "champions"):
        return "Πρωταθλητής"
    if league and low == "runners-up":
        return "2η θέση"
    for k, g in sorted(STAGE_WORDS.items(), key=lambda x: -len(x[0])):
        if low.startswith(k):
            return g + t[len(k):]
    return t[:60]


def season_summary(text: str) -> dict:
    """Από το infobox: τελική θέση και πού έφτασε η ομάδα σε κάθε κύπελλο."""
    box = templates(text, re.compile(r"infobox football club season"))
    if not box:
        return {}
    p = params(box[0][1])
    out = {}
    if p.get("league result"):
        out["league"] = greek_result(p["league result"], True)
    cups = []
    for i in range(1, 6):
        name = p.get(f"cup{i}") if i > 1 or "cup1" in p else p.get("cup")
        res = p.get(f"cup{i} result") if i > 1 or "cup1 result" in p else p.get("cup result")
        if name and res:
            label = competition(plain(name)) or plain(name)
            if label == "Πρωτάθλημα":
                label = plain(name)
            cups.append({"name": label, "result": greek_result(res, False)})
    if cups:
        out["cups"] = cups
    top = plain(p.get("league topscorer", ""))
    if top:
        out["topscorer"] = top
    return out


def season(year: int) -> tuple[list[dict], dict]:
    text = fetch_wikitext(year)
    if not text:
        return [], {}
    summary = season_summary(text)
    if summary:
        summary["source"] = page_url(year)
    return season_matches(text, year), summary
