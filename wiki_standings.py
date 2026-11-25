#!/usr/bin/env python3
"""Βαθμολογίες παλιών σεζόν από τα άρθρα σεζόν της Wikipedia, για το αρχείο (archive.py standings).

Οι επίσημες πηγές (ESPN, esake.gr, waterpololeague.gr…) δίνουν μόνο την τρέχουσα βαθμολογία. Η Wikipedia έχει
ένα άρθρο ανά σεζόν πρωταθλήματος με τον πίνακα της κανονικής περιόδου:

- ποδόσφαιρο: «1985–86 Alpha Ethniki» / «2010–11 Super League Greece» (en)
- τα υπόλοιπα: τα ελληνικά άρθρα, π.χ. «Α1 Κατηγορία υδατοσφαίρισης ανδρών 2009-2010», που βρίσκονται με
  αναζήτηση στον τίτλο (οι ονομασίες αλλάζουν ανά εποχή: Α΄ Εθνική, Α1, Basket League…).

Από κάθε άρθρο κρατάμε τον πρώτο πίνακα που μοιάζει με βαθμολογία (στήλες ομάδα και βαθμοί, γραμμή του ΠΑΟΚ).
Η σελίδα παίρνεται ήδη μορφοποιημένη (HTML από το API), ώστε να διαβάζεται και το Module:Sports table.

    python3 wiki_standings.py football 1985     δοκιμή: εμφάνιση του πίνακα
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from build_calendars import clean, is_paok
from wiki import UA

API = "https://{lang}.wikipedia.org/w/api.php"

# Τμήμα → πού ψάχνουμε. «search»: ερωτήματα αναζήτησης· «titles»: κανονικές εκφράσεις για τους τίτλους που
# μετρούν (με τη σειρά προτίμησης όταν μια σεζόν έχει δύο άρθρα)· «make»: τίτλοι που φτιάχνονται από τη χρονιά.
# «score»: η στήλη υπέρ-κατά.
SPECS: dict[str, dict] = {
    "football": {"lang": "en", "score": "Γκολ",
                 "make": lambda y: [f"{y}–{_yy(y)} Alpha Ethniki", f"{y}–{_yy(y)} Super League Greece"]},
    "football-women": {"lang": "el", "score": "Γκολ",
                       "search": ['intitle:"ποδοσφαίρου γυναικών"'],
                       "titles": [r"^Α΄ (?:Εθνική )?(?:Κατηγορία )?ποδοσφαίρου γυναικών"],
                       "also": ("en", ["intitle:\"Greek A Division (women's football)\""],
                                [r"Greek A Division \(women's football\)$"])},
    "basketball": {"lang": "el", "score": "Πόντοι",
                   "search": ['intitle:"καλαθοσφαίρισης" intitle:"ανδρών"'],
                   "titles": [r"^Πρωτάθλημα καλαθοσφαίρισης (?:Α1|Α΄|Α') εθνικής κατηγορίας ανδρών",
                              r"^Πρωτάθλημα καλαθοσφαίρισης ανδρών Basket League",
                              r"^Πανελλήνιο πρωτάθλημα καλαθοσφαίρισης ανδρών"]},
    "basketball-women": {"lang": "el", "score": "Πόντοι",
                         "search": ['intitle:"καλαθοσφαίρισης" intitle:"γυναικών"'],
                         "titles": [r"^Πρωτάθλημα καλαθοσφαίρισης (?:Α1|Α΄|Α') εθνικής κατηγορίας γυναικών",
                                    r"^Πανελλήνιο πρωτάθλημα καλαθοσφαίρισης γυναικών"],
                         "also": ("en", ["intitle:\"Greek Women's Basketball League\""],
                                  [r"^\d{4}–\d{2} Greek Women's Basketball League$"])},
    "volley": {"lang": "el", "score": "Σετ",
               "search": ['intitle:"πετοσφαίρισης" intitle:"ανδρών"'],
               "titles": [r"^Πρωτάθλημα πετοσφαίρισης (?:Α1|Α΄|Α') εθνικής κατηγορίας ανδρών",
                          r"^Πρωτάθλημα πετοσφαίρισης ανδρών (?:Volley ?League|VolleyLeague)",
                          r"^Πανελλήνιο πρωτάθλημα πετοσφαίρισης ανδρών"]},
    "volley-women": {"lang": "el", "score": "Σετ",
                     "search": ['intitle:"πετοσφαίρισης" intitle:"γυναικών"'],
                     "titles": [r"^Πρωτάθλημα πετοσφαίρισης (?:Α1|Α΄|Α') εθνικής κατηγορίας γυναικών",
                                r"^Πρωτάθλημα πετοσφαίρισης γυναικών (?:Volley ?League|VolleyLeague)",
                                r"^Πανελλήνιο πρωτάθλημα πετοσφαίρισης γυναικών"]},
    "handball": {"lang": "el", "score": "Γκολ",
                 "search": ['intitle:"χειροσφαίρισης" intitle:"ανδρών"'],
                 "titles": [r"^Πρωτάθλημα χειροσφαίρισης (?:Α1|Α΄|Α') εθνικής κατηγορίας ανδρών",
                            r"^Πρωτάθλημα χειροσφαίρισης ανδρών Handball Premier",
                            r"^Πανελλήνιο πρωτάθλημα χειροσφαίρισης ανδρών"]},
    "handball-women": {"lang": "el", "score": "Γκολ",
                       "search": ['intitle:"χειροσφαίρισης" intitle:"γυναικών"'],
                       "titles": [r"^Πρωτάθλημα χειροσφαίρισης (?:Α1|Α΄|Α') εθνικής κατηγορίας γυναικών"]},
    "waterpolo": {"lang": "el", "score": "Γκολ",
                  "search": ['intitle:"υδατοσφαίρισης" intitle:"ανδρών"'],
                  "titles": [r"^Α1 (?:Κατηγορία|Εθνική) υδατοσφαίρισης ανδρών",
                             r"^Α΄ Εθνική Κατηγορία υδατοσφαίρισης ανδρών", r"^Εθνική Κατηγορία υδατοσφαίρισης ανδρών",
                             r"^Water Polo League ανδρών", r"^Πανελλήνιο πρωτάθλημα υδατοσφαίρισης ανδρών"]},
    "waterpolo-women": {"lang": "el", "score": "Γκολ",
                        "search": ['intitle:"υδατοσφαίρισης" intitle:"γυναικών"'],
                        "titles": [r"^Α1 (?:Κατηγορία|Εθνική) υδατοσφαίρισης γυναικών",
                                   r"^Α΄ Κατηγορία υδατοσφαίρισης γυναικών",
                                   r"^Water Polo League γυναικών", r"^Πανελλήνιο πρωτάθλημα υδατοσφαίρισης γυναικών"]},
}


def _yy(y: int) -> str:
    return f"{y + 1}" if y == 1999 else f"{(y + 1) % 100:02d}"


def _get(lang: str, params: dict) -> dict:
    url = API.format(lang=lang) + "?" + urllib.parse.urlencode({"format": "json", **params})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode())
            time.sleep(1)
            return d
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise
            time.sleep(10 * (attempt + 1))
    return {}


def search_titles(lang: str, query: str) -> list[str]:
    out, offset = [], 0
    while offset is not None and offset < 2000:
        d = _get(lang, {"action": "query", "list": "search", "srlimit": 500, "sroffset": offset, "srsearch": query,
                        "srnamespace": 0})
        out += [x["title"] for x in d.get("query", {}).get("search", [])]
        offset = (d.get("continue") or {}).get("sroffset")
    return out


# «2009-2010», «1993−94», «2013–14», «2020-21»: η σεζόν που αρχίζει τη χρονιά αυτή (μόνο με δεύτερη χρονιά).
_SEASON = re.compile(r"\b((?:19|20)\d\d)\s*[-–−/]\s*((?:19|20)?\d\d)\b")


def season_start(title: str) -> int | None:
    m = _SEASON.search(title)
    if not m:
        return None
    y, end = int(m.group(1)), m.group(2)
    end_y = int(end) if len(end) == 4 else (y // 100) * 100 + int(end)
    if end_y < y:
        end_y += 100
    return y if end_y == y + 1 else None


def season_articles(key: str) -> dict[int, list[tuple[str, str]]]:
    """Σεζόν → [(γλώσσα, τίτλος)] με τη σειρά προτίμησης."""
    spec = SPECS[key]
    out: dict[int, list[tuple[str, str]]] = {}
    if "make" in spec:
        return {y: [(spec["lang"], t) for t in spec["make"](y)] for y in range(1959, 2026)}
    groups = [(spec["lang"], spec["search"], spec["titles"])]
    if spec.get("also"):
        groups.append(spec["also"])
    for lang, queries, patterns in groups:
        found = []
        for q in queries:
            found += [t for t in search_titles(lang, q) if t not in found]
        for pat in patterns:
            for t in found:
                if re.search(pat, t) and not re.search(r"Κύπελλο|Cup|play ?off|πλέι|Super Cup|Κύπρου|Β΄|Α2|A2", t, re.I):
                    y = season_start(t)
                    if y is not None and (lang, t) not in out.get(y, []):
                        out.setdefault(y, []).append((lang, t))
    return out


def article_html(lang: str, title: str) -> tuple[str, str]:
    """(HTML, τελικός τίτλος μετά από ανακατεύθυνση)· κενό αν δεν υπάρχει."""
    d = _get(lang, {"action": "parse", "prop": "text", "redirects": 1, "formatversion": 2, "page": title})
    if "error" in d:
        return "", title
    return d["parse"]["text"], d["parse"]["title"]


def article_url(lang: str, title: str) -> str:
    return f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))


# ---------------------------------------------------------------- πίνακες

def _tables(page: str) -> list[str]:
    """Όλοι οι πίνακες της σελίδας, και οι εμφωλευμένοι χωριστά (η βαθμολογία είναι συχνά μέσα σε πίνακα διάταξης)."""
    out, stack = [], []
    for m in re.finditer(r"<table\b[^>]*>|</table>", page):
        if m.group(0).startswith("<table"):
            stack.append(m.start())
        elif stack:
            out.append((stack.pop(), page[:m.end()]))
    return [full[start:] for start, full in sorted(out, key=lambda x: x[0])]


_LINKS: dict[str, str] = {}  # κείμενο κελιού → σελίδα Wikipedia (από την τελευταία ανάγνωση)


def _rows(table: str) -> list[list[tuple[str, int]]]:
    """Γραμμές: (κείμενο κελιού, colspan). Χωρίς υποσημειώσεις [1], [α]."""
    inner = re.sub(r"^<table[^>]*>|</table>$", "", table)
    # Εμφωλευμένοι πίνακες έξω (μετρούν χωριστά)
    while re.search(r"<table\b", inner):
        new = re.sub(r"<table\b(?:(?!<table\b).)*?</table>", "", inner, flags=re.S)
        if new == inner:
            break
        inner = new
    inner = re.sub(r'<sup[^>]*class="[^"]*reference[^"]*"[^>]*>.*?</sup>', "", inner, flags=re.S)
    inner = re.sub(r"<style\b.*?</style>", "", inner, flags=re.S)
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", inner, re.S):
        cells = []
        for attrs, body in re.findall(r"<t[hd]([^>]*)>(.*?)</t[hd]>", tr, re.S):
            span = re.search(r'colspan="?(\d+)', attrs)
            # Ο σύνδεσμος του κελιού (σελίδα του συλλόγου, για το σήμα). Όχι εικόνες/σημαίες ή κόκκινοι σύνδεσμοι.
            link = next((html.unescape(h) for h in re.findall(r'<a[^>]+href="/wiki/([^"#?]+)"', body)
                         if not re.match(r"(?:File|Αρχείο|Εικόνα|Image):", urllib.parse.unquote(h))), "")
            _LINKS[clean(body)] = urllib.parse.unquote(link).replace("_", " ") if link else _LINKS.get(clean(body), "")
            cells.append((clean(body), int(span.group(1)) if span else 1))
        if cells:
            rows.append(cells)
    return rows


# Ετικέτες κεφαλίδας → στήλη. Πεζά, χωρίς τελείες/τόνους.
_LABELS = [
    ("pos", r"^(θεση|θ|θση|pos|#|α/α|κατ)$"),
    ("team", r"^(ομαδα|ομαδες|team|club|συλλογος|σωματειο)$"),
    ("gp", r"^(αγ|αγωνες|αγων|αγ ?\(?α\)?|pld|p|gp|α|g|ag|αγωνιες)$"),
    ("w", r"^(ν|νικες|w|νικ|n)$"),
    ("d", r"^(ι|ισοπαλιες|d|ισ|i)$"),
    ("l", r"^(η|ηττες|l|ητ|ηττ|h)$"),
    ("wl", r"^(ν-η|ν - η|w-l)$"),
    ("gf", r"^(γυ|γκολ υπερ|gf|pf|f|πυ|υπ|υπερ|πoντοι υπερ|ποντοι υπερ|συ|σετ υπερ|sw|γυ\+|επιθ|επιθεση)$"),
    ("ga", r"^(γκ|γκολ κατα|ga|pa|a|πκ|κατα|ποντοι κατα|σκ|σετ κατα|sl|αμυν|αμυνα)$"),
    ("gfa", r"^(γκολ|τερματα|ποντοι|σετ|γ|goals|sets|points|τερμ|σκορ|δ\.?τ|γκολ υπερ-κατα)$"),
    ("pts", r"^(β|βαθ|βαθμοι|βαθμ|βθμ|ποντ|pts|points|πτ|βθ|b|βαθμολογια)$"),
]


def _norm(label: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", label.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t.replace(".", "")).strip()


def _kind(label: str) -> str | None:
    n = _norm(label)
    if n == "pts" or n.startswith("βαθμ"):
        return "pts"
    for kind, pat in _LABELS:
        if re.match(pat, n):
            return kind
    return None


def _num(text: str) -> int | None:
    m = re.search(r"-?\d+", text.replace("−", "-"))
    return int(m.group()) if m else None


def _team(text: str) -> str:
    text = re.sub(r"\s*\[[^\]]*\]", "", text)
    text = re.sub(r"\s*\((?:[A-ZΑ-Ω]{1,3}(?:,\s*)?)+\)\s*$", "", text)  # (C), (R), (Π, Υ)
    return text.strip(" *†‡§")


def standings_from_html(page: str) -> tuple[list[str], list[dict]] | None:
    """Ο πρώτος πίνακας της σελίδας που είναι βαθμολογία με τον ΠΑΟΚ: (κεφαλίδες, γραμμές)."""
    for t in _tables(page):
        rows = _rows(t)
        if len(rows) < 5:
            continue
        # Κεφαλίδα: η πρώτη γραμμή με ομάδα και βαθμούς. Σε κεφαλίδα δύο γραμμών («Σύνολο» με colspan από πάνω,
        # «Β Ν Ι Η» από κάτω) οι θέσεις του colspan παίρνουν τις ετικέτες της δεύτερης γραμμής.
        found = None
        for hi, head in enumerate(rows[:4]):
            labels, single = [], []
            for text, span in head:
                labels += [text] + [""] * (span - 1)
                single += [span == 1] * span
            if any(span > 1 for _, span in head) and hi + 1 < len(rows):
                sub = [t for t, sp in rows[hi + 1] for _ in range(sp)]
                if len(sub) >= len(labels):  # η δεύτερη γραμμή έχει και τις κενές θέσεις
                    pad = len(sub) - len(labels)
                    labels = [b or (a if one else "") for a, b, one in zip(labels + [""] * pad, sub, single + [False] * pad)]
                else:
                    it = iter(sub)
                    merged = []
                    for text, span in head:
                        merged += [text] if span == 1 else [next(it, "") for _ in range(span)]
                    labels = merged
                kinds = [_kind(x) for x in labels]
                if "pts" in kinds and ("team" in kinds or "pos" in kinds or "w" in kinds):
                    found = hi + 1
                    break
            kinds = [_kind(x) for x in labels]
            if "pts" in kinds and ("team" in kinds or "pos" in kinds or "w" in kinds):
                found = hi
                break
        if found is None:
            continue
        hi = found
        width = len(kinds)
        first = {}
        for i, k in enumerate(kinds):
            if k and k not in first:
                first[k] = i
        last_used = max(first.values())
        out, last_pos = [], 0
        for r in rows[hi + 1:]:
            cells = []
            for text, span in r:
                cells += [text] * span
            if len(cells) < width and kinds[0] == "pos" and _num(cells[0]) is None and cells and re.search(r"[A-Za-zΑ-Ωα-ω]", cells[0]):
                cells = [str(last_pos)] + cells  # rowspan στη θέση (ισοβαθμία)
            if len(cells) < min(width - 1, last_used + 1):
                continue
            col = {}
            for i, k in enumerate(kinds):
                if k and k not in col and i < len(cells):
                    col[k] = cells[i]
            team = col.get("team")
            if team is None:  # χωρίς ετικέτα «Ομάδα»: το πρώτο κελί με γράμματα
                team = next((c for c in cells if len(re.findall(r"[A-Za-zΑ-Ωα-ωά-ώΆ-Ώ]", c)) >= 3), "")
            raw, team = team, _team(team)
            pts = _num(col.get("pts", ""))
            if not team or pts is None:
                continue
            pos = _num(col.get("pos", "")) or (last_pos + 1)
            last_pos = pos
            if "wl" in col and "w" not in col:
                w, _, l = col["wl"].partition("-")
                col["w"], col["l"] = w.strip(), l.strip()
            if "gfa" in col and "gf" not in col:
                f, _, a = re.sub(r"\s", "", col["gfa"]).replace("–", "-").partition("-")
                col["gf"], col["ga"] = f, a
            out.append({"pos": pos, "team": team, "raw": raw, **{k: col[k] for k in ("gp", "w", "d", "l", "gf", "ga") if k in col},
                        "pts": str(pts)})
        if len(out) >= 4 and any(_paok(x["team"]) for x in out):
            return [k for k in ("gp", "w", "d", "l", "gf", "pts") if any(k in x for x in out)], out
    return None


def _paok(name: str) -> bool:
    """Και ενωμένες ομάδες, π.χ. «Φιλαθλητικός / ΠΑΟΚ»."""
    return is_paok(name) or bool(re.search(r"(?<![Α-Ωα-ω])Π\.?Α\.?Ο\.?Κ\.?(?![Α-Ωα-ω])|\bPAOK\b", name))


def greek_title(title: str) -> str:
    """«Παναθηναϊκός (ποδόσφαιρο)» → «Παναθηναϊκός», «Π.Α.Ε. Άρης» → «Άρης»."""
    t = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
    return re.sub(r"^(?:Π\.?Α\.?Ε\.?|Π\.?Α\.?Σ\.?Ε\.?)\s+", "", t)


def clubs(lang: str, names: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Για τα ονόματα του πίνακα, από τη σελίδα κάθε συλλόγου στη Wikipedia: (όνομα → σήμα, όνομα → ελληνικό
    όνομα). Το σήμα είναι μικρογραφία της κύριας εικόνας της σελίδας· το ελληνικό όνομα ο τίτλος του ελληνικού
    άρθρου (μόνο για την αγγλική Wikipedia)."""
    titles = {n: _LINKS.get(n, "") for n in names}
    want = sorted({t for t in titles.values() if t})
    image: dict[str, str] = {}
    greek: dict[str, str] = {}
    for i in range(0, len(want), 40):
        params = {"action": "query", "prop": "pageimages|langlinks", "piprop": "thumbnail", "pithumbsize": 96,
                  "pilicense": "any", "redirects": 1, "lllang": "el", "lllimit": "max", "titles": "|".join(want[i:i + 40])}
        # Η απάντηση έρχεται σε κομμάτια («continue»): οι εικόνες και οι σύνδεσμοι γλώσσας κάθε σελίδας μαζεύονται.
        alias: dict[str, str] = {}
        pages: dict[str, dict] = {}
        cont: dict = {}
        for _ in range(20):
            d = _get(lang, {**params, **cont})
            q = d.get("query", {})
            alias.update({x["from"]: x["to"] for x in q.get("normalized", []) + q.get("redirects", [])})
            for pg in q.get("pages", {}).values():
                have = pages.setdefault(pg["title"], {})
                for k, v in pg.items():
                    if k == "langlinks":
                        have.setdefault(k, []).extend(v)
                    elif k not in have:
                        have[k] = v
            cont = d.get("continue") or {}
            if not cont:
                break
        for t in want[i:i + 40]:
            pg = pages.get(alias.get(alias.get(t, t), alias.get(t, t)), {})
            src = pg.get("thumbnail", {}).get("source", "")
            if src and not re.search(r"(?i)flag|σημαία|map|χάρτης|location|locator", src):
                image[t] = src
            el = next((x.get("*") or x.get("title") for x in pg.get("langlinks", []) if x.get("lang") == "el"), "")
            if el:
                greek[t] = greek_title(el)
    return ({n: image[t] for n, t in titles.items() if t in image},
            {n: greek[t] for n, t in titles.items() if t in greek})


