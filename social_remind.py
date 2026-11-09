#!/usr/bin/env python3
"""Υπενθυμίσεις στον διαχειριστή για τα social: πότε και τι να ανεβάσει.

Διαβάζει το plan.json του κλάδου social (το γράφει το social.yml) και, στην ώρα κάθε post, story
ή Reel, στέλνει ειδοποίηση στο θέμα «s:ops:pre» (το ανοίγει ο διαχειριστής από τη σελίδα
Ειδοποιήσεις → Διαχειριστής → «Υπενθυμίσεις social»). Πατώντας την ανοίγει η σελίδα /social/ με
τις εικόνες και τη λεζάντα για αντιγραφή.

Τα αποτελέσματα ημέρας φεύγουν όταν μπουν όλα τα σκορ (ως 5 ώρες μετά την ώρα του πλάνου).
Τρέχει κάθε 15 λεπτά από το reminders.yml:  python3 social_remind.py plan.json .state/social.json
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import notify

TOPIC = "s:ops:pre"
EARLY = dt.timedelta(minutes=5)       # ο έλεγχος τρέχει κάθε 15': να μη φύγει πολύ αργά
LATE = dt.timedelta(minutes=50)       # μετά από τόσο, για post/story χωρίς αναμονή, δεν στέλνεται πια
RESULTS_LATE = dt.timedelta(hours=5)  # τα αποτελέσματα περιμένουν τα σκορ
KIND = {"post": "post", "story": "story", "reel": "Reel"}
ICON = {"post": "🖼️", "story": "📱", "reel": "🎬"}


def key(it: dict) -> str:
    return f"{it['day']}-{it['time'].replace(':', '')}-{it['what']}"


def ready(it: dict) -> bool:
    return it["type"] == "reel" or (bool(it.get("images")) and not it.get("missing"))


def message(it: dict) -> tuple[str, str]:
    title = f"{ICON.get(it['type'], '📣')} Ώρα για {KIND.get(it['type'], it['type'])}: {it['title']}"
    n = len(it.get("images") or [])
    parts = []
    if it.get("how"):
        parts.append(it["how"])
    elif n:
        parts.append(f"{n} εικόν{'α' if n == 1 else 'ες'}" + (", λεζάντα έτοιμη" if it.get("caption") else ""))
    if it.get("note"):
        parts.append(it["note"])
    return title, " ".join(p.rstrip(".") + "." for p in parts + ["Πάτα για εικόνες και λεζάντα"])


def due(items: list[dict], sent: dict, now: dt.datetime) -> list[dict]:
    out = []
    for it in items:
        at = dt.datetime.fromisoformat(f"{it['day']}T{it['time']}").replace(tzinfo=notify.ATHENS)
        late = RESULTS_LATE if it.get("missing") is not None else LATE
        if key(it) in sent or not (at - EARLY <= now <= at + late) or not ready(it):
            continue
        out.append(it)
    return out


def main(plan_path: Path, state_path: Path, now: dt.datetime | None = None) -> int:
    now = now or dt.datetime.now(notify.ATHENS)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    sent = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    for it in due(plan.get("items", []), sent, now):
        title, body = message(it)
        notify._push([TOPIC], title, body, f"/social/#{key(it)}", tag=f"social-{key(it)}", once=f"social-{key(it)}")
        sent[key(it)] = now.isoformat(timespec="minutes")
    cutoff = now - dt.timedelta(days=10)
    sent = {k: v for k, v in sent.items() if dt.datetime.fromisoformat(v) > cutoff}
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(sent, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
