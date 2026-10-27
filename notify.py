#!/usr/bin/env python3
"""Ειδοποιήσεις ntfy για τους αγώνες του ΠΑΟΚ.

Κάθε τμήμα έχει θέματα (topics) στο ntfy.sh, ώστε ο καθένας να διαλέγει τι θέλει:
    <PREFIX>-<τμήμα>-pre     υπενθύμιση περίπου μία ώρα πριν από τον αγώνα
    <PREFIX>-<τμήμα>-time    νέος αγώνας στο πρόγραμμα ή αλλαγή ημέρας/ώρας
    <PREFIX>-<τμήμα>-live    έναρξη, γκολ/περίοδοι, τέλος (μόνο όπου υπάρχει live, βλ. live.py)
    <PREFIX>-<τμήμα>-result  τελικό αποτέλεσμα

Επιπλέον, κάθε αγώνας έχει δικά του θέματα, για όποιον θέλει ειδοποιήσεις μόνο για ένα ματς:
    <PREFIX>-m-<id>          όλα τα παραπάνω για τον αγώνα αυτό
    <PREFIX>-m-<id>-<είδος>  μόνο ένα είδος (pre, time, live, result)

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
KINDS = ("pre", "time", "live", "result")
REMINDER_WINDOW = dt.timedelta(minutes=75)
# Πόσο νωρίτερα ξεκινά η παρακολούθηση live, ώστε να «δει» τον αγώνα πριν αρχίσει.
LIVE_LEAD = dt.timedelta(minutes=50)
LIVE_SPAN = dt.timedelta(hours=3, minutes=30)
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


def match_topic(m: dict, kind: str | None = None) -> str:
    return f"{TOPIC_PREFIX}-m-{m['nt']}" + (f"-{kind}" if kind else "")


def enabled() -> bool:
    return os.environ.get("NTFY") == "1"


def when_text(m: dict) -> str:
    d = dt.datetime.fromisoformat(m["start"]).astimezone(ATHENS)
    day = f"{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"
    return f"{day}, {d:%H:%M}" if m.get("timeKnown") else f"{day}, ώρα TBC"


def teams(m: dict, with_score: bool = False) -> str:
    mid = f" {m['score'].replace('-', '–')} " if with_score and m.get("score") else " – "
    return f"{m['home']}{mid}{m['away']}"


def _post(topic_name: str, title: str, message: str, click: str, tags: list[str] | None = None) -> None:
    payload = {"topic": topic_name, "title": title, "message": message, "click": click}
    if tags:
        payload["tags"] = tags
    if not enabled():
        print(f"  (χωρίς αποστολή) {topic_name}: {title} | {message}")
        return
    req = urllib.request.Request(NTFY_SERVER, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        print(f"  ειδοποίηση {topic_name}: {title}")
    except Exception as e:  # μια αποτυχημένη ειδοποίηση δεν σταματά την υπόλοιπη δουλειά
        print(f"  ! ntfy {topic_name}: {e}", file=sys.stderr)
    time.sleep(1)  # ευγενικός ρυθμός προς το ntfy.sh


def send(section: str, kind: str, title: str, message: str, match: dict | None = None,
         to_match: bool = True, also_match_kinds: tuple[str, ...] = (), tags: list[str] | None = None) -> None:
    """Στέλνει στο θέμα του τμήματος και, αν δοθεί αγώνας, και στα θέματα του αγώνα.

    also_match_kinds: επιπλέον θέματα του αγώνα (π.χ. το τελικό από το live πηγαίνει και στο «result»).
    """
    click = f"{SITE}#/{section}"
    _post(topic(section, kind), title, message, click, tags)
    if match is None or not match.get("nt"):
        return
    click = f"{SITE}#/m/{match['nt']}"
    kinds = ((kind,) if to_match else ()) + tuple(also_match_kinds)
    if to_match:
        _post(match_topic(match), title, message, click, tags)
    for k in kinds:
        _post(match_topic(match, k), title, message, click, tags)


def changes(previous: list[dict], current: list[dict], sections: set[str]) -> list[tuple]:
    """Νέοι αγώνες, αλλαγές ημέρας/ώρας και νέα αποτελέσματα για τα τμήματα που ανανεώθηκαν.

    Επιστρέφει (τμήμα, είδος, τίτλος, κείμενο, αγώνας).
    """
    now = dt.datetime.now(dt.timezone.utc)
    prev = {m["uid"]: m for m in previous}
    had = {m["section"] for m in previous}
    events: list[tuple] = []
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
                               f"{when_text(m)}" + (f". {details}" if details else ""), m))
            continue
        if start > now and not m.get("score") and (
                old["start"] != m["start"] or old.get("timeKnown") != m.get("timeKnown")):
            events.append((sec, "time", f"{emoji} Αλλαγή: {teams(m)}",
                           f"Τώρα: {when_text(m)} (ήταν {when_text(old)})", m))
        if m.get("score") and not old.get("score") and now - start < dt.timedelta(days=3):
            events.append((sec, "result", f"{emoji} Τελικό: {teams(m, with_score=True)}",
                           m.get("competition", "") + (f", {m['round']}" if m.get("round") else ""), m))
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
    for sec, kind, title, message, m in changes(previous, current, sections):
        # Για αγώνες με live, το τελικό στο θέμα του αγώνα το στέλνει ήδη το live.py.
        to_match = not (kind == "result" and m.get("live"))
        send(sec, kind, title, message, match=m, to_match=to_match)


def live_window(m: dict, now: dt.datetime) -> bool:
    """Αν ένας αγώνας με live πρέπει να παρακολουθείται τώρα."""
    if not m.get("live") or not m.get("timeKnown") or m.get("score"):
        return False
    start = dt.datetime.fromisoformat(m["start"])
    return start - LIVE_LEAD <= now <= start + LIVE_SPAN


def reminders(matches_path: Path, state_path: Path) -> int:
    """Υπενθύμιση για αγώνες που ξεκινούν μέσα στα επόμενα 75 λεπτά, μία φορά για τον καθένα.

    Γράφει επίσης live=1 στο GITHUB_OUTPUT όταν πρέπει να ξεκινήσει η παρακολούθηση live.
    """
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
             f"Στις {local:%H:%M}" + (f", {details}" if details else ""), match=m)
        state[key] = now.isoformat(timespec="minutes")
        sent += 1
    # Κρατάμε μόνο τις τελευταίες 3 μέρες.
    cutoff = now - dt.timedelta(days=3)
    state = {k: v for k, v in state.items() if dt.datetime.fromisoformat(v) > cutoff}
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Υπενθυμίσεις: {sent}")

    live = [m for m in data.get("matches", []) if live_window(m, now)]
    if live:
        print("Αγώνες για live: " + ", ".join(teams(m) for m in live))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"live={1 if live else 0}\n")
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["reminders"]:
        here = Path(__file__).resolve().parent
        sys.exit(reminders(here / "docs" / "matches.json", here / ".state" / "reminded.json"))
    print(__doc__)
