"""Έλεγχοι για τα «δύσκολα» σημεία που βρήκαμε σε πραγματικούς αγώνες (τρέχουν στο tests.yml).

    python3 -m unittest discover tests
"""
import datetime as dt
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.pop("PUSH", None)  # καμία πραγματική ειδοποίηση από τα tests

import build_calendars as b  # noqa: E402
import live  # noqa: E402
import notify  # noqa: E402

UTC = dt.timezone.utc
M = {"uid": "x", "nt": "abcdef0123", "section": "waterpolo", "home": "ΠΑΟΚ", "away": "Εθνικός",
     "competition": "Water Polo League", "start": "2026-10-31T16:00:00+02:00", "timeKnown": True, "score": ""}


def st(state, home=0, away=0, **kw):
    return dict({"state": state, "home": home, "away": away}, **kw)


def titles(m, old, new):
    return [t for t, _ in live.events(m, old, new)]


class LiveEvents(unittest.TestCase):
    def test_first_read_is_only_a_reference(self):
        self.assertEqual(live.events(dict(M, live={"src": "koe"}), None, st("in", 3, 2, done=1)), [])

    def test_start(self):
        m = dict(M, live={"src": "koe"})
        self.assertTrue(titles(m, st("pre"), st("in", done=0))[0].startswith("🤽 Ξεκίνησε"))

    def test_waterpolo_halftime_and_period(self):
        m = dict(M, live={"src": "koe"})
        self.assertIn("Ημίχρονο", titles(m, st("in", 5, 6, done=1), st("in", 5, 6, done=2))[0])
        self.assertIn("Τέλος 3ης περιόδου", titles(m, st("in", 10, 8, done=2), st("in", 10, 8, done=3))[0])

    def test_waterpolo_tie_after_four_goes_to_penalties(self):
        m = dict(M, live={"src": "koe"})
        self.assertIn("πέναλτι", titles(m, st("in", 12, 12, done=3), st("in", 12, 12, done=4))[0])

    def test_no_period_end_after_four_when_not_tied(self):
        m = dict(M, live={"src": "koe"})
        self.assertEqual(titles(m, st("in", 13, 11, done=3), st("in", 13, 11, done=4)), [])

    def test_basketball_tie_after_four_goes_to_overtime(self):
        m = dict(M, section="basketball", live={"src": "gs"})
        self.assertIn("παράταση", titles(m, st("in", 80, 80, done=3), st("in", 80, 80, done=4))[0])

    def test_volley_set_end_with_points(self):
        m = dict(M, section="volley", live={"src": "dp"})
        new = st("in", 2, 0, done=2, quarters=[{"home": 25, "away": 23}, {"home": 25, "away": 12}])
        self.assertEqual(titles(m, st("in", 1, 0, done=1), new),
                         ["🏐 Τέλος 2ου σετ (25–12): ΠΑΟΚ 2–0 Εθνικός"])

    def test_handball_halftime(self):
        m = dict(M, section="handball", live={"src": "ehf"})
        self.assertIn("Ημίχρονο", titles(m, st("in", 14, 16, done=0), st("in", 14, 16, done=1))[0])

    def test_final_needs_two_reads(self):
        """Στο πόλο η ΚΟΕ έδειξε για λίγο «τέλος» στο διάλειμμα: μία ανάγνωση δεν αρκεί."""
        m = dict(M, live={"src": "koe"})
        old = st("in", 10, 8, done=3)
        first = live.settle_final(old, st("post", 10, 8, done=4))
        self.assertEqual(first["state"], "in")
        self.assertEqual(titles(m, old, first), [])
        second = live.settle_final(first, st("post", 10, 8, done=4))
        self.assertEqual(titles(m, first, second), ["🤽 Τελικό: ΠΑΟΚ 10–8 Εθνικός"])

    def test_glitch_post_then_in_sends_nothing(self):
        old = st("in", 10, 8, done=3)
        first = live.settle_final(old, st("post", 10, 8, done=4))
        back = live.settle_final(first, st("in", 10, 8, done=3))
        self.assertEqual(back["state"], "in")
        self.assertFalse(back.get("post_seen"))


