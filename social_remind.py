#!/usr/bin/env python3
"""Υπενθυμίσεις στον διαχειριστή για τα social: πότε και τι να ανεβάσει.

Διαβάζει το plan.json του κλάδου social (το γράφει το social.yml) και, στην ώρα κάθε post, story
ή Reel, στέλνει ειδοποίηση στο θέμα «s:ops:pre» (το ανοίγει ο διαχειριστής από τη σελίδα
Ειδοποιήσεις → Διαχειριστής → «Υπενθυμίσεις social»). Πατώντας την ανοίγει η σελίδα /social/ με
τις εικόνες και τη λεζάντα για αντιγραφή.

Τα αποτελέσματα ημέρας φεύγουν όταν μπουν όλα τα σκορ (ως 5 ώρες μετά την ώρα του πλάνου).

Αλλαγές μετά την ανάρτηση: τα post προγράμματος (κανονικό και ακαδημιών) έχουν «track» και «lines» (μία
γραμμή ανά αγώνα). Όταν φύγει η υπενθύμιση κρατάμε τις γραμμές· αν ως την έναρξη του τελευταίου αγώνα
(«until») αλλάξει κάποια (ώρα, μέρα, γήπεδο, νέος ή αναβληθείς αγώνας), έρχεται ειδοποίηση «Άλλαξε το
πρόγραμμα» με το τι άλλαξε, για διορθωμένο story ή επεξεργασία του post με τη νέα εικόνα.
Τρέχει κάθε 15 λεπτά από το reminders.yml:  python3 social_remind.py plan.json .state/social.json
"""
from __future__ import annotations

import datetime as dt
import hashlib
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


def changes(items: list[dict], tracked: dict, now: dt.datetime) -> list[tuple[dict, list[str], list[str]]]:
    """Post προγράμματος που έχουν ήδη ανέβει και των οποίων οι αγώνες άλλαξαν: (item, νέες, παλιές γραμμές)."""
    out = []
    for it in items:
        old = tracked.get(it.get("track") or "")
        if not old or not it.get("lines") or now >= dt.datetime.fromisoformat(old["until"]):
            continue
        new_l, old_l = it["lines"], old["lines"]
        added = [x for x in new_l if x not in old_l]
        gone = [x for x in old_l if x not in new_l]
        if added or gone:
            out.append((it, added, gone))
    return out


def change_message(it: dict, added: list[str], gone: list[str]) -> tuple[str, str]:
    title = "⚠️ Άλλαξε το " + it["title"][0].lower() + it["title"][1:]
    parts = [f"Τώρα: {x}" for x in added[:3]]
    if not added:
        parts = [f"Βγήκε: {x}" for x in gone[:3]]
    more = len(added) - 3 if added else len(gone) - 3
    if more > 0:
        parts.append(f"και {more} ακόμα")
    return title, ". ".join(parts) + ". Πάτα για τη νέα εικόνα"


def main(plan_path: Path, state_path: Path, now: dt.datetime | None = None) -> int:
    now = now or dt.datetime.now(notify.ATHENS)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    sent = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    tracked = sent.pop("_tracked", {})
    items = plan.get("items", [])
    for it, added, gone in changes(items, tracked, now):
        title, body = change_message(it, added, gone)
        tag = f"social-change-{it['track']}"
        notify._push([TOPIC], title, body, f"/social/#{key(it)}", tag=tag,
                     once=f"{tag}-{hashlib.sha1('|'.join(it['lines']).encode()).hexdigest()[:10]}")
        tracked[it["track"]]["lines"] = it["lines"]
    for it in due(items, sent, now):
        title, body = message(it)
        notify._push([TOPIC], title, body, f"/social/#{key(it)}", tag=f"social-{key(it)}", once=f"social-{key(it)}")
        sent[key(it)] = now.isoformat(timespec="minutes")
        if it.get("track") and it.get("lines") and it.get("until"):
            tracked[it["track"]] = {"lines": it["lines"], "until": it["until"]}
    cutoff = now - dt.timedelta(days=10)
    sent = {k: v for k, v in sent.items() if dt.datetime.fromisoformat(v) > cutoff}
    sent["_tracked"] = {k: v for k, v in tracked.items() if dt.datetime.fromisoformat(v["until"]) > now}
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(sent, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
