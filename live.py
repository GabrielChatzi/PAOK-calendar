#!/usr/bin/env python3
"""Παρακολουθεί τους αγώνες του ΠΑΟΚ σε εξέλιξη και στέλνει live ειδοποιήσεις.

Τρέχει ως μία μακριά εργασία στο GitHub Actions (workflow live.yml), που ξεκινά λίγο πριν
από έναν αγώνα με live και τελειώνει όταν δεν μένει κανένας αγώνας να παρακολουθήσει.
Κάθε λεπτό διαβάζει το ζωντανό σκορ και στέλνει ειδοποίηση για:
    ποδόσφαιρο (ESPN):     έναρξη, κάθε γκολ, ημίχρονο, τελικό
    μπάσκετ EuroCup:       έναρξη, τέλος κάθε περιόδου, τελικό
    πόλο (ΚΟΕ, European Aquatics μέσω api/live.js): έναρξη, τέλος κάθε περιόδου, τελικό

Οι ειδοποιήσεις πηγαίνουν στο θέμα «live» του τμήματος και στο θέμα του αγώνα.
Η πρώτη ανάγνωση κάθε αγώνα είναι μόνο σημείο αναφοράς: αν η εργασία ξεκινήσει στη μέση
του αγώνα, δεν στέλνει παλιά γεγονότα.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import notify

POLL_SECONDS = 60
MAX_RUNTIME = dt.timedelta(hours=5, minutes=20)
IDLE_EXIT = dt.timedelta(minutes=20)
UA = "Mozilla/5.0 (PAOKalendar live; +https://paokalendar.vercel.app)"


def get_json(url: str) -> dict | None:
    """JSON από μια πηγή· None αν η απάντηση είναι κενή (π.χ. το EuroCup πριν από το τζάμπολ)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8-sig").strip()
    return json.loads(body) if body else None


def load_matches() -> list[dict]:
    """Τα δεδομένα από τη σελίδα (πάντα τα τελευταία)· αλλιώς από το repo."""
    try:
        return (get_json(notify.SITE + "matches.json?t=" + str(int(time.time()))) or {})["matches"]
    except Exception as e:
        print(f"  ! matches.json από τη σελίδα: {e}", file=sys.stderr)
        path = Path(__file__).resolve().parent / "docs" / "matches.json"
        return json.loads(path.read_text(encoding="utf-8"))["matches"]


# ---------------------------------------------------------------- πηγές

def espn_state(live: dict) -> dict:
    url = (f"https://site.api.espn.com/apis/site/v2/sports/soccer/{live['league']}"
           f"/summary?event={live['id']}")
    data = get_json(url)
    if not data:
        raise ValueError("κενή απάντηση")
    comp = data["header"]["competitions"][0]
    status = comp["status"]["type"]
    score = {c["homeAway"]: int(c.get("score") or 0) for c in comp["competitors"]}
    home_id = next((c["team"]["id"] for c in comp["competitors"] if c["homeAway"] == "home"), None)
    goals = []
    for e in data.get("keyEvents") or []:
        if not e.get("scoringPlay"):
            continue
        players = [p.get("athlete", {}).get("displayName", "") for p in e.get("participants") or []]
        kind = (e.get("type") or {}).get("type", "")
        note = " (πέναλτι)" if "penalty" in kind else " (αυτογκόλ)" if "own" in kind else ""
        goals.append({
            "id": str(e.get("id")),
            "clock": (e.get("clock") or {}).get("displayValue", ""),
            "team": (e.get("team") or {}).get("displayName", ""),
            "home": (e.get("team") or {}).get("id") == home_id,
            "text": (players[0] if players and players[0] else e.get("shortText", "")) + note,
        })
    return {
        "state": status.get("state", "pre"),  # pre / in / post
        "home": score.get("home", 0), "away": score.get("away", 0),
        "halftime": status.get("name") == "STATUS_HALFTIME",
        "detail": status.get("shortDetail") or status.get("detail") or "",
        "goals": goals,
    }