class Euroleague(unittest.TestCase):
    def state(self, h):
        with mock.patch.object(live, "get_json", lambda url: h):
            return live.euroleague_state({"code": 1, "season": "U2026"})["state"]

    def test_live_flag_before_tipoff_is_not_start(self):
        self.assertEqual(self.state({"Live": True, "ScoreA": "0", "ScoreB": "0", "Quarter": "0"}), "pre")
        self.assertEqual(self.state({"Live": True, "ScoreA": "0", "ScoreB": "0", "Quarter": "1", "RemainingPartialTime": "10:00"}), "pre")

    def test_started(self):
        self.assertEqual(self.state({"Live": True, "ScoreA": "0", "ScoreB": "0", "Quarter": "1", "RemainingPartialTime": "09:41"}), "in")
        self.assertEqual(self.state({"Live": True, "ScoreA": "2", "ScoreB": "0", "Quarter": "1"}), "in")
        self.assertEqual(self.state({"Live": True, "ScoreA": "40", "ScoreB": "38", "Quarter": "0"}), "in")  # ημίχρονο

    def test_final_while_still_live(self):
        # Balkan–ΠΑΟΚ 56-79, 10/11/2026: «Live» και Quarter "" για πάνω από μία ώρα μετά το τέλος.
        end = {"Live": True, "ScoreA": "56", "ScoreB": "79", "Quarter": "", "GameTime": "40:00", "RemainingPartialTime": "00:00"}
        self.assertEqual(self.state(end), "post")
        self.assertEqual(self.state(dict(end, GameTime="30:00")), "in")                          # διάλειμμα 3ης-4ης
        self.assertEqual(self.state(dict(end, ScoreA="79")), "in")                               # ισοπαλία: παράταση
        self.assertEqual(self.state(dict(end, ScoreA="85", ScoreB="83", GameTime="45:00")), "post")  # μετά την παράταση
        self.assertEqual(self.state(dict(end, Quarter="4", RemainingPartialTime="00:12", GameTime="39:48")), "in")


class Football(unittest.TestCase):
    def espn(self, name, state, home=0, away=0, pens=None):
        comps = [{"homeAway": "home", "score": str(home), "team": {"id": "1"}}, {"homeAway": "away", "score": str(away), "team": {"id": "2"}}]
        if pens:
            comps[0]["shootoutScore"], comps[1]["shootoutScore"] = pens
        data = {"header": {"competitions": [{"status": {"type": {"name": name, "state": state}}, "competitors": comps}]}, "keyEvents": []}
        with mock.patch.object(live, "get_json", return_value=data):
            return live.espn_state({"league": "gre.1", "id": "1"})

    def test_postponed_is_not_final(self):
        m = dict(M, section="football", live={"src": "espn"})
        new = live.settle_final(st("pre"), self.espn("STATUS_POSTPONED", "post"))
        self.assertEqual(new["state"], "pre")
        self.assertEqual(titles(m, dict(st("pre"), off=""), new), ["⚽ Αναβλήθηκε: ΠΑΟΚ – Εθνικός"])

    def test_second_half_start(self):
        m = dict(M, section="football", live={"src": "espn"})
        old = st("in", 0, 2, goals=[], halftime=True)
        self.assertEqual(titles(m, old, st("in", 0, 2, goals=[], halftime=False)),
                         ["⚽ Ξεκίνησε το 2ο ημίχρονο: ΠΑΟΚ 0–2 Εθνικός"])
        self.assertEqual(titles(m, old, st("in", 0, 2, goals=[], halftime=True)), [])
        self.assertEqual(live.once_key(m, "⚽ Ξεκίνησε το 2ο ημίχρονο: ΠΑΟΚ 0–2 Εθνικός", False), "abcdef0123-h2")

    def test_disallowed_goal(self):
        m = dict(M, section="football", live={"src": "espn"})
        old = st("in", 1, 0, goals=[{"id": "g1"}])
        self.assertEqual(titles(m, old, st("in", 0, 0, goals=[])), ["⚽ Ακυρώθηκε γκολ: ΠΑΟΚ 0–0 Εθνικός"])

    def test_state_survives_restart(self):
        import tempfile, pathlib
        now = dt.datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(live, "STATE_FILE", pathlib.Path(d) / "s.json"):
            live.save_states({"u": st("in", 2, 1, done=2)}, now)
            self.assertEqual(live.load_states(now + dt.timedelta(minutes=20))["u"]["done"], 2)
            self.assertEqual(live.load_states(now + dt.timedelta(hours=2)), {})

    def test_final_after_penalties(self):
        m = dict(M, section="football", live={"src": "espn"})
        new = self.espn("STATUS_FINAL_PEN", "post", 1, 1, pens=(4, 3))
        self.assertIn("(πέναλτι 4–3)", titles(m, st("in", 1, 1), new)[-1])


