"""Αντίγραφα των σημάτων των αντιπάλων στις ακαδημίες, ώστε να μη χαθούν αν μια πηγή μπλοκάρει ή σβήσει εικόνες.

Τρέχει στο update.yml μετά τον builder. Για κάθε σήμα με εξωτερική διεύθυνση (paokfc.gr, epesth.gr, ekasth.gr,
sl2.gr, epo.gr…) στους αγώνες και στις βαθμολογίες των ακαδημιών:
- το κατεβάζει μία φορά στο docs/crests/<hash>.<png|jpg|gif|webp|svg> (πηγαίνει στον κλάδο data μαζί με τα
  υπόλοιπα και το σερβίρει το api/data.js ως https://paokalendar.gr/crests/…),
- και γράφει στο matches.json / standings.json τη δική μας διεύθυνση.
Το όνομα του αρχείου βγαίνει από την αρχική διεύθυνση, οπότε ένα σήμα που κατέβηκε μια φορά μένει, ακόμα κι αν
η πηγή αργότερα δεν απαντά. Αν δεν κατέβει (και δεν υπάρχει από πριν), μένει η αρχική διεύθυνση.

    python3 crests.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import unicodedata
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

DOCS = Path(__file__).resolve().parent / "docs"
DIR = DOCS / "crests"
SITE = "https://paokalendar.gr/crests/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
MAX = 1_000_000


def kind(data: bytes) -> str:
    """Τι εικόνα είναι, από τα πρώτα bytes (κενό: δεν είναι εικόνα, π.χ. σελίδα σφάλματος)."""
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"\xff\xd8"):
        return "jpg"
    if data.startswith(b"GIF8"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    head = data[:400].lstrip().lower()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in head):
        return "svg"
    return ""


def local(url: str, have: dict[str, str]) -> str:
    """Η δική μας διεύθυνση για το σήμα (το κατεβάζει αν χρειάζεται)· κενό αν δεν υπάρχει αντίγραφο."""
    key = hashlib.sha1(url.encode()).hexdigest()[:16]
    if key in have:
        return SITE + have[key]
    data, ext = b"", ""
    # Πρώτα απευθείας· αν η πηγή μπλοκάρει (π.χ. Cloudflare στο paokfc.gr), μέσω της υπηρεσίας εικόνων wsrv.nl.
    for src in (url, "https://wsrv.nl/?url=" + urllib.parse.quote(url, safe="")):
        try:
            r = subprocess.run(["curl", "-sSL", "--fail", "--max-time", "30", "--max-filesize", str(MAX), "-A", UA, src],
                               capture_output=True, timeout=60)
            data = r.stdout if r.returncode == 0 else b""
        except Exception:
            data = b""
        ext = kind(data)
        if ext:
            break
    if not ext:
        print(f"  ! σήμα: {url}", file=sys.stderr)
        have[key] = ""
        return ""
    name = f"{key}.{ext}"
    (DIR / name).write_bytes(data)
    have[key] = name
    print(f"  σήμα: {url} → {name}")
    return SITE + name


# ---------------------------------------------------------------- σήματα που λείπουν
# Για αντιπάλους χωρίς σήμα στην πηγή (π.χ. ΕΠΣ Μακεδονίας): (1) ίδιο όνομα σε άλλο τμήμα του site (π.χ. ΧΑΝΘ από
# το μπάσκετ), (2) οι διοργανώσεις της ΕΠΟ, (3) η ελληνική Wikipedia (εικόνα της σελίδας του συλλόγου). Μόνο όταν
# ταιριάζουν όλες οι λέξεις του ονόματος. Τα ευρήματα (και όσα δεν βρέθηκαν, για 30 μέρες) στο docs/crest_lookup.json.
LOOKUP = DOCS / "crest_lookup.json"
GENERIC = {"ΑΟ", "ΑΕ", "ΑΣ", "ΠΑΕ", "ΓΣ", "ΠΟ", "ΑΜΣ", "ΑΟΚ", "ΑΚΑΔ", "ΑΚΑΔΗΜΙΑ", "ΠΟΔ", "ΜΑΣ", "ΓΑΣ", "ΠΑΣ", "ΑΠΣ",
           "ΑΠΟ", "ΑΜΟ", "ΠΑΟ", "ΑΠΟΕ", "ΑΕΠΣ", "ΑΓΠΣ", "ΦΣ", "ΜΓΣ", "ΝΓΣΘ", "ΑΝΔΡΩΝ", "ΓΥΝΑΙΚΩΝ", "ΠΟΔΟΣΦΑΙΡΟ", "ΠΟΔΟΣΦΑΙΡΙΚΟΣ",
           "ΟΜΙΛΟΣ", "ΑΘΛΗΤΙΚΟΣ", "ΣΥΛΛΟΓΟΣ", "ΝΕΩΝ", "ΝΕΑΝΙΔΩΝ", "ΚΟΡΑΣΙΔΩΝ", "ΠΑΙΔΩΝ", "ΜΦΑΟΦ", "ΑΠΟΕ"}
EPO_COMPS = [3, 5, 6, 9, 10, 26, 27, 37, 38, 56]
OTHER_SPORT = re.compile(r"καλαθοσφαιρ|πετοσφαιρ|χειροσφαιρ|υδατοσφαιρ|βολει|μπασκετ|πολο\b", re.I)


def plain(text: str) -> str:
    t = unicodedata.normalize("NFD", text)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").upper()
    return t.translate(str.maketrans("ABEZHIKMNOPTYX", "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ"))


def words(name: str) -> frozenset[str]:
    """Οι λέξεις που ξεχωρίζουν το όνομα (5 πρώτα γράμματα): χωρίς «Α.Σ.», «(1)», «Κ17», χρονιές, «(ποδόσφαιρο)»."""
    t = plain(name).replace(".", " ")  # «Μ.ΑΛΕΞΑΝΔΡΟΣ» → «ΑΛΕΞΑΝΔΡΟΣ», «Α.Σ.» → (τίποτα)
    t = re.sub(r"\((?:\d|ΠΟΔΟΣΦΑΙΡ[^)]*)\)|\bΚ\d\d\b|\b\d+\b", " ", t)
    return frozenset(w[:5] for w in re.findall(r"[Α-ΩA-Z0-9]+", t) if len(w) > 1 and w not in GENERIC)


def http(url: str) -> str:
    r = subprocess.run(["curl", "-sSL", "--fail", "--max-time", "30", "-A", "PAOKalendar/1.0 (+https://paokalendar.gr)", url],
                       capture_output=True, timeout=60)
    if r.returncode:
        raise RuntimeError(f"curl {r.returncode}")
    return r.stdout.decode("utf-8", "replace")


def epo_pool() -> dict[frozenset, set]:
    """Όνομα → σήμα από τις διοργανώσεις της ΕΠΟ (αγώνες και βαθμολογίες, όλοι οι όμιλοι)."""
    pool: dict[frozenset, set] = {}

    def grab(page: str) -> None:
        for tr in re.findall(r"<tr>(.*?)</tr>", page, re.S):
            m = re.search(r'<img[^>]+src="([^"]+)".*?class="team-text">([^<]+)<', tr, re.S)
            if m:
                pool.setdefault(words(html.unescape(m.group(2))), set()).add("https://www.epo.gr" + html.unescape(m.group(1)))
        for block in page.split("node--type-national-match")[1:]:
            names = [re.sub(r"<[^>]+>", "", n).strip() for n in re.findall(r"field--name-name[^>]*>(.*?)</div>", block, re.S)[:2]]
            logos = re.findall(r'field--name-field-icon.*?<img[^>]+src="([^"]+)"', block, re.S)[:2]
            for n, logo in zip(names, logos):
                pool.setdefault(words(html.unescape(n)), set()).add("https://www.epo.gr" + html.unescape(logo))

    for comp in EPO_COMPS:
        try:
            page = http(f"https://www.epo.gr/el/competition/{comp}/matches")
            grab(page)
            for u in dict.fromkeys(re.findall(rf'value="(/el/competition/{comp}/stage/\d+/group/\d+/matches)"', page)):
                grab(http("https://www.epo.gr" + html.unescape(u)))
        except Exception as e:
            print(f"  ! ΕΠΟ {comp}: {e}", file=sys.stderr)
    return pool


def wiki(name: str) -> str:
    """Η εικόνα της σελίδας του συλλόγου στην ελληνική Wikipedia, αν ο τίτλος έχει ακριβώς τις ίδιες λέξεις."""
    want = words(name)
    q = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": re.sub(r"\(\d\)", "", name) + " ποδόσφαιρο",
                                "srlimit": 5, "format": "json"})
    hits = json.loads(http("https://el.wikipedia.org/w/api.php?" + q))["query"]["search"]
    titles = [h["title"] for h in hits if same_club(want, words(h["title"])) and not OTHER_SPORT.search(plain(h["title"]).lower())]
    if not titles:
        return ""
    q = urllib.parse.urlencode({"action": "query", "prop": "pageimages", "piprop": "original", "titles": titles[0], "format": "json"})
    pages = json.loads(http("https://el.wikipedia.org/w/api.php?" + q))["query"]["pages"]
    src = next(iter(pages.values())).get("original", {}).get("source", "")
    return src.split("?")[0]


def same_club(ours: frozenset, theirs: frozenset) -> bool:
    """Ίδιες λέξεις, ή (για ονόματα με 2+ λέξεις) όλες οι δικές μας στο άλλο όνομα («Αγροτικός Αστέρας» → «… Ευόσμου»)."""
    return bool(ours) and (ours == theirs or (len(ours) >= 2 and ours <= theirs))


def pick(pool: dict[frozenset, set], w: frozenset) -> str:
    urls = {u for k, us in pool.items() if same_club(w, k) for u in us}
    return next(iter(urls)) if len(urls) == 1 else ""


def find_missing(names: set[str], known: dict[frozenset, set]) -> dict[str, str]:
    """Σήματα για ονόματα χωρίς σήμα· γράφει/διαβάζει το docs/crest_lookup.json."""
    cache = json.loads(LOOKUP.read_text(encoding="utf-8")) if LOOKUP.exists() else {}
    today = dt.date.today()
    todo = [n for n in sorted(names) if words(n) and not (
        n in cache and (cache[n]["url"] or dt.date.fromisoformat(cache[n]["at"]) > today - dt.timedelta(days=30)))]
    pool = None
    for n in todo:
        w, url, src = words(n), "", ""
        url = pick(known, w)
        src = "site" if url else ""
        if not url:
            if pool is None:
                pool = epo_pool()
            url = pick(pool, w)
            src = "epo" if url else ""
        if not url:
            try:
                url, src = wiki(n), "wikipedia"
            except Exception as e:
                print(f"  ! Wikipedia {n}: {e}", file=sys.stderr)
        cache[n] = {"url": url, "source": src if url else "", "at": today.isoformat()}
        print(f"  {n}: {src + ' ' + url if url else '—'}")
    if todo:
        LOOKUP.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {n: v["url"] for n, v in cache.items() if v.get("url")}


def main() -> int:
    matches_path, standings_path = DOCS / "matches.json", DOCS / "standings.json"
    if not matches_path.exists():
        return 0
    DIR.mkdir(exist_ok=True)
    have = {p.stem: p.name for p in DIR.iterdir() if p.is_file()}
    data = json.loads(matches_path.read_text(encoding="utf-8"))
    academy = {s["key"] for s in data.get("sections", []) if s.get("academy")}

    st = json.loads(standings_path.read_text(encoding="utf-8")) if standings_path.exists() else {}
    # Σήματα που λείπουν: πρώτα τα ονόματα με σήμα σε όλο το site (κάθε άθλημα), μετά ΕΠΟ και Wikipedia.
    known: dict[frozenset, set] = {}
    missing: set[str] = set()

    def note(name: str, logo: str, section: str) -> None:
        if not name or "ΠΑΟΚ" in plain(name):
            return
        if logo:
            known.setdefault(words(name), set()).add(logo)
        elif section in academy:
            missing.add(name)
    for m in data.get("matches", []):
        note(m.get("home", ""), m.get("homeLogo", ""), m.get("section"))
        note(m.get("away", ""), m.get("awayLogo", ""), m.get("section"))
    for key, tables in st.items():
        for t in tables if isinstance(tables, list) else []:
            for row in t.get("rows", []):
                note(row.get("team", ""), row.get("logo", ""), key)
    found = find_missing(missing, known) if missing else {}

    def swap(url: str) -> str:
        if not url or not re.match(r"https?://", url) or url.startswith(SITE):
            return url
        return local(url, have) or url

    changed = 0
    for m in data.get("matches", []):
        if m.get("section") not in academy:
            continue
        for side in ("home", "away"):
            if not m.get(side + "Logo") and found.get(m.get(side, "")):
                m[side + "Logo"] = found[m[side]]
        for k in ("homeLogo", "awayLogo"):
            new = swap(m.get(k) or "")
            if new != (m.get(k) or ""):
                m[k], changed = new, changed + 1
    if changed:
        matches_path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    if standings_path.exists():
        n = 0
        for key, tables in st.items():
            if key not in academy or not isinstance(tables, list):
                continue
            for t in tables:
                for row in t.get("rows", []):
                    if not row.get("logo") and found.get(row.get("team", "")):
                        row["logo"] = found[row["team"]]
                    new = swap(row.get("logo") or "")
                    if new != (row.get("logo") or ""):
                        row["logo"], n = new, n + 1
        if n:
            standings_path.write_text(json.dumps(st, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        changed += n
    saved = sum(1 for v in have.values() if v)
    print(f"Σήματα ακαδημιών: {saved} αντίγραφα, {changed} διευθύνσεις άλλαξαν")
    return 0


if __name__ == "__main__":
    sys.exit(main())
