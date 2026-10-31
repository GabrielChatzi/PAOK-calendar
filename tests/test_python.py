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


if __name__ == "__main__":
    unittest.main()