class Genius(unittest.TestCase):
    def data(self, period, top, clock="08:36"):
        return {"period": period, "clock": clock, "tm": {"1": {"name": "Iraklis BC", "score": 31}, "2": {"name": "PAOK BC", "score": 34}},
                "pbp": [top, {"actionType": "2pt", "period": period - 1}]}

    def test_start_of_period_keeps_previous_done(self):
        """Αρχή 3ης: η τελευταία ενέργεια είναι ακόμα το τέλος της 2ης (έβγαλε «Τέλος 3ης»)."""
        j = self.data(3, {"actionType": "period", "subType": "end", "period": 2})
        s = live.gs_state(j, "Live", "a")
        self.assertEqual((s["state"], s["quarter"], s["done"]), ("in", 3, 2))

    def test_end_of_period(self):
        j = self.data(3, {"actionType": "period", "subType": "end", "period": 3}, clock="00:00")
        self.assertEqual(live.gs_state(j, "Live", "a")["done"], 3)

    def test_side_flips_scores(self):
        j = self.data(2, {"actionType": "2pt", "period": 2})
        self.assertEqual((live.gs_state(j, "Live", "a")["home"], live.gs_state(j, "Live", "h")["home"]), (31, 34))

    def test_game_end(self):
        j = self.data(4, {"actionType": "game", "subType": "end", "period": 4})
        self.assertEqual(live.gs_state(j, "Live", "a")["state"], "post")


class Results(unittest.TestCase):
    def test_volley_final_only_with_three_sets(self):
        for score, ok in (("3-1", True), ("0-3", True), ("2-1", False), ("1-1", False), ("", False)):
            self.assertEqual(b.is_volley_final(score), ok, score)

    def test_no_final_before_shortest_duration(self):
        now = dt.datetime(2026, 10, 31, 16, 50, tzinfo=b.ATHENS)
        m = b.Match(section="waterpolo", uid="u", day=now.date(), time=dt.time(16, 0), home="ΠΑΟΚ", away="Χ",
                    paok_home=True, score="4-6")
        b.drop_live_scores("waterpolo", [m], now)  # 50' μετά την έναρξη
        self.assertEqual(m.score, "")
        m.score = "13-11"
        b.drop_live_scores("waterpolo", [m], now + dt.timedelta(minutes=20))
        self.assertEqual(m.score, "13-11")

    def test_waterpololeague_live_badge_is_not_final(self):
        block = ('<a href="https://waterpololeague.gr/fixture/paok-x-2026-10-31" class="block">'
                 '<div class="font-heading text-xs">ΠΑΟΚ DOMUS ERGO</div><div class="font-heading text-xs">ΕΘΝΙΚΟΣ</div>'
                 '<div class="hidden w-16 px-1 text-center sm:block"><div class="text-sm font-semibold text-red-600">'
                 '<span class="flex"><span class="relative"></span></span> LIVE </span> 8 - 7 </div></div>'
                 '<!-- Quick Info --><div class="pl-6"><div>Σαβ, 31 Οκτ 2026</div><div class="text-xs">16:00</div></div></a>')
        with mock.patch.object(b, "fetch", return_value=block), mock.patch.object(b, "koe_live", return_value=None):
            ms = b.waterpolo_matches("waterpolo")
        self.assertEqual(ms[0].score, "")