def euroleague_state(live: dict) -> dict:
    """Σκορ από το live.euroleague.net. Πριν από το τζάμπολ η απάντηση είναι κενή (= δεν ξεκίνησε).

    «Quarter» είναι η τρέχουσα περίοδος· στα διαλείμματα γίνεται 0. Ποια περίοδος τελείωσε
    το βρίσκει η track_periods() από την τελευταία περίοδο που είδε.
    """
    url = f"https://live.euroleague.net/api/Header?gamecode={live['code']}&seasoncode={live['season']}"
    h = get_json(url) or {}

    def num(x):
        try:
            return int(str(x or "").strip())
        except ValueError:
            return 0
    a, b = num(h.get("ScoreA")), num(h.get("ScoreB"))
    quarter = num(h.get("Quarter"))
    if h.get("Live"):
        state = "in"
    elif a or b:
        state = "post"
    else:
        state = "pre"
    clock = str(h.get("RemainingPartialTime") or "").strip()
    detail = f"{quarter}η περίοδος {clock}".strip() if quarter >= 1 else ("Διάλειμμα" if state == "in" else "")
    return {"state": state, "home": a, "away": b, "quarter": quarter, "detail": detail}


def track_periods(old: dict | None, new: dict) -> None:
    """Συμπληρώνει «seen» (τελευταία περίοδος σε εξέλιξη) και «done» (περίοδοι που τελείωσαν).

    Στο διάλειμμα (περίοδος 0) τελείωσε η τελευταία που είδαμε. Αν η παρακολούθηση ξεκινήσει
    μέσα σε διάλειμμα, δεν ξέρουμε ποια ήταν: done = None μέχρι να αρχίσει η επόμενη.
    """
    q = new.get("quarter", 0)
    seen = q or (old or {}).get("seen", 0)
    new["seen"] = seen
    if q >= 1:
        new["done"] = q - 1
    elif new["state"] == "in":
        new["done"] = seen or None
    else:
        new["done"] = (old or {}).get("done")


def waterpolo_state(live: dict) -> dict:
    """Πόλο από το api/live.js της σελίδας (ΚΟΕ ή European Aquatics, σύστημα Microplus).

    Η απάντηση έχει ήδη «done» (περίοδοι που τελείωσαν) και «quarter» (η τρέχουσα).
    """
    st = get_json(notify.SITE + "api/live?" + urllib.parse.urlencode(live)) or {}
    if st.get("state") not in ("pre", "in", "post"):
        raise ValueError(st.get("error") or "άγνωστη απάντηση")
    q = st.get("quarter") or 0
    if live.get("src") == "dp":
        st["detail"] = f"{q}ο σετ {st.get('clock') or ''}".strip() if st["state"] == "in" else ""
        return st
    st["detail"] = (f"{q}η περίοδος {st.get('clock') or ''}".strip() if q else "Διάλειμμα") if st["state"] == "in" else ""
    return st


SOURCES = {"espn": espn_state, "euroleague": euroleague_state, "koe": waterpolo_state, "ea": waterpolo_state,
           "dp": waterpolo_state, "gs": waterpolo_state}
PERIOD_SOURCES = ("euroleague", "koe", "ea", "dp", "gs")


# ---------------------------------------------------------------- γεγονότα

def score_text(m: dict, st: dict) -> str:
    return f"{m['home']} {st['home']}–{st['away']} {m['away']}"


def ordinal_period(q: int) -> str:
    return f"{q}ης περιόδου" if q <= 4 else "παράτασης"


