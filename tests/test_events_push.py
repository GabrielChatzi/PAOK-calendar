"""Ειδοποιήσεις ατομικών αθλημάτων σε όσους τα ακολουθούν (events.event_pushes)."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.pop("PUSH", None)

import events  # noqa: E402

NOW = dt.datetime(2026, 11, 28, 10, 0, tzinfo=dt.timezone.utc)  # 12:00 ώρα Ελλάδας, Σάββατο


def ev(i, start, end=None, results="", sport="judo"):
    return {"id": i, "sport": sport, "title": f"Τουρνουά {i}", "start": start, "end": end or start, "venue": "Λάρισα",
            "athletes": "", "results": results}


class EventPushTest(unittest.TestCase):
    def kinds(self, out):
        return [(x[0], x[5], x[6]) for x in out]

    def test_new_event_today_and_medals(self):
        out = events.event_pushes([ev("a", "2026-11-28", results="🥇 Α\n🥈 Β")], {}, NOW, known=set())
        self.assertEqual(self.kinds(out), [("e:judo:time", "a", "time"), ("e:judo:pre", "a", "pre"), ("e:judo:result", "a", "result")])
        self.assertIn("🥇1 🥈1", out[2][1])

    def test_nothing_twice(self):
        sent = {"a": {"time": "2026-11-28-2026-11-28", "pre": "2026-11-28", "result": "🥇1"}}
        self.assertEqual(events.event_pushes([ev("a", "2026-11-28", results="🥇 Α")], sent, NOW, known={"a"}), [])

    def test_new_medal_and_date_change(self):
        sent = {"a": {"time": "2026-12-05-2026-12-05", "result": "🥇1"}}
        out = events.event_pushes([ev("a", "2026-12-06", results="🥇 Α")], sent, NOW, known={"a"})
        self.assertEqual(self.kinds(out), [("e:judo:time", "a", "time")])
        self.assertIn("Αλλαγή", out[0][1])
        sent2 = {"b": {"time": "2026-11-27-2026-11-28", "pre": "2026-11-27", "result": "🥇1"}}
        out = events.event_pushes([ev("b", "2026-11-27", "2026-11-28", results="🥇 Α\n🥉 Γ")], sent2, NOW, known={"b"})
        self.assertEqual(self.kinds(out), [("e:judo:result", "b", "result")])

    def test_old_and_before_nine(self):
        self.assertEqual(events.event_pushes([ev("o", "2026-10-01", results="🥇 Α")], {}, NOW, known={"o"}), [])
        early = dt.datetime(2026, 11, 28, 5, 0, tzinfo=dt.timezone.utc)  # 07:00 Ελλάδα
        out = events.event_pushes([ev("a", "2026-11-28")], {"a": {"time": "2026-11-28-2026-11-28"}}, early, known={"a"})
        self.assertEqual(out, [])

    def test_known_without_record_is_silent(self):
        sent = {}
        out = events.event_pushes([ev("k", "2026-12-10")], sent, NOW, known={"k"})
        self.assertEqual(out, [])
        self.assertEqual(sent["k"]["time"], "2026-12-10-2026-12-10")


if __name__ == "__main__":
    unittest.main()