class Postponed(unittest.TestCase):
    def test_status_change_notifies_and_stops_waiting(self):
        old = dict(M, start="2099-01-01T16:00:00+02:00")
        new = dict(old, status="postponed", note="Λόγω καιρού")
        ev = notify.changes([old], [new], {"waterpolo"})
        self.assertEqual([(e[1], e[2]) for e in ev], [("time", "🤽 Αναβλήθηκε: ΠΑΟΚ – Εθνικός")])
        now = dt.datetime.fromisoformat("2099-01-01T17:30:00+02:00")
        self.assertFalse(notify.awaiting_result(new, now))
        self.assertFalse(notify.live_window(dict(new, live={"src": "koe"}), now))

    def test_calendar_marks_postponed_and_note(self):
        m = b.Match(section="football", uid="u", day=dt.date(2026, 11, 8), time=dt.time(20, 0), home="ΠΑΟΚ", away="Χ",
                    paok_home=True, status="cancelled")
        ics = b.build_ics("x", [m], "20261101T000000Z")
        self.assertIn("ΜΑΤΑΙΩΘΗΚΕ: ", ics)
        self.assertIn("STATUS:CANCELLED", ics)

    def test_manual_status_marks_official_match(self):
        import json, tempfile, pathlib
        m = b.Match(section="volley", uid="u", day=dt.date(2026, 11, 8), time=dt.time(18, 0), home="ΠΑΟΚ", away="Χ", paok_home=True)
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "manual.json"
            path.write_text(json.dumps([{"section": "volley", "date": "2026-11-08", "status": "postponed", "reason": "Ανακοίνωση ΕΣΑΠ"}]))
            with mock.patch.object(b, "MANUAL_PATH", path):
                self.assertEqual(b.manual_matches("volley", [m]), [])
        self.assertEqual((m.status, m.note), ("postponed", "Ανακοίνωση ΕΣΑΠ"))

    def test_genius_postponed(self):
        s = live.gs_state({"period": 0, "tm": {}, "pbp": []}, "Postponed", "h")
        self.assertEqual((s["state"], s["off"]), ("pre", "Αναβλήθηκε"))


class Notify(unittest.TestCase):
    def test_reminder_one_hour(self):
        self.assertLessEqual(notify.REMINDER_WINDOW, dt.timedelta(minutes=62))
        self.assertGreaterEqual(notify.REMINDER_WINDOW, dt.timedelta(minutes=60))

    def test_awaiting_result_window(self):
        start = dt.datetime(2026, 10, 31, 14, 0, tzinfo=UTC)
        m = dict(M, start=start.isoformat())
        self.assertFalse(notify.awaiting_result(m, start + dt.timedelta(minutes=60)))
        self.assertTrue(notify.awaiting_result(m, start + dt.timedelta(minutes=75)))
        self.assertFalse(notify.awaiting_result(m, start + dt.timedelta(hours=7)))
        self.assertFalse(notify.awaiting_result(dict(m, score="13-11"), start + dt.timedelta(minutes=75)))

    def test_result_goes_to_match_followers_quietly(self):
        sent = []
        with mock.patch.object(notify, "_push", lambda *a, **k: sent.append((a, k))):
            notify.send("waterpolo", "result", "Τελικό", "x", match=dict(M, live={"src": "koe"}))
        (topics, *_), kw = sent[0][0], sent[0][1]
        self.assertIn("m:abcdef0123:result", topics)
        self.assertEqual(sent[0][0][4], "abcdef0123-result")
        self.assertTrue(kw.get("quiet"))
        # Μία φορά ανά συσκευή, όποιος κι αν το στείλει πρώτος (live ή ενημέρωση).
        self.assertEqual(kw.get("once"), "abcdef0123-result")

    def test_live_final_shares_once_key_with_result(self):
        sent = []
        m = dict(M, live={"src": "koe"})
        with mock.patch.object(notify, "_push", lambda *a, **k: sent.append(k)):
            notify.send("waterpolo", "live", "Τελικό", "x", match=m, also_match_kinds=("result",),
                        tag="abcdef0123-result", once="abcdef0123-result")
            notify.send("waterpolo", "live", "Ξεκίνησε", "x", match=m)
        self.assertEqual(sent[0]["once"], "abcdef0123-result")
        self.assertIsNone(sent[1]["once"])

    def _reminders(self, matches, now):
        import json, tempfile
        from pathlib import Path
        sent = []
        with tempfile.TemporaryDirectory() as d:
            mp, sp = Path(d) / "m.json", Path(d) / "s.json"
            mp.write_text(json.dumps({"matches": matches}), encoding="utf-8")
            fake = mock.Mock(wraps=dt.datetime)
            fake.now.return_value = now
            with mock.patch.object(notify, "_push", lambda topics, title, *a, **k: sent.append((topics, title))), \
                    mock.patch.object(notify.dt, "datetime", fake), mock.patch.dict(os.environ, {"GITHUB_OUTPUT": ""}):
                notify.reminders(mp, sp)
                notify.reminders(mp, sp)  # δεύτερος έλεγχος: τίποτα ξανά
        return sent

    def test_kickoff_notice_only_without_live(self):
        start = dt.datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        no_live = dict(M, uid="a", nt="aaaaaaaaaa", section="futsal", start=start.isoformat(), live=None)
        with_live = dict(M, uid="b", nt="bbbbbbbbbb", start=start.isoformat(), live={"src": "koe"})
        sent = self._reminders([no_live, with_live], start + dt.timedelta(seconds=40))
        self.assertEqual(len(sent), 1)
        topics, title = sent[0]
        self.assertTrue(title.startswith("🥅 Ξεκινά:"))
        self.assertIn("s:futsal:pre", topics)
        self.assertIn("m:aaaaaaaaaa:pre", topics)

    def test_no_kickoff_notice_late_or_postponed(self):
        start = dt.datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        m = dict(M, section="futsal", start=start.isoformat(), live=None)
        self.assertEqual(self._reminders([m], start + dt.timedelta(minutes=16)), [])
        self.assertEqual(self._reminders([dict(m, status="postponed")], start + dt.timedelta(seconds=40)), [])


