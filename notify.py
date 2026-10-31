#!/usr/bin/env python3
"""Ειδοποιήσεις για τους αγώνες του ΠΑΟΚ μέσα στην εφαρμογή (web push).

Η εφαρμογή γράφει κάθε συσκευή σε θέματα, ώστε ο καθένας να διαλέγει τι θέλει:
    s:<τμήμα>:<είδος>    για όλους τους αγώνες ενός τμήματος
    m:<αγώνας>:<είδος>   για έναν μόνο αγώνα
Είδη: pre (υπενθύμιση περίπου μία ώρα πριν), time (νέος αγώνας ή αλλαγή ημέρας/ώρας),
live (έναρξη, γκολ/περίοδοι, τέλος· βλ. live.py), result (τελικό αποτέλεσμα).

Η αποστολή γίνεται από το /api/push της σελίδας (Vercel). Η ταυτότητα του GitHub Actions
αποδεικνύεται με το OIDC token του GitHub (χρειάζεται «permissions: id-token: write»).

Οι αλλαγές και τα αποτελέσματα στέλνονται από το build_calendars.py όταν ενημερώνεται το
πρόγραμμα. Οι υπενθυμίσεις στέλνονται από αυτό το script (python3 notify.py reminders),
που τρέχει κάθε 15 λεπτά και διαβάζει μόνο το docs/matches.json.

Αποστολή γίνεται μόνο όταν υπάρχει η μεταβλητή περιβάλλοντος PUSH=1.
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

SITE = "https://paokalendar.vercel.app/"
ATHENS = ZoneInfo("Europe/Athens")
KINDS = ("pre", "time", "live", "result")
# Η υπενθύμιση φεύγει στον πρώτο έλεγχο (κάθε 15 λεπτά) που απέχει το πολύ μία ώρα από την έναρξη·
# 2 λεπτά περιθώριο για ελέγχους που τρέχουν λίγο νωρίτερα από το τέταρτο.
REMINDER_WINDOW = dt.timedelta(minutes=62)
# Πόσο νωρίτερα ξεκινά η παρακολούθηση live, ώστε να «δει» τον αγώνα πριν αρχίσει.
LIVE_LEAD = dt.timedelta(minutes=50)
LIVE_SPAN = dt.timedelta(hours=3, minutes=30)
MAX_PER_KIND = 8  # πάνω από τόσες ειδοποιήσεις μαζί μάλλον σημαίνει πρόβλημα στην πηγή

EMOJI = {
    "football": "⚽", "football-women": "⚽", "basketball": "🏀", "basketball-women": "🏀",
    "volley": "🏐", "volley-women": "🏐", "handball": "🤾", "handball-women": "🤾",
    "waterpolo": "🤽", "waterpolo-women": "🤽", "futsal": "🥅",
}
# Περίπου πόση ώρα κρατά ένας αγώνας ανά τμήμα (λεπτά), μαζί με τα διαλείμματα. Από εκεί και πέρα
# περιμένουμε το τελικό αποτέλεσμα και ανανεώνουμε το πρόγραμμα πιο συχνά (βλ. reminders()).
DURATION = {
    "football": 115, "football-women": 115, "basketball": 120, "basketball-women": 115,
    "volley": 130, "volley-women": 130, "handball": 95, "handball-women": 95,
    "waterpolo": 80, "waterpolo-women": 80, "futsal": 95,
}
RESULT_WAIT = dt.timedelta(hours=6)
WEEKDAYS = ["Δευ", "Τρι", "Τετ", "Πεμ", "Παρ", "Σαβ", "Κυρ"]
MONTHS = ["Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαΐ", "Ιουν", "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ"]


def enabled() -> bool:
    return os.environ.get("PUSH") == "1"


def when_text(m: dict) -> str:
    d = dt.datetime.fromisoformat(m["start"]).astimezone(ATHENS)
    day = f"{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"
    return f"{day}, {d:%H:%M}" if m.get("timeKnown") else f"{day}, ώρα TBC"


def teams(m: dict, with_score: bool = False) -> str:
    mid = f" {m['score'].replace('-', '–')} " if with_score and m.get("score") else " – "
    return f"{m['home']}{mid}{m['away']}"


_oidc: dict = {}


def _oidc_token() -> str | None:
    """Token ταυτότητας του GitHub Actions για το /api/push (ισχύει λίγα λεπτά, κρατιέται 4)."""
    url, req_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL"), os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not url or not req_token:
        return None
    if _oidc.get("token") and time.time() - _oidc["at"] < 240:
        return _oidc["token"]
    req = urllib.request.Request(url + "&audience=paokalendar", headers={"Authorization": f"Bearer {req_token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        _oidc.update(token=json.loads(r.read())["value"], at=time.time())
    return _oidc["token"]


def _push(topics: list[str], title: str, message: str, url: str, tag: str | None = None,
          quiet: bool = False) -> None:
    """Ειδοποίηση web push σε όσες συσκευές έχουν γραφτεί σε κάποιο από τα θέματα (μία φορά στην καθεμία)."""
    if not enabled():
        print(f"  (χωρίς αποστολή) push {','.join(topics)}: {title} | {message}")
        return
    try:
        token = _oidc_token()
        if not token:
            print("  ! push: λείπει το OIDC token (permissions: id-token: write)", file=sys.stderr)
            return
        body = {"topics": topics, "title": title, "body": message, "url": url, "tag": tag, "quiet": quiet}
        req = urllib.request.Request(SITE + "api/push", data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read())
        print(f"  push {','.join(topics)}: {title} → {res.get('sent', 0)}/{res.get('matched', 0)}")
        for err in res.get("errors") or []:
            print(f"    ! {err}", file=sys.stderr)
    except Exception as e:  # μια αποτυχημένη ειδοποίηση δεν σταματά την υπόλοιπη δουλειά
        print(f"  ! push {','.join(topics)}: {e}", file=sys.stderr)


def send(section: str, kind: str, title: str, message: str, match: dict | None = None,
         to_match: bool = True, also_match_kinds: tuple[str, ...] = (), tag: str | None = None) -> None:
    """Στέλνει σε όσους ακολουθούν το τμήμα και, αν δοθεί αγώνας, σε όσους ακολουθούν τον αγώνα.

    to_match: αν πηγαίνει και στο ίδιο είδος του αγώνα.
    also_match_kinds: επιπλέον είδη του αγώνα (π.χ. το τελικό από το live πηγαίνει και στο «result»).
    """
    has_match = match is not None and bool(match.get("nt"))
    kinds = ((kind,) if to_match else ()) + tuple(also_match_kinds) if has_match else ()
    topics = [f"s:{section}:{kind}"] + [f"m:{match['nt']}:{k}" for k in kinds]
    url = f"/#/m/{match['nt']}" if has_match else f"/#/{section}"
    # Ίδιο tag για το ίδιο γεγονός: αν φτάσει δύο φορές, η δεύτερη αντικαθιστά την πρώτη.
    # Το τελικό μπορεί να έρθει και από το live.py και από την ενημέρωση (ίδιο tag «<αγώνας>-result»):
    # η δεύτερη φορά αντικαθιστά την πρώτη χωρίς νέο ήχο.
    tag = tag or (f"{match['nt']}-{kind}" if has_match and kind != "live" else None)
    _push(list(dict.fromkeys(topics)), title, message, url, tag, quiet=kind == "result")


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
        # Το τελικό πηγαίνει πάντα και σε όσους ακολουθούν τον αγώνα, ακόμα κι αν το έστειλε ήδη το
        # live.py (π.χ. αν δεν έτρεχε): με το ίδιο tag, η συσκευή κρατά μία ειδοποίηση.
        send(sec, kind, title, message, match=m)


def live_window(m: dict, now: dt.datetime) -> bool:
    """Αν ένας αγώνας με live πρέπει να παρακολουθείται τώρα."""
    if not m.get("live") or not m.get("timeKnown") or m.get("score"):
        return False
    start = dt.datetime.fromisoformat(m["start"])
    return start - LIVE_LEAD <= now <= start + LIVE_SPAN


def awaiting_result(m: dict, now: dt.datetime) -> bool:
    """Αν ένας αγώνας πρέπει να έχει τελειώσει αλλά δεν έχουμε ακόμα το αποτέλεσμα."""
    if not m.get("timeKnown") or m.get("score"):
        return False
    start = dt.datetime.fromisoformat(m["start"])
    end = start + dt.timedelta(minutes=DURATION.get(m["section"], 120) - 10)
    return end <= now <= start + RESULT_WAIT


def reminders(matches_path: Path, state_path: Path) -> int:
    """Υπενθύμιση για αγώνες που ξεκινούν μέσα στην επόμενη ώρα, μία φορά για τον καθένα.

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
    waiting = [m for m in data.get("matches", []) if awaiting_result(m, now)]
    if waiting:
        print("Αναμένεται αποτέλεσμα: " + ", ".join(teams(m) for m in waiting))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"live={1 if live else 0}\n")
            f.write(f"refresh={1 if waiting else 0}\n")
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["reminders"]:
        here = Path(__file__).resolve().parent
        sys.exit(reminders(here / "docs" / "matches.json", here / ".state" / "reminded.json"))
    print(__doc__)
