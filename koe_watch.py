"""Παρακολούθηση της ΚΟΕ για τα πρωταθλήματα υποδομής στο πόλο (Παίδων, Εφήβων, Νέων, Κορασίδων, Νεανίδων).

Τα πρωταθλήματα αυτά ξεκινούν τον Δεκέμβριο και δεν έχουν ακόμα πρόγραμμα. Σε κάθε ενημέρωση (update.yml) διαβάζει
τη σελίδα «Υδατοσφαίριση» του koe.org.gr και, για κάθε νέα ανακοίνωση που μοιάζει με προκήρυξη, πρόγραμμα ή
κλήρωση των ηλικιακών κατηγοριών, στέλνει ειδοποίηση στο θέμα του διαχειριστή («s:ops:live») και γράφει
σχόλιο σε ένα issue («ΚΟΕ: πόλο υποδομής»), ώστε να έρθει και email από το GitHub.
Ό,τι έχει ήδη ελεγχθεί κρατιέται στο docs/koe_watch.json (πηγαίνει στον κλάδο data μαζί με τα υπόλοιπα).

    python3 koe_watch.py          κανονικά
    DRY=1 python3 koe_watch.py    μόνο εμφάνιση, χωρίς ειδοποίηση, issue ή αποθήκευση
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

PAGES = ["https://koe.org.gr/sports/water-polo"]
STATE = Path(__file__).resolve().parent / "docs" / "koe_watch.json"
ISSUE = "ΚΟΕ: πόλο υποδομής"
UA = "Mozilla/5.0 (PAOKalendar; +https://paokalendar.gr)"
DRY = os.environ.get("DRY") == "1"

AGES = re.compile(r"παιδ|εφηβ|νεων\b|νεοι|κορασ|νεανιδ|υποδομ|αναπτυξ|ηλικιακ|u1\d|κ1\d|k1\d|"
                  r"paid|efiv|efib|neon\b|koras|neanid|ypodom|upodom|anaptu|anapty|ilikiak")
# Εθνικές ομάδες (Παγκόσμιο Νεανίδων, αποστολές, κλήσεις) δεν μας αφορούν.
NATIONAL = re.compile(r"εθνικ|παγκοσμ|ευρωπαικ|μεσογει|αποστολ|κληση|ethnik|pagkosm|europaik|mesogei|apostol|klisi")
KINDS = re.compile(r"προκηρυξ|προγραμμ|κληρωσ|πρωταθλ|ομιλ|prokir|prokhr|program|kliros|protathl|omil")


def plain(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def articles(page: str) -> list[tuple[str, str]]:
    """(διεύθυνση, τίτλος) των ανακοινώσεων της σελίδας, χωρίς διπλά."""
    out: dict[str, str] = {}
    for url, text in re.findall(r'<a[^>]+href="(https://koe\.org\.gr/article/[^"#?]+)"[^>]*>(.*?)</a>', page, re.S):
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()
        if len(title) > len(out.get(url, "")):
            out[url] = title
    return list(out.items())


def relevant(url: str, title: str) -> bool:
    t = plain(title + " " + url.rsplit("/", 1)[-1].replace("-", " "))
    return bool(AGES.search(t) and KINDS.search(t)) and not NATIONAL.search(t)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"seen": []}
    seen = set(state["seen"])
    found: list[tuple[str, str]] = []
    for page in PAGES:
        try:
            found += articles(fetch(page))
        except Exception as e:
            print(f"  ! ΚΟΕ {page}: {e}", file=sys.stderr)
    new = [(u, t) for u, t in found if u not in seen and relevant(u, t)]
    print(f"ΚΟΕ: {len(found)} ανακοινώσεις, {len(new)} νέες για τις υποδομές")
    for url, title in new:
        print(f"  {title} — {url}")
    if DRY:
        return 0
    if new:
        import notify
        import watchdog
        for url, title in new:
            notify._push([watchdog.TOPIC], "🤽 ΚΟΕ: πόλο υποδομής", title[:140], url, tag="koe-" + url.rsplit("/", 1)[-1][:40])
        try:
            issue = next((i for i in watchdog.gh("issues?state=open&per_page=50")
                          if i.get("title") == ISSUE and "pull_request" not in i), None)
            text = "Νέα ανακοίνωση της ΚΟΕ για τα τμήματα υποδομής στο πόλο:\n\n" + \
                "\n".join(f"- [{t}]({u})" for u, t in new)
            if issue:
                watchdog.gh(f"issues/{issue['number']}/comments", "POST", {"body": text})
            else:
                watchdog.gh("issues", "POST", {"title": ISSUE, "body": text + "\n\nΌταν βγει πρόγραμμα, προσθέτουμε "
                                               "τα τμήματα στις ακαδημίες. Το issue το κλείνεις όταν γίνει."})
        except Exception as e:
            print(f"  ! issue: {e}", file=sys.stderr)
    state["seen"] = sorted(seen | {u for u, _ in found})
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