class ClubResults(unittest.TestCase):
    """Αποτελέσματα από τις αναρτήσεις της ΑΣ ΠΑΟΚ (πραγματικοί τίτλοι)."""

    def score(self, title, text="", home="ΠΑΟΚ", away="Χ", paok_home=True):
        import club
        return club.score_from_post(title, text, home, away, paok_home)

    def test_win_in_title(self):
        t = "Επιστροφή στις νίκες για τον ΠΑΟΚ PayspotLabraki, νίκη με 7-3 επί του ΑΟΔ Κορυδαλλού!"
        self.assertEqual(self.score(t, away="ΚΟΡΥΔΑΛΛΟΥ ΑΟΔ"), "7-3")

    def test_win_away_from_text(self):
        t = "Από πεντάρα σε πεντάρα οι Νταμπλούχες!"
        text = "Νέα εύκολη νίκη για τον ΠΑΟΚ, που επικράτησε με 5-0 του ΠΑΣ Πύργος στη Βάρδα."
        self.assertEqual(self.score(t, text, home="ΠΑΣ ΠΥΡΓΟΣ", away="ΠΑΟΚ", paok_home=False), "0-5")

    def test_loss_away(self):
        text = "Ο ΠΑΟΚ ηττήθηκε με 71-69 από την ΑΕΟ Πρωτέα Βούλας."
        self.assertEqual(self.score("«Λύγισε» στην Βούλα…", text, home="ΠΡΩΤΕΑΣ", away="ΠΑΟΚ", paok_home=False), "71-69")

    def test_score_at_end_of_sentence(self):
        text = ("Για την 5η αγωνιστική της WBL 1, ο ΠΑΟΚ αντιμετώπισε εκτός έδρας τον Πρωτέα Βούλας, το απόγευμα "
                "της Κυριακής 1 Νοεμβρίου, γνωρίζοντας την ήττα με 71-69. Οι «ασπρόμαυρες» πήραν προβάδισμα με 9-16, "
                "κλείνοντας το πρώτο δεκάλεπτο στο 14-20.")
        self.assertEqual(self.score("«Λύγισε» στην Βούλα…", text, home="ΠΡΩΤΕΑΣ", away="ΠΑΟΚ", paok_home=False), "71-69")

    def test_youth_teams_ignored(self):
        self.assertIsNone(self.score("Νίκη με 14-11 για τους Παίδες Πόλο του ΠΑΟΚ"))

    def test_named_order(self):
        self.assertEqual(self.score("ΠΑΣ Πύργος – ΠΑΟΚ 0-5", home="ΠΑΣ ΠΥΡΓΟΣ", away="ΠΑΟΚ", paok_home=False), "0-5")

    def test_unclear_gives_nothing(self):
        self.assertIsNone(self.score("Η μικτή ζώνη του ΠΑΣ Πύργος-ΠΑΟΚ", "νίκη με 5-0"))
        self.assertIsNone(self.score("Συνεχίζει στο Conference Cup ο ΠΑΟΚ Infotrust!"))
        self.assertIsNone(self.score("Το σκορ ήταν 3-2", "Αγώνας με ανατροπές."))  # δεν λέει ποιος κέρδισε
        self.assertIsNone(self.score("ΠΑΟΚ - Κορυδαλλός (01/11, 14:00)"))

    def test_results_only_posts_after_start(self):
        import club
        m = b.Match(section="futsal", uid="u", day=dt.date(2026, 11, 1), time=dt.time(14, 0), home="ΠΑΟΚ",
                    away="ΚΟΡΥΔΑΛΛΟΥ ΑΟΔ", paok_home=True)
        post = lambda date, title: {"date": date, "title": {"rendered": title}, "content": {"rendered": ""},
                                    "categories": [7], "link": "x", "id": 1}
        posts = [post("2026-11-01T13:00:00", "Νίκη με 9-1!"), post("2026-11-01T15:34:00", "νίκη με 7-3 επί του Κορυδαλλού")]
        with mock.patch.dict(club._DATA, {"posts": posts}), \
                mock.patch.object(club, "get_json", lambda path: [{"id": 7, "name": "Ποδόσφαιρο Σάλας"}]):
            club.results("futsal", [m], now=dt.datetime(2026, 11, 1, 16, 0, tzinfo=b.ATHENS))
        self.assertEqual(m.score, "7-3")