def events(m: dict, old: dict | None, new: dict) -> list[tuple[str, str]]:
    """(τίτλος, κείμενο) για ό,τι άλλαξε από την προηγούμενη ανάγνωση. Το τελικό είναι πάντα τελευταίο."""
    if old is None:
        return []  # πρώτη ανάγνωση: μόνο σημείο αναφοράς
    e = notify.EMOJI.get(m["section"], "")
    out = []
    comp = m.get("competition", "")
    if old["state"] == "pre" and new["state"] == "in":
        out.append((f"{e} Ξεκίνησε: {m['home']} – {m['away']}", comp))
    if new["state"] in ("in", "post") and m["live"]["src"] == "espn":
        seen = {g["id"] for g in old.get("goals", [])}
        # Αν έρθουν πολλά γκολ μαζί, κάθε ειδοποίηση δείχνει το σκορ τη στιγμή εκείνου του γκολ.
        running = {"home": old.get("home", 0), "away": old.get("away", 0)}
        for g in new.get("goals", []):
            if g["id"] in seen:
                continue
            running["home" if g.get("home") else "away"] += 1
            if running["home"] > new["home"] or running["away"] > new["away"]:
                running = {"home": new["home"], "away": new["away"]}
            paok = "PAOK" in g["team"].upper()
            title = f"{e} ΓΚΟΛ{' ΤΟΥ ΠΑΟΚ' if paok else ''}! {score_text(m, running)}"
            out.append((title, " ".join(x for x in (g["clock"], g["text"]) if x)))
        if new.get("halftime") and not old.get("halftime"):
            out.append((f"{e} Ημίχρονο: {score_text(m, new)}", comp))
    if m["live"]["src"] == "dp" and new["state"] == "in" and old["state"] == "in":
        # Βόλεϊ: τέλος κάθε σετ (όχι όταν τελειώνει ο αγώνας· τότε έρχεται το «Τελικό»).
        d_old, d_new = old.get("done") or 0, new.get("done") or 0
        sets = (new.get("quarters") or [])
        if d_new > d_old:
            pts = sets[d_new - 1] if len(sets) >= d_new else None
            detail = f" ({pts['home']}–{pts['away']})" if pts else ""
            out.append((f"{e} Τέλος {d_new}ου σετ{detail}: {m['home']} {new['home']}–{new['away']} {m['away']}", comp))
    elif m["live"]["src"] in PERIOD_SOURCES and new["state"] == "in" and old["state"] == "in":
        d_old, d_new = old.get("done"), new.get("done")
        waterpolo = m["live"]["src"] in ("koe", "ea")
        # Μετά την 4η, αν το σκορ δεν είναι ισόπαλο, έρχεται το «Τελικό» αντί για «Τέλος περιόδου».
        if d_old is not None and d_new is not None and d_new > d_old and not (d_new >= 4 and new["home"] != new["away"]):
            what = ("Ημίχρονο" if d_new == 2 else
                    ("Ισοπαλία, πάμε στα πέναλτι" if waterpolo else "Ισοπαλία, πάμε παράταση") if d_new == 4
                    else f"Τέλος {ordinal_period(d_new)}")
            out.append((f"{e} {what}: {score_text(m, new)}", comp))
    if old["state"] != "post" and new["state"] == "post":
        out.append((f"{e} Τελικό: {score_text(m, new)}", comp))
    return out


# ---------------------------------------------------------------- κύριο

def main() -> int:
    started = dt.datetime.now(dt.timezone.utc)
    upcoming = [m for m in load_matches() if m.get("live") and notify.live_window(m, started)]
    print("Αγώνες για παρακολούθηση: " + (", ".join(f"{m['home']} – {m['away']}" for m in upcoming) or "κανένας ακόμα"))
    states: dict[str, dict] = {}
    idle_since: dt.datetime | None = None
    while True:
        now = dt.datetime.now(dt.timezone.utc)
        if now - started > MAX_RUNTIME:
            print("Τέλος χρόνου εργασίας.")
            break
        matches = load_matches()
        watch = [m for m in matches if m.get("live") and (
            notify.live_window(m, now) or states.get(m["uid"], {}).get("state") == "in")]
        if not watch:
            idle_since = idle_since or now
            if now - idle_since > IDLE_EXIT:
                print("Κανένας αγώνας σε εξέλιξη· τέλος.")
                break
        else:
            idle_since = None
        for m in watch:
            src = SOURCES.get(m["live"].get("src"))
            if not src:
                continue
            try:
                new = src(m["live"])
            except Exception as e:
                print(f"  ! {m['home']} – {m['away']}: {e}", file=sys.stderr)
                continue
            old = states.get(m["uid"])
            if m["live"]["src"] == "euroleague":
                track_periods(old, new)
            # Το «Τελικό» μόνο αν το δούμε σε δύο συνεχόμενες αναγνώσεις: οι πηγές δείχνουν καμιά
            # φορά για λίγο τέλος αγώνα σε διάλειμμα (π.χ. η ΚΟΕ μετά την 3η περίοδο).
            if new["state"] == "post" and old and old["state"] != "post" and not old.get("post_seen"):
                new = dict(old, post_seen=True)
            for title, message in events(m, old, new):
                final = old is not None and old["state"] != "post" and new["state"] == "post" and "Τελικό" in title
                # Το τελικό πηγαίνει και στο θέμα «result» του αγώνα.
                notify.send(m["section"], "live", title, message, match=m,
                            also_match_kinds=("result",) if final else (),
                            tag=f"{m['nt']}-result" if final else None)
            if old is None or (old["state"], old["home"], old["away"]) != (new["state"], new["home"], new["away"]):
                print(f"{now:%H:%M} {m['home']} – {m['away']}: {new['state']} {new['home']}-{new['away']} {new.get('detail', '')}")
            states[m["uid"]] = new
        time.sleep(POLL_SECONDS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
