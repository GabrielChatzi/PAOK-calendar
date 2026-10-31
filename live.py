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

POLL_SECONDS = 20  # οι πηγές (και το CDN του api/live.js, 15'') αντέχουν· το τελικό φεύγει σε ~40''
FAIL_ALERT = 15   # τόσες συνεχόμενες αποτυχίες μιας πηγής (~5') → ειδοποίηση λειτουργίας
MAX_RUNTIME = dt.timedelta(hours=5, minutes=20)
IDLE_EXIT = dt.timedelta(minutes=20)
UA = "Mozilla/5.0 (PAOKalendar live; +https://paokalendar.vercel.app)"


def get_json(url: str) -> dict | None:
    """JSON από μια πηγή· None αν η απάντηση είναι κενή (π.χ. το EuroCup πριν από το τζάμπολ)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8-sig").strip()
    return json.loads(body) if body else None


RAW = "https://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/data/matches.json"


def load_matches() -> list[dict]:
    """Τα τελευταία δεδομένα από το GitHub (ενημερώνονται χωρίς νέα έκδοση της Vercel)· αλλιώς από τη
    σελίδα ή το repo."""
    for url in (RAW + "?t=" + str(int(time.time())), notify.SITE + "matches.json?t=" + str(int(time.time()))):
        try:
            return (get_json(url) or {})["matches"]
        except Exception as e:
            print(f"  ! matches.json από {url.split('?')[0]}: {e}", file=sys.stderr)
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
    pens = {c["homeAway"]: c.get("shootoutScore") for c in comp["competitors"]}
    name = status.get("name") or ""
    # Αναβολή, διακοπή ή ματαίωση: η ESPN τα δείχνει ως «post» με σκορ 0–0 (δεν είναι «Τελικό»).
    off = OFF_STATUS.get(name) or next((v for k, v in OFF_STATUS.items() if k in name), "")
    return {
        "state": "pre" if off else status.get("state", "pre"),  # pre / in / post
        "home": score.get("home", 0), "away": score.get("away", 0),
        "halftime": name == "STATUS_HALFTIME",
        "detail": status.get("shortDetail") or status.get("detail") or "",
        "goals": goals,
        "off": off,
        "pens": [pens["home"], pens["away"]] if pens.get("home") is not None and pens.get("away") is not None else None,
    }


OFF_STATUS = {"STATUS_POSTPONED": "Αναβλήθηκε", "STATUS_CANCELED": "Ματαιώθηκε", "STATUS_ABANDONED": "Διακόπηκε",
              "STATUS_SUSPENDED": "Διακόπηκε", "STATUS_DELAYED": "Καθυστερεί η έναρξη", "STATUS_FORFEIT": "Χαρίστηκε"}


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
    if live.get("src") == "ehf":
        st["detail"] = f"{q}ο ημίχρονο" if st["state"] == "in" and q else ""
        return st
    st["detail"] = (f"{q}η περίοδος {st.get('clock') or ''}".strip() if q else "Διάλειμμα") if st["state"] == "in" else ""
    return st


GS_WIDGET = "https://widget.wh.geniussports.com/widget//?"
GS_DATA = "https://fibalivestats.dcd.shared.geniussports.com/data/"
_gs_found: dict[str, str] = {}


def basketball_state(live: dict) -> dict:
    """Basket League απευθείας από τη Genius Sports (ίδια λογική με το api/live.js, χωρίς τη Vercel).

    Τον αγώνα της ημέρας τον βρίσκει στο widget του esake.gr· σκορ, περίοδο και τέλος περιόδου/αγώνα
    από το data.json του αγώνα. Περίοδος τελειωμένη μόνο αν η τελευταία ενέργεια είναι το τέλος αυτής.
    """
    import re
    paok = re.compile(r"P\.?\s?A\.?\s?O\.?\s?K|Π\.?Α\.?Ο\.?Κ", re.I)
    req = urllib.request.Request(GS_WIDGET + live["key"], headers={"User-Agent": UA, "Referer": "https://www.esake.gr/"})
    with urllib.request.urlopen(req, timeout=30) as r:
        js = r.read().decode("utf-8")
    raw = re.search(r'var html = "(.*?)";\n', js, re.S)
    html = json.loads(f'"{raw.group(1)}"') if raw else ""
    rows = []
    for li in re.findall(r'<li class="spls_lsmatch[^"]*">(.*?)</li>', html, re.S):
        mid = re.search(r"webcast/\w+/(\d+)", li)
        status = re.search(r'spls_matchstatus">([^<]*)', li)
        date = re.search(r'spls_datefield">([^<]*)', li)
        if mid:
            rows.append({"id": mid.group(1), "status": (status.group(1) if status else "").strip(),
                         "date": (date.group(1) if date else "").strip()})
    day = dt.date.fromisoformat(live["day"])
    day_text = f"{day.day} {day:%b} {day.year}"
    key = f"{live['key']}|{live['day']}"
    row = next((x for x in rows if x["id"] == _gs_found.get(key)), None)
    data = None
    if not row:
        today = dt.datetime.now(notify.ATHENS).date()
        for c in rows:
            if not (c["date"] == day_text or (day == today and "live" in c["status"].lower())):
                continue
            try:
                j = get_json(f"{GS_DATA}{c['id']}/data.json")
            except Exception:
                continue
            tm = (j or {}).get("tm") or {}
            if any(paok.search((tm.get(t) or {}).get("name") or "") for t in ("1", "2")):
                row, data = c, j
                break
        if not row:
            raise ValueError("ο αγώνας δεν βρέθηκε στη Genius Sports")
        _gs_found[key] = row["id"]
    j = data or get_json(f"{GS_DATA}{row['id']}/data.json") or {}
    return gs_state(j, row["status"], live.get("side"))


def gs_state(j: dict, status: str, side: str | None) -> dict:
    """Η κατάσταση από το data.json της Genius και την ένδειξη του widget (Live/Final/Upcoming)."""
    import re
    paok = re.compile(r"P\.?\s?A\.?\s?O\.?\s?K|Π\.?Α\.?Ο\.?Κ", re.I)
    pbp = j.get("pbp") or []  # τα πιο πρόσφατα πρώτα
    tm = j.get("tm") or {}
    ended = any(a.get("actionType") == "game" and a.get("subType") == "end" for a in pbp)
    status = (status or "").lower()
    state = "post" if "final" in status or ended else "in" if "live" in status or pbp else "pre"
    flip = bool(paok.search((tm.get("1") or {}).get("name") or "")) != (side == "h")
    a, b = ("2", "1") if flip else ("1", "2")
    period = int(j.get("period") or 0)
    top = pbp[0] if pbp else {}
    # Στην αρχή μιας περιόδου η τελευταία ενέργεια μπορεί να είναι ακόμα το τέλος της προηγούμενης.
    period_ended = top.get("actionType") == "period" and top.get("subType") == "end" and int(top.get("period") or 0) == period
    clock = str(j.get("clock") or "")
    return {
        "state": state, "home": int((tm.get(a) or {}).get("score") or 0), "away": int((tm.get(b) or {}).get("score") or 0),
        "quarter": period if state == "in" else 0,
        "done": period if state == "post" or period_ended else max(0, period - 1),
        "detail": f"{period}η περίοδος {'' if period_ended else clock}".strip() if state == "in" else "",
    }


SOURCES = {"espn": espn_state, "euroleague": euroleague_state, "koe": waterpolo_state, "ea": waterpolo_state,
           "dp": waterpolo_state, "gs": basketball_state, "ehf": waterpolo_state, "eok": waterpolo_state}
PERIOD_SOURCES = ("euroleague", "koe", "ea", "dp", "gs", "eok")


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
    if m["live"]["src"] == "ehf" and new["state"] == "in" and old["state"] == "in":
        # Χάντμπολ: ημίχρονο όταν εμφανιστεί το σκορ ημιχρόνου.
        if (new.get("done") or 0) >= 1 > (old.get("done") or 0):
            out.append((f"{e} Ημίχρονο: {score_text(m, new)}", comp))
    elif m["live"]["src"] == "dp" and new["state"] == "in" and old["state"] == "in":
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
    if new.get("off") and new.get("off") != old.get("off"):
        out.append((f"{e} {new['off']}: {m['home']} – {m['away']}", comp))
    if old["state"] != "post" and new["state"] == "post":
        pens = new.get("pens")
        extra = f" (πέναλτι {pens[0]}–{pens[1]})" if pens and (pens[0] or pens[1]) else ""
        out.append((f"{e} Τελικό: {score_text(m, new)}{extra}", comp))
    return out


def settle_final(old: dict | None, new: dict) -> dict:
    """Το «Τελικό» μόνο αν το δούμε σε δύο συνεχόμενες αναγνώσεις: οι πηγές δείχνουν καμιά φορά για
    λίγο τέλος αγώνα σε διάλειμμα. Στην πρώτη μένουμε στην παλιά κατάσταση, με σημάδι."""
    if new["state"] == "post" and old and old["state"] != "post" and not old.get("post_seen"):
        return dict(old, post_seen=True)
    return new


# ---------------------------------------------------------------- κύριο

def main() -> int:
    started = dt.datetime.now(dt.timezone.utc)
    upcoming = [m for m in load_matches() if m.get("live") and notify.live_window(m, started)]
    print("Αγώνες για παρακολούθηση: " + (", ".join(f"{m['home']} – {m['away']}" for m in upcoming) or "κανένας ακόμα"))
    if not upcoming:
        # Ξεκίνησε από το πρόγραμμα του live.yml (εφεδρικός δρόμος) χωρίς αγώνα κοντά: τίποτα να κάνει.
        return 0
    states: dict[str, dict] = {}
    failures: dict[str, int] = {}
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
                failures[m["uid"]] = failures.get(m["uid"], 0) + 1
                if failures[m["uid"]] == FAIL_ALERT and dt.datetime.fromisoformat(m["start"]) <= now:
                    notify._push(["s:ops:live"], "⚠️ PAOKalendar: δεν διαβάζεται το live",
                                 f"{notify.teams(m)}: η πηγή ({m['live'].get('src')}) αποτυγχάνει εδώ και ~5 λεπτά: {e}",
                                 "/#/notifications", tag=f"ops-live-{m['nt']}")
                continue
            failures[m["uid"]] = 0
            old = states.get(m["uid"])
            if m["live"]["src"] == "euroleague":
                track_periods(old, new)
            new = settle_final(old, new)
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