class TV(unittest.TestCase):
    def test_channel_from_announcement(self):
        import club
        for text, want in [("Η αναμέτρηση θα μεταδοθεί μέσω του ΕΟΚ TV. Για το", "ΕΟΚ TV"),
                           ("Το παιχνίδι θα μεταδοθεί μέσω του AC PAOK TV.", "AC PAOK TV"),
                           ("Ο αγώνας θα μεταδοθεί ζωντανά από την ΕΡΤ Sports 2, ενώ", "ΕΡΤ Sports 2")]:
            self.assertEqual(club.CHANNEL_RE.search(text).group(1), want)

    def test_video_matches_opponent_and_sport(self):
        import club
        self.assertIn("ΚΟΡΥΔ", club.team_words("ΚΟΡΥΔΑΛΛΟΥ ΑΟΔ"))
        self.assertEqual(club.team_words("Z.A.O.N."), ["ΖΑΟΝ"])
        self.assertTrue(club.same_sport("futsal", "ΠΑΟΚ - Κορυδαλλού | FUTSAL SUPER LEAGUE"))
        self.assertFalse(club.same_sport("volley-women", "Αllwyn WBL1 - ΠΡΩΤΕΑΣ ΒΟΥΛΑΣ- ΠΑΟΚ"))

    def test_weekly_programme_channel(self):
        import club
        post = {"id": 1, "date": "2026-11-02T12:25:00", "modified": "2026-11-02T12:25:00", "link": "x",
                "title": {"rendered": "Όπου και αν παίζεις σ’ ακολουθάμε (03/11-09/11)"},
                "content": {"rendered": "<p>Τρίτη 3 Νοεμβρίου 2026</p><p>ΚΑΕ ΠΑΟΚ<br>6η αγωνιστική, EuroCup<br>"
                                        "PAOK Sports Arena<br>20:00, ΠΑΟΚ-Ρόμα (Novasports Prime)</p>"}}
        with mock.patch.object(club, "get_json", lambda path: [post]):
            e = club.program_entries(dt.date(2026, 11, 2))
        self.assertEqual((e[0]["section"], e[0]["channel"], e[0]["away"]), ("basketball", "Novasports Prime", "Ρόμα"))


