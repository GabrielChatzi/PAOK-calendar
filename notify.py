#!/usr/bin/env python3
"""Ειδοποιήσεις ntfy για τους αγώνες του ΠΑΟΚ.

Κάθε τμήμα έχει τρία θέματα (topics) στο ntfy.sh, ώστε ο καθένας να διαλέγει τι θέλει:
    <PREFIX>-<τμήμα>-pre     υπενθύμιση περίπου μία ώρα πριν από τον αγώνα
    <PREFIX>-<τμήμα>-time    νέος αγώνας στο πρόγραμμα ή αλλαγή ημέρας/ώρας
    <PREFIX>-<τμήμα>-result  τελικό αποτέλεσμα

Οι αλλαγές και τα αποτελέσματα στέλνονται από το build_calendars.py όταν ενημερώνεται το
πρόγραμμα. Οι υπενθυμίσεις στέλνονται από αυτό το script (python3 notify.py reminders),
που τρέχει κάθε 15 λεπτά και διαβάζει μόνο το docs/matches.json.

Αποστολή γίνεται μόνο όταν υπάρχει η μεταβλητή περιβάλλοντος NTFY=1.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

NTFY_SERVER = "https://ntfy.sh"
TOPIC_PREFIX = "paokcal-x7q3"
SITE = "https://paokalendar.vercel.app/"
ATHENS = ZoneInfo("Europe/Athens")
KINDS = ("pre", "time", "result")
REMINDER_WINDOW = dt.timedelta(minutes=75)
MAX_PER_KIND = 8  # πάνω από τόσες ειδοποιήσεις μαζί μάλλον σημαίνει πρόβλημα στην πηγή

EMOJI = {
    "football": "⚽", "football-women": "⚽", "basketball": "🏀", "basketball-women": "🏀",
    "volley": "🏐", "volley-women": "🏐", "handball": "🤾", "handball-women": "🤾",
    "waterpolo": "🤽", "waterpolo-women": "🤽",
}
WEEKDAYS = ["Δευ", "Τρι", "Τετ", "Πεμ", "Παρ", "Σαβ", "Κυρ"]
MONTHS = ["Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαΐ", "Ιουν", "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ"]


def topic(section: str, kind: str) -> str:
    return f"{TOPIC_PREFIX}-{section}-{kind}"


def enabled() -> bool:
    return os.environ.get("NTFY") == "1"


def when_text(m: dict) -> str:
    d = dt.datetime.fromisoformat(m["start"]).astimezone(ATHENS)
    day = f"{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"
    return f"{day}, {d:%H:%M}" if m.get("timeKnown") else f"{day}, ώρα TBC"


def teams(m: dict, with_score: bool = False) -> str:
    mid = f" {m['score'].replace('-', '–')} " if with_score and m.get("score") else " – "
    return f"{m['home']}{mid}{m['away']}"


def send(section: str, kind: str, title: str, message: str) -> None:
    payload = {
        "topic": topic(section, kind),
        "title": title,
        "message": message,
        "click": f"{SITE}#/{section}",
    }
    if not enabled():
        print(f"  (χωρίς αποστολή) {payload['topic']}: {title} | {message}")
        return
    req = urllib.request.Request(NTFY_SERVER, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        print(f"  ειδοποίηση {payload['topic']}: {title}")
    except Exception as e:  # μια αποτυχημένη ειδοποίηση δεν σταματά την ενημέρωση
        print(f"  ! ntfy {payload['topic']}: {e}", file=sys.stderr)
    time.sleep(1)  # ευγενικό ρυθμό προς το ntfy.sh


def changes(previous: list[dict], current: list[dict], sections: set[str]) -> list[tuple[str, str, str, str]]:
    """Νέοι αγώνες, αλλαγές ημέρας/ώρας και νέα αποτελέσματα για τα τμήματα που ανανεώθηκαν."""
    now = dt.datetime.now(dt.timezone.utc)
    prev = {m["uid"]: m for m in previous}
    had = {m["section"] for m in previous}
    events: list[tuple[str, str, str, str]] = []
    for m in current:
        sec = m["section"]
        if sec not in sections or sec not in had:
            continue  # πρώτη φορά που βλέπουμε το τμήμα: καμία ειδοποίηση
        start = dt.datetime.fromisoformat(m["start"])
        emoji = EMOJI.get(sec, "")
        old = prev.get(m["uid"])
        details = ", ".join(x for x in (m.get("competition"), m.get("venue")) if x)
        if old is None:
            if start > now and not m.get("score"):
                events.append((sec, "time", f"{emoji} Νέος αγώνας: {teams(m)}",
                               f"{when_text(m)}" + (f". {details}" if details else "")))
            continue
        if start > now and not m.get("score") and (
                old["start"] != m["start"] or old.get("timeKnown") != m.get("timeKnown")):
            events.append((sec, "time", f"{emoji} Αλλαγή: {teams(m)}",
                           f"Τώρα: {when_text(m)} (ήταν {when_text(old)})"))
        if m.get("score") and not old.get("score") and now - start < dt.timedelta(days=3):
            events.append((sec, "result", f"{emoji} Τελικό: {teams(m, with_score=True)}",
                           m.get("competition", "") + (f", {m['round']}" if m.get("round") else "")))
    # Προστασία: αν μια πηγή αλλάξει μορφή, δεν θέλουμε δεκάδες ειδοποιήσεις.
    counts: dict[tuple[str, str], int] = {}
    for sec, kind, *_ in events:
        counts[(sec, kind)] = counts.get((sec, kind), 0) + 1
    kept = []
    for e in events:
        if counts[(e[0], e[1])] > MAX_PER_KIND:
            print(f"  ! παράλειψη {counts[(e[0], e[1])]} ειδοποιήσεων {e[0]}/{e[1]} (πολλές μαζί)", file=sys.stderr)
            continue
        kept.append(e)
    return kept


def send_changes(previous: list[dict], current: list[dict], sections: set[str]) -> None:
    for sec, kind, title, message in changes(previous, current, sections):
        send(sec, kind, title, message)


def reminders(matches_path: Path, state_path: Path) -> int:
    """Υπενθύμιση για αγώνες που ξεκινούν μέσα στα επόμενα 75 λεπτά, μία φορά για τον καθένα."""
    data = json.loads(matches_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    now = dt.datetime.now(dt.timezone.utc)
    sent = 0
    for m in data.get("matches", []):
        if not m.get("timeKnown") or m.get("score"):
            continue
        start = dt.datetime.fromisoformat(m["start"])
        key = f"{m['uid']}@{m['start']}"  # αν αλλάξει η ώρα, ξαναστέλνεται για τη νέα
        if not (now < start <= now + REMINDER_WINDOW) or key in state:
            continue
        local = start.astimezone(ATHENS)
        mins = max(1, round((start - now).total_seconds() / 60 / 5) * 5)
        sec = m["section"]
        details = ", ".join(x for x in (m.get("venue"), m.get("competition")) if x)
        send(sec, "pre", f"{EMOJI.get(sec, '')} Σε {mins} λεπτά: {teams(m)}",
             f"Στις {local:%H:%M}" + (f", {details}" if details else ""))
        state[key] = now.isoformat(timespec="minutes")
        sent += 1
    # Κρατάμε μόνο τις τελευταίες 3 μέρες.
    cutoff = now - dt.timedelta(days=3)
    state = {k: v for k, v in state.items() if dt.datetime.fromisoformat(v) > cutoff}
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Υπενθυμίσεις: {sent}")
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["reminders"]:
        here = Path(__file__).resolve().parent
        sys.exit(reminders(here / "docs" / "matches.json", here / ".state" / "reminded.json"))
    print(__doc__)
