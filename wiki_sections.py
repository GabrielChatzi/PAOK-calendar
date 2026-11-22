"""Περίληψη ανά σεζόν (τελική θέση, κύπελλο, Ευρώπη) για τμήματα χωρίς σελίδες σεζόν στη Wikipedia.

Τα άρθρα των τμημάτων έχουν πίνακες «ανά σεζόν» σε τρεις μορφές, και για καθεμία υπάρχει εδώ αναγνώστης:
  - «κάθετος» πίνακας, μία σεζόν ανά γραμμή (PAOK BC, PAOK FC (women), βόλεϊ ανδρών)
  - «πλέγμα» θέσεων: στήλες οι σεζόν, γραμμές οι θέσεις, σημαδεμένο το κελί (μπάσκετ, χάντμπολ ανδρών)
  - λίστα «* 2018-19: Πρε Λιγκ 1η» (βόλεϊ γυναικών)
Το περιεχόμενο είναι CC BY-SA: η σελίδα του αρχείου γράφει την πηγή.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from wiki import UA, plain

# Τμήμα → άρθρα (γλώσσα, τίτλος, μορφή). Το πρώτο που δίνει κάτι για μια σεζόν μετρά.
SOURCES = {
    "basketball": [("en", "PAOK BC", "vertical"), ("el", "Π.Α.Ο.Κ. (καλαθοσφαίριση ανδρών)", "grid")],
    "volley": [("el", "Π.Α.Ο.Κ. (πετοσφαίριση ανδρών)", "vertical")],
    "volley-women": [("el", "Π.Α.Ο.Κ. (πετοσφαίριση γυναικών)", "bullets")],
    "handball": [("el", "Π.Α.Ο.Κ. (χειροσφαίριση ανδρών)", "grid")],
    "football-women": [("en", "PAOK FC (women)", "vertical")],
}


def article_url(lang: str, title: str) -> str:
    return f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))


def fetch_article(lang: str, title: str) -> str:
    url = f"https://{lang}.wikipedia.org/w/api.php?format=json&action=parse&prop=wikitext&redirects=1&page=" + urllib.parse.quote(title)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode())
            time.sleep(1.5)
            return d.get("parse", {}).get("wikitext", {}).get("*", "")
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            time.sleep(10 * (attempt + 1))
    return ""


def season_key(text: str) -> str | None:
    """«1958–59», «2001-2002», «[[…1999-2000|00]]» → «1958-59», «2001-02», «1999-00»."""
    m = re.search(r"((?:19|20)\d\d)\s*[–\-−/]\s*((?:19|20)?\d\d)", text)
    if m:
        return f"{m[1]}-{m[2][-2:]}"
    return None


def _cell_value(cell: str) -> str:
    """«style="…" | τιμή» → «τιμή» (το | μέσα σε [[ ]] ή {{ }} δεν χωρίζει)."""
    depth, cut = 0, -1
    for i, ch in enumerate(cell):
        two = cell[i:i + 2]
        if two in ("[[", "{{"):
            depth += 1
        elif two in ("]]", "}}"):
            depth -= 1
        elif ch == "|" and depth == 0 and cell[i + 1:i + 2] != "|" and cell[i - 1:i] != "|":
            cut = i
    value = cell[cut + 1:] if cut >= 0 and re.search(r"=", cell[:cut]) else cell
    return value.strip()


def tables(text: str) -> list[tuple[int, list[list[tuple[bool, str]]]]]:
    """Οι πίνακες wiki: (θέση, γραμμές), κάθε γραμμή [(επικεφαλίδα;, κελί)]· τα κελιά ως wikitext."""
    out = []
    for m in re.finditer(r"^\{\|.*?^\|\}", text, re.M | re.S):
        rows, cur = [], []
        for line in m[0].split("\n")[1:-1]:
            s = line.strip()
            if s.startswith("|-"):
                if cur:
                    rows.append(cur)
                cur = []
                continue
            if s.startswith("|+"):
                continue
            if s.startswith("!") or s.startswith("|"):
                head = s.startswith("!")
                body = s[1:]
                parts = re.split(r"!!" if head else r"\|\|", body) if head else _split_cells(body)
                cur += [(head, _cell_value(p)) for p in parts]
            elif cur:  # συνέχεια του προηγούμενου κελιού
                h, v = cur[-1]
                cur[-1] = (h, v + "\n" + line)
        if cur:
            rows.append(cur)
        out.append((m.start(), rows))
    return out


def _split_cells(body: str) -> list[str]:
    parts, depth, cur, i = [], 0, "", 0
    while i < len(body):
        two = body[i:i + 2]
        if two in ("[[", "{{"):
            depth += 1
        elif two in ("]]", "}}"):
            depth -= 1
        if two == "||" and depth == 0:
            parts.append(cur)
            cur = ""
            i += 2
            continue
        cur += body[i]
        i += 1
    parts.append(cur)
    return parts


EN_WORDS = [(r"^champions?$", "Πρωταθλητής"), (r"^winners?$", "Κατάκτηση"), (r"^runners?[ -]?up$", "2η θέση"),
            (r"^final(ist)?s?$", "Φιναλίστ"), (r"^semi-?finals?$", "Ημιτελικά"), (r"^quarter-?finals?$", "Προημιτελικά"),
            (r"^last (\d+)$", r"Φάση των \1"), (r"^round of (\d+)$", r"Φάση των \1"), (r"^top (\d+)$", r"Top \1"),
            (r"^group stage$|^groups?$|^regular season$", "Όμιλοι"), (r"^(\d+)(?:st|nd|rd|th)(?: place)?$", r"\1η θέση"),
            (r"^qualifying rounds?$|^qualification$", "Προκριματικά"),
            (r"^no tournament$|^—$|^-$|^did not (?:participate|qualify)$|^dnq$|^not participated$|^tbd$|^tba$", "")]


def greek(value: str) -> str:
    v = plain(value).strip()
    for rx, g in EN_WORDS:
        if re.match(rx, v, re.I):
            return re.sub(rx, g, v, flags=re.I)
    v = re.sub(r"(\d+)(?:st|nd|rd|th) place", r"\1η θέση", v, flags=re.I)
    return v


def europe(cell: str) -> dict | None:
    """«[[Korać Cup]] <br>[[1974–75 FIBA Korać Cup|Last 32]]» → {"name": "Korać Cup", "result": "Φάση των 32"}."""
    parts = [plain(p) for p in re.split(r"<br\s*/?>", cell) if plain(p)]
    if not parts or greek(parts[0]) == "":
        return None
    if len(parts) == 1:
        return {"name": "Ευρώπη", "result": greek(parts[0])}
    return {"name": parts[0], "result": greek(parts[1])} if greek(parts[1]) else None


def vertical(text: str) -> dict[str, dict]:
    """Πίνακες με μία σεζόν ανά γραμμή· οι στήλες από τις επικεφαλίδες."""
    out: dict[str, dict] = {}
    for _, rows in tables(text):
        heads = [plain(c).lower() for row in rows[:2] for h, c in row if h]
        if not any(re.match(r"season|περίοδος|σεζόν", h) for h in heads):
            continue
        header = [plain(c).lower() for h, c in rows[0] if h] if rows and rows[0] and rows[0][0][0] else []
        for row in rows:
            cells = [c for h, c in row]
            if not cells or all(h for h, _ in row):
                continue
            season = season_key(plain(cells[0])) or season_key(cells[0])
            if not season:
                continue
            info: dict = {}
            if "greek league" in header:  # PAOK BC: Season, Greek League, Greek Cup, Europe, …
                idx = {k: header.index(k) for k in ("greek league", "greek cup", "europe") if k in header}
                if len(cells) > idx.get("greek league", 99):
                    info["league"] = greek(cells[idx["greek league"]])
                cups = []
                if "greek cup" in idx and len(cells) > idx["greek cup"] and greek(cells[idx["greek cup"]]):
                    cups.append({"name": "Κύπελλο Ελλάδας", "result": greek(cells[idx["greek cup"]])})
                if "europe" in idx and len(cells) > idx["europe"]:
                    e = europe(cells[idx["europe"]])
                    if e:
                        cups.append(e)
                if cups:
                    info["cups"] = cups
            elif any(h in ("θέση",) for h in header):  # βόλεϊ: Περίοδος, Θέση, Ν–Η
                pos = header.index("θέση")
                if len(cells) > pos:
                    info["league"] = re.sub(r"^(\d+)η?$", r"\1η θέση", plain(cells[pos]))
                if len(cells) > pos + 1 and re.fullmatch(r"\d+\s*[–-]\s*\d+", plain(cells[pos + 1])):
                    info["record"] = plain(cells[pos + 1]).replace("-", "–") + " (Ν–Η)"
            elif "pos" in heads or "position" in " ".join(heads):  # ποδόσφαιρο γυναικών: Season, Div, Pos, Pld, W, D, L, GF, GA, Pts
                if len(cells) > 2:
                    info["league"] = greek(cells[2])
                nums = [plain(c) for c in cells[3:10]]
                if len(nums) >= 4 and all(re.fullmatch(r"\d+", x) for x in nums[1:4]):
                    info["record"] = f"{nums[1]}–{nums[2]}–{nums[3]} (Ν–Ι–Η)"
            if info.get("cups"):
                info["cups"] = [c for c in info["cups"] if c.get("result")]
            info = {k: v for k, v in info.items() if v}
            if info:
                out.setdefault(season, info)
    return out


def grid(text: str) -> dict[str, dict]:
    """Πλέγμα θέσεων: στη γραμμή επικεφαλίδων οι σεζόν, μετά μία γραμμή ανά θέση με σημαδεμένα κελιά."""
    out: dict[str, dict] = {}
    for _, rows in tables(text):
        if not rows or plain(rows[0][0][1]) not in ("Θ.", "Θ", "Θέση"):
            continue
        seasons = []
        for h, c in rows[0][1:]:
            s = season_key(c)
            if not s:
                yy = re.search(r"(\d\d)", plain(c))
                if yy:
                    end = int(yy[1]) + (1900 if int(yy[1]) >= 50 else 2000)
                    s = f"{end - 1}-{yy[1]}"
            seasons.append(s)
        for row in rows[1:]:
            if not row or not row[0][0]:
                continue
            pos = plain(row[0][1])
            if not re.fullmatch(r"\d{1,2}", pos):
                continue
            for i, (h, c) in enumerate(row[1:]):
                if i < len(seasons) and seasons[i] and plain(c):
                    out.setdefault(seasons[i], {"league": "Πρωταθλητής" if pos == "1" else f"{pos}η θέση"})
    return out


def bullets(text: str) -> dict[str, dict]:
    """«* 2018-19: Πρε Λιγκ 1η {{προβιβασμός}}» → {"2018-19": {"league": "Πρε Λιγκ, 1η θέση (άνοδος)"}}."""
    out = {}
    for m in re.finditer(r"^\*\s*((?:19|20)\d\d\s*[-–]\s*\d\d)\s*:\s*(.+)$", text, re.M):
        s = season_key(m[1])
        raw = m[2]
        note = " (άνοδος)" if "προβιβασμ" in raw else " (υποβιβασμός)" if "υποβιβασμ" in raw else ""
        v = plain(raw)
        mm = re.match(r"^(.*?)\s*(\d{1,2})η(?: θέση)?\s*$", v)
        if mm:
            v = f"{mm[1]}, {mm[2]}η θέση" if mm[1] else f"{mm[2]}η θέση"
        v = v.strip(" -")
        if s and v:
            out[s] = {"league": v + note}
    return out


READERS = {"vertical": vertical, "grid": grid, "bullets": bullets}


def summaries() -> dict[str, dict[str, dict]]:
    """{τμήμα: {σεζόν: {"league", "cups", "record", "source"}}}."""
    out: dict[str, dict[str, dict]] = {}
    for key, sources in SOURCES.items():
        got: dict[str, dict] = {}
        for lang, title, kind in sources:
            try:
                text = fetch_article(lang, title)
            except Exception as e:
                print(f"  ! {title}: {e}")
                continue
            for season, info in READERS[kind](text).items():
                if season not in got:
                    got[season] = {**info, "source": article_url(lang, title)}
        out[key] = got
        print(f"{key}: {len(got)} σεζόν" + (f" ({min(got)} → {max(got)})" if got else ""))
    return out