class HandballLogos(unittest.TestCase):
    def test_greek_names_match_latin_slugs(self):
        logos = [(["DRAMA"], "drama.jpg"), (["GAS", "KILKIS"], "kilkis.jpg"), (["XANTH"], "xanth.jpg"),
                 (["AEK"], "aek.jpg"), (["OLYMPIAKOS", "SFP", "KSYNI"], "olympiacos.png")]
        with mock.patch.dict(b._OXE_LOGOS, {False: logos}):
            self.assertEqual(b.oxe_logo("GMC ΔΡΑΜΑ 1986", False), "drama.jpg")
            self.assertEqual(b.oxe_logo("Γ.Α.Σ ΚΙΛΚΙΣ", False), "kilkis.jpg")
            self.assertEqual(b.oxe_logo("Χ.Α.Ν.Θ", False), "xanth.jpg")
            self.assertEqual(b.oxe_logo("Α.Ε.Κ.", False), "aek.jpg")
            self.assertEqual(b.oxe_logo("ΟΛΥΜΠΙΑΚΟΣ ΟΜΙΛΟΣ ΞΥΝΗ", False), "olympiacos.png")
            self.assertEqual(b.oxe_logo("ΑΓΝΩΣΤΗ ΟΜΑΔΑ", False), "")


class Admin(unittest.TestCase):
    def test_admin_final_overrides(self):
        m = b.Match(section="futsal", uid="u1", day=dt.date(2026, 11, 1), time=dt.time(14, 0), home="ΠΑΟΚ",
                    away="Χ", paok_home=True, score="6-3", live={"src": "x"})
        nt = b.match_topic_id("u1")
        with mock.patch.dict(b._ADMIN, {"entries": {nt: {"nt": nt, "home": 7, "away": 3, "final": True, "note": ""}}}):
            b.apply_admin("futsal", [m])
        self.assertEqual((m.score, m.live), ("7-3", None))

    def test_admin_live_entry_does_not_set_score(self):
        m = b.Match(section="futsal", uid="u2", day=dt.date(2026, 11, 1), time=dt.time(14, 0), home="ΠΑΟΚ",
                    away="Χ", paok_home=True)
        nt = b.match_topic_id("u2")
        with mock.patch.dict(b._ADMIN, {"entries": {nt: {"nt": nt, "home": 1, "away": 0, "final": False}}}):
            b.apply_admin("futsal", [m])
        self.assertEqual(m.score, "")

    def test_goal_once_key_matches_admin(self):
        m = dict(M, nt="abcdef0123")
        self.assertEqual(live.once_key(m, "⚽ ΓΚΟΛ ΤΟΥ ΠΑΟΚ! ΠΑΟΚ 1–0 Εθνικός", False), "abcdef0123-s1-0")
        self.assertEqual(live.once_key(m, "⚽ Τελικό: ΠΑΟΚ 1–0 Εθνικός", True), "abcdef0123-result")
        self.assertEqual(live.once_key(m, "⚽ Ημίχρονο: ΠΑΟΚ 1–0 Εθνικός", False), "abcdef0123-ht")
        self.assertEqual(live.once_key(m, "🤽 Τέλος 3ης περιόδου: ΠΑΟΚ 9–6 Ολυμπιακός", False), "abcdef0123-p3")
        self.assertEqual(live.once_key(m, "🤽 Ισοπαλία, πάμε στα πέναλτι: ΠΑΟΚ 9–9 Ολυμπιακός", False), "abcdef0123-p4")
        self.assertEqual(live.once_key(m, "🏐 Τέλος 2ου σετ (25–21): ΠΑΟΚ 2–0 Ολυμπιακός", False), "abcdef0123-set2")
        self.assertEqual(live.once_key(m, "⚽ Ακυρώθηκε γκολ: ΠΑΟΚ 0–0 Εθνικός", False), "abcdef0123-x0-0")
        self.assertIsNone(live.once_key(m, "🏀 Τέλος παράτασης: ΠΑΟΚ 90–90 Άρης", False))


