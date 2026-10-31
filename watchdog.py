#!/usr/bin/env python3
"""Έλεγχος υγείας του PAOKalendar: βρίσκει τι έχει σταματήσει να δουλεύει και ειδοποιεί αμέσως.

Τρέχει μέσα στα workflows (python3 watchdog.py reminders | update) και ελέγχει:
    selftest   το /api/health?selftest=1 (εγγραφή συσκευής, βάση, κρυπτογράφηση ειδοποίησης)
    deploy     αν απέτυχε η τελευταία έκδοση της Vercel (π.χ. όριο εκδόσεων)
    data       αν τα δεδομένα (κλάδος data) έχουν να ενημερωθούν πάνω από 3 ώρες      (reminders)
    live:<id>  αγώνας με live σε εξέλιξη χωρίς να τρέχει η παρακολούθηση (live.yml)   (reminders)
    reminders  αν ο έλεγχος κάθε 15 λεπτά (reminders.yml) έχει να τρέξει πάνω από 40 λεπτά (update)

Για κάθε νέο πρόβλημα στέλνει ειδοποίηση στο θέμα «s:ops:live» (το ενεργοποιεί ο διαχειριστής από τη
σελίδα Ειδοποιήσεις, μετά από μία επίσκεψη στο #/admin) και κρατά ανοιχτό ένα issue «Πρόβλημα
λειτουργίας» (το GitHub στέλνει email). Όταν λυθούν όλα, κλείνει το issue και στέλνει «Λύθηκε».
Με DRY=1 μόνο τυπώνει τι θα έκανε.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request

import notify

REPO = os.environ.get("GITHUB_REPOSITORY", "GabrielChatzi/PAOK-calendar")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
DRY = os.environ.get("DRY") == "1"
TITLE = "Πρόβλημα λειτουργίας"
RAW = f"https://raw.githubusercontent.com/{REPO}/data/matches.json"
UA = "PAOKalendar watchdog (+https://paokalendar.vercel.app)"
TOPIC = "s:ops:live"

DATA_STALE = dt.timedelta(hours=3)
REMINDERS_STALE = dt.timedelta(minutes=40)
LIVE_GRACE = dt.timedelta(minutes=5)

# Ποια προβλήματα ελέγχει κάθε τρόπος: μόνο αυτά μπορεί να δηλώσει «λυμένα».
CHECKS = {"reminders": ("selftest", "deploy", "data", "live:"), "update": ("selftest", "deploy", "reminders")}


def http_json(url: str, method: str = "GET", body: dict | None = None, github: bool = False):
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if github:
        headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        if TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"
    data = json.dumps(body).encode() if body is not None else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8")
    return json.loads(text) if text.strip() else None


def gh(path: str, method: str = "GET", body: dict | None = None):
    return http_json(f"https://api.github.com/repos/{REPO}/{path}", method, body, github=True)


def when(t: dt.datetime) -> str:
    return t.astimezone(notify.ATHENS).strftime("%d/%m %H:%M")


# ---------------------------------------------------------------- έλεγχοι

def check_selftest() -> list[tuple[str, str]]:
    try:
        d = http_json(notify.SITE + "api/health?selftest=1")
    except Exception as e:
        return [("selftest", f"Ο server των ειδοποιήσεων δεν απαντά ({e}). Δεν αποθηκεύονται επιλογές ούτε φεύγουν ειδοποιήσεις.")]
    if not d or not d.get("ok"):
        bad = ", ".join(f"{k}: {v}" for k, v in (d or {}).get("checks", {}).items() if v != "ok") or "άγνωστο σφάλμα"
        return [("selftest", f"Ο αυτοέλεγχος των ειδοποιήσεων απέτυχε ({bad}). Μάλλον δεν αποθηκεύονται οι επιλογές των συσκευών.")]
    return []


def check_deploy() -> list[tuple[str, str]]:
    sha = gh("commits/main")["sha"]
    statuses = gh(f"commits/{sha}/statuses")
    vercel = next((s for s in statuses if "vercel" in (s.get("context") or "").lower()), None)
    if vercel and vercel.get("state") in ("failure", "error"):
        return [("deploy", f"Η τελευταία έκδοση στη Vercel απέτυχε: {vercel.get('description') or vercel['state']}. "
                           "Οι αλλαγές στον κώδικα δεν έχουν ανέβει στη σελίδα.")]
    return []


def load_matches() -> dict:
    return http_json(RAW + "?t=" + str(int(dt.datetime.now().timestamp())))


def check_data(data: dict, now: dt.datetime) -> list[tuple[str, str]]:
    stamps = []
    for v in (data.get("updated") or {}).values():
        try:
            stamps.append(dt.datetime.fromisoformat(v))
        except ValueError:
            pass
    if not stamps:
        return [("data", "Δεν βρέθηκε ώρα ενημέρωσης στο matches.json του κλάδου data.")]
    newest = max(stamps)
    if now - newest > DATA_STALE:
        return [("data", f"Το πρόγραμμα έχει να ενημερωθεί από {when(newest)}. Μάλλον δεν τρέχει το update.yml.")]
    return []


def live_running() -> bool:
    for status in ("in_progress", "queued"):
        runs = gh(f"actions/workflows/live.yml/runs?status={status}&per_page=5").get("workflow_runs", [])
        if runs:
            return True
    return False


def check_live(data: dict, now: dt.datetime) -> list[tuple[str, str]]:
    late = [m for m in data.get("matches", []) if notify.live_window(m, now)
            and dt.datetime.fromisoformat(m["start"]) + LIVE_GRACE <= now]
    if not late or live_running():
        return []
    return [(f"live:{m['nt']}", f"{notify.teams(m)} παίζεται από {when(dt.datetime.fromisoformat(m['start']))} "
                                "χωρίς να τρέχει η παρακολούθηση live: δεν φεύγουν live ειδοποιήσεις.") for m in late]


def check_reminders(now: dt.datetime) -> list[tuple[str, str]]:
    runs = gh("actions/workflows/reminders.yml/runs?status=success&per_page=1").get("workflow_runs", [])
    if not runs:
        return [("reminders", "Δεν βρέθηκε καμία επιτυχημένη εκτέλεση των υπενθυμίσεων.")]
    last = dt.datetime.fromisoformat(runs[0]["created_at"].replace("Z", "+00:00"))
    if now - last > REMINDERS_STALE:
        return [("reminders", f"Ο έλεγχος κάθε 15 λεπτά (υπενθυμίσεις, έναρξη live) έχει να τρέξει από {when(last)}. "
                              "Δες αν δουλεύει η δουλειά στο cron-job.org.")]
    return []


def problems(mode: str) -> list[tuple[str, str]]:
    now = dt.datetime.now(dt.timezone.utc)
    out: list[tuple[str, str]] = []
    steps = [check_selftest, check_deploy]
    if mode == "reminders":
        data = load_matches()
        steps += [lambda: check_data(data, now), lambda: check_live(data, now)]
    else:
        steps += [lambda: check_reminders(now)]
    for step in steps:
        try:
            out += step()
        except Exception as e:  # ένας έλεγχος που δεν μπόρεσε να γίνει δεν είναι πρόβλημα της εφαρμογής
            print(f"  ! έλεγχος {getattr(step, '__name__', '')}: {e}", file=sys.stderr)
    return out


# ---------------------------------------------------------------- issue και ειδοποιήσεις

def open_issue() -> dict | None:
    for issue in gh("issues?state=open&per_page=50"):
        if issue.get("title") == TITLE and "pull_request" not in issue:
            return issue
    return None


def keys_in(issue: dict | None) -> list[str]:
    m = re.search(r"<!-- ops: (.*?) -->", (issue or {}).get("body") or "")
    return [k for k in m.group(1).split(",") if k] if m else []


def checked(mode: str, key: str) -> bool:
    return any(key == c or (c.endswith(":") and key.startswith(c)) for c in CHECKS[mode])


def main(mode: str) -> int:
    found = problems(mode)
    issue = open_issue()
    prev = keys_in(issue)
    current = {k: text for k, text in found}
    # Ό,τι υπήρχε και δεν το ελέγχει αυτός ο τρόπος μένει ως έχει.
    remaining = {k: None for k in prev if not checked(mode, k)}
    remaining.update(current)
    new = [k for k in current if k not in prev]
    print("Προβλήματα: " + (", ".join(current) or "κανένα") + (f" (νέα: {', '.join(new)})" if new else ""))
    if DRY:
        for k, text in found:
            print(f"  [{k}] {text}")
        return 0

    for k in new:
        notify._push([TOPIC], "⚠️ PAOKalendar: κάτι δεν δουλεύει", current[k], "/#/notifications", tag=f"ops-{k}")

    if remaining:
        lines = [f"- **{k}**: {text}" for k, text in current.items()]
        lines += [f"- **{k}**: (από προηγούμενο έλεγχο)" for k in remaining if k not in current]
        body = ("Ο αυτόματος έλεγχος βρήκε προβλήματα. Το issue κλείνει μόνο του όταν λυθούν.\n\n"
                + "\n".join(lines) + f"\n\nΤελευταίος έλεγχος: {when(dt.datetime.now(dt.timezone.utc))} ({mode})\n\n"
                + f"<!-- ops: {','.join(remaining)} -->\n")
        if not issue:
            gh("issues", "POST", {"title": TITLE, "body": body})
        else:
            gh(f"issues/{issue['number']}", "PATCH", {"body": body})
            if new:
                gh(f"issues/{issue['number']}/comments", "POST", {"body": "Νέο πρόβλημα: " + ", ".join(new)})
    elif issue:
        gh(f"issues/{issue['number']}/comments", "POST", {"body": "Όλα δουλεύουν ξανά. Κλείνει αυτόματα."})
        gh(f"issues/{issue['number']}", "PATCH", {"state": "closed"})
        notify._push([TOPIC], "✅ PAOKalendar: όλα δουλεύουν ξανά", "Λύθηκαν: " + ", ".join(prev), "/#/notifications", tag="ops-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in CHECKS else "reminders"))