def to_table(key: str, title: str, url: str, kinds: list[str], rows: list[dict],
             logos: dict[str, str] | None = None, names: dict[str, str] | None = None) -> dict:
    """Στη μορφή του standings.table (columns + rows με cells)."""
    names = {"gp": "Αγ", "w": "Ν", "d": "Ι", "l": "Η", "gf": SPECS[key]["score"], "pts": "Β"}
    cols = [k for k in kinds if k != "d" or any(x.get("d") not in (None, "", "0") for x in rows)]
    def cell(x, k):
        if k == "gf":
            return f"{x.get('gf', '')}-{x.get('ga', '')}" if x.get("gf") else ""
        return x.get(k, "")
    league = re.sub(r"\s*\(?(?:19|20)\d\d\s*[-–−/]\s*(?:19|20)?\d\d\)?\s*", " ", title).strip()
    league = {"Alpha Ethniki": "Α' Εθνική", "Super League Greece": "Super League",
              "Greek A Division (women's football)": "Α' Εθνική Γυναικών",
              "Greek Women's Basketball League": "Α1 Γυναικών"}.get(league, league)
    return {"title": league, "url": url, "columns": [names[k] for k in cols], "source": "wikipedia",
            "rows": [{"pos": x["pos"], "team": "ΠΑΟΚ" if is_paok(x["team"]) else (names or {}).get(x["raw"]) or x["team"],
                      **({"en": x["team"]} if (names or {}).get(x["raw"]) and not is_paok(x["team"]) else {}),
                      "logo": "" if _paok(x["team"]) else (logos or {}).get(x["raw"], ""),
                      "paok": _paok(x["team"]), "cells": [cell(x, k) for k in cols]} for x in rows]}


def season_table(key: str, year: int, articles: dict[int, list[tuple[str, str]]] | None = None) -> dict | None:
    for lang, title in (articles if articles is not None else season_articles(key)).get(year, []):
        page, real = article_html(lang, title)
        if not page:
            continue
        _LINKS.clear()
        got = standings_from_html(page)
        if got:
            try:
                logos, names = clubs(lang, [x["raw"] for x in got[1]])
            except Exception as e:
                print(f"  ! σήματα {real}: {e}", file=sys.stderr)
                logos, names = {}, {}
            return to_table(key, real, article_url(lang, real), *got, logos=logos,
                            names=names if lang == "en" else None)
    return None


if __name__ == "__main__":
    key, year = sys.argv[1], int(sys.argv[2])
    t = season_table(key, year)
    print(json.dumps(t, ensure_ascii=False, indent=1) if t else "—")