class VolleyWomenNames(unittest.TestCase):
    def test_latin_names_become_greek(self):
        import build_calendars as b
        self.assertEqual(b.volley_women_name("PANATHINAIKOS A.O."), "Παναθηναϊκός Α.Ο.")
        self.assertEqual(b.volley_women_name("OLYMPIACOS S.F.P."), "Ολυμπιακός Σ.Φ.Π.")
        self.assertEqual(b.volley_women_name("Z.A.O.N."), "Ζ.Α.Ο.Ν.")
        self.assertEqual(b.volley_women_name("A.S. ELPIS"), "Α.Σ. Ελπίς")
        self.assertEqual(b.volley_women_name("P.A.O.K. F&U"), "ΠΑΟΚ")
        self.assertEqual(b.volley_women_name("UNKNOWN CLUB ATHENS"), "Unknown Club Athens")  # άγνωστη: όπως είναι


if __name__ == "__main__":
    unittest.main()


class LiveResults(unittest.TestCase):
    """Το τελικό από την πηγή live όταν η επίσημη σελίδα αργεί (Καλαμάτα–ΠΑΟΚ, 9/11)."""

    def match(self):
        return b.Match(section="volley", uid="u", day=dt.date(2026, 11, 9), time=dt.time(19, 30),
                       home="Καλαμάτα", away="ΠΑΟΚ", paok_home=False,
                       live={"src": "dp", "fed": "hvl", "day": "2026-11-09", "side": "a"})

    def run_with(self, st, now):
        m = self.match()
        with mock.patch.dict(live.SOURCES, {"dp": lambda _: st}):
            b.live_results("volley", [m], now)
        return m

    def test_final(self):
        m = self.run_with({"state": "post", "home": 1, "away": 3}, dt.datetime(2026, 11, 9, 22, 0, tzinfo=b.ATHENS))
        self.assertEqual((m.score, m.live), ("1-3", None))

    def test_not_final(self):
        now = dt.datetime(2026, 11, 9, 22, 0, tzinfo=b.ATHENS)
        self.assertEqual(self.run_with({"state": "in", "home": 1, "away": 2}, now).score, "")
        self.assertEqual(self.run_with({"state": "post", "home": 1, "away": 2}, now).score, "")

    def test_too_early(self):
        m = self.run_with({"state": "post", "home": 0, "away": 3}, dt.datetime(2026, 11, 9, 20, 0, tzinfo=b.ATHENS))
        self.assertEqual(m.score, "")


class SocialRemind(unittest.TestCase):
    ITEMS = [
        {"type": "post", "what": "results", "day": "2026-11-10", "time": "09:00", "title": "Αποτελέσματα",
         "caption": "x", "missing": [], "images": ["a.png", "b.png"]},
        {"type": "story", "what": "dayResults", "day": "2026-11-10", "time": "21:30", "title": "Αποτελέσματα ημέρας",
         "missing": ["Balkan – ΠΑΟΚ"], "images": []},
    ]

    def due(self, t, sent=None):
        import social_remind
        now = dt.datetime.fromisoformat(t).replace(tzinfo=b.ATHENS)
        return [i["what"] for i in social_remind.due(self.ITEMS, sent or {}, now)]

    def test_on_time_once(self):
        self.assertEqual(self.due("2026-11-10T08:56"), ["results"])
        self.assertEqual(self.due("2026-11-10T08:50"), [])
        self.assertEqual(self.due("2026-11-10T15:00"), [])
        self.assertEqual(self.due("2026-11-10T09:10", {"2026-11-10-0900-results": "x"}), [])

    def test_waits_for_scores(self):
        self.assertEqual(self.due("2026-11-10T21:30"), [])
        self.ITEMS[1].update(missing=[], images=["s.png"])
        try:
            self.assertEqual(self.due("2026-11-10T23:40"), ["dayResults"])
        finally:
            self.ITEMS[1].update(missing=["Balkan – ΠΑΟΚ"], images=[])
