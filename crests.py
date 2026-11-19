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

import hashlib
import json
import re
import subprocess
import sys
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
    try:
        r = subprocess.run(["curl", "-sSL", "--fail", "--max-time", "30", "--max-filesize", str(MAX), "-A", UA, url],
                           capture_output=True, timeout=60)
        data = r.stdout if r.returncode == 0 else b""
    except Exception:
        data = b""
    ext = kind(data)
    if not ext:
        print(f"  ! σήμα: {url}", file=sys.stderr)
        have[key] = ""
        return ""
    name = f"{key}.{ext}"
    (DIR / name).write_bytes(data)
    have[key] = name
    print(f"  σήμα: {url} → {name}")
    return SITE + name


def main() -> int:
    matches_path, standings_path = DOCS / "matches.json", DOCS / "standings.json"
    if not matches_path.exists():
        return 0
    DIR.mkdir(exist_ok=True)
    have = {p.stem: p.name for p in DIR.iterdir() if p.is_file()}
    data = json.loads(matches_path.read_text(encoding="utf-8"))
    academy = {s["key"] for s in data.get("sections", []) if s.get("academy")}

    def swap(url: str) -> str:
        if not url or not re.match(r"https?://", url) or url.startswith(SITE):
            return url
        return local(url, have) or url

    changed = 0
    for m in data.get("matches", []):
        if m.get("section") not in academy:
            continue
        for k in ("homeLogo", "awayLogo"):
            new = swap(m.get(k) or "")
            if new != (m.get(k) or ""):
                m[k], changed = new, changed + 1
    if changed:
        matches_path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    if standings_path.exists():
        st = json.loads(standings_path.read_text(encoding="utf-8"))
        n = 0
        for key, tables in st.items():
            if key not in academy or not isinstance(tables, list):
                continue
            for t in tables:
                for row in t.get("rows", []):
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
