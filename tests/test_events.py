"""Ατομικά αθλήματα: ημερομηνίες από τις αναρτήσεις της ΑΣ ΠΑΟΚ και διοργανώσεις (events.py)."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.pop("PUSH", None)

import events as ev  # noqa: E402

D = dt.date
REF = D(2026, 11, 20)


def post(pid, date, title, content, cat=64, link=None):
    return {"id": pid, "date": date + "T12:00:00", "title": {"rendered": title}, "content": {"rendered": content},
            "link": link or f"https://acpaok.gr/p{pid}/", "categories": [cat, 78]}


class FindDates(unittest.TestCase):
    def test_range_same_month(self):
        self.assertEqual(ev.find_dates("Στη Νίκαια από τις 19 έως τις 22 Νοεμβρίου", REF), (D(2026, 11, 19), D(2026, 11, 22)))

    def test_range_wins_over_earlier_single_day(self):
        text = "Η αποστολή φεύγει από την Τετάρτη (18/11). Το πρωτάθλημα γίνεται από τις 19 έως τις 22 Νοεμβρίου."
        self.assertEqual(ev.find_dates(text, REF), (D(2026, 11, 19), D(2026, 11, 22)))

    def test_weekdays_and_kai(self):
        self.assertEqual(ev.find_dates("το Σάββατο 28 και την Κυριακή 29 Νοεμβρίου στο ΣΕΦ", REF),
                         (D(2026, 11, 28), D(2026, 11, 29)))

    def test_cross_month_and_year(self):
        self.assertEqual(ev.find_dates("από 30 Δεκεμβρίου έως 2 Ιανουαρίου", REF), (D(2026, 12, 30), D(2027, 1, 2)))
        self.assertEqual(ev.find_dates("28/12 - 3/1", REF), (D(2026, 12, 28), D(2027, 1, 3)))

    def test_numeric(self):
        self.assertEqual(ev.find_dates("Πανελλήνιο Κλειστού (28-29/11)", REF), (D(2026, 11, 28), D(2026, 11, 29)))
        self.assertEqual(ev.find_dates("Μίτινγκ την Κυριακή 6/12", REF), (D(2026, 12, 6), D(2026, 12, 6)))

    def test_ignores_old_and_non_dates(self):
        # Βιογραφικό με παλιές χρονιές, κιλά και ρεκόρ: τίποτα.
        text = "2024: 2η θέση στη σκυταλοδρομία 4×100μ. Πανελλήνιο Κύπελλο 2025-26. 12 πανελλήνια ρεκόρ στα 85 κιλά"
        self.assertIsNone(ev.find_dates(text, REF))
        self.assertIsNone(ev.find_dates("Πρωταθλητής στις 5 Μαΐου 2019", REF))

    def test_month_word_must_be_a_month(self):
        self.assertIsNone(ev.find_dates("με 12 μαρτυρίες αθλητών", REF))


class Events(unittest.TestCase):
    def test_from_posts_with_results_attached(self):
        posts = [
            post(1, "2026-11-20", "Με στόχο τις διακρίσεις στο Πανελλήνιο Πρωτάθλημα ο ΠΑΟΚ στην Άρση Βαρών!",
                 "<p>Στη Νίκαια από τις 19 έως τις 22 Νοεμβρίου.</p>"),
            post(2, "2026-11-23", "Τρία μετάλλια για τον ΠΑΟΚ στο Πανελλήνιο!", "<p>Ολοκληρώθηκε το πρωτάθλημα.</p>"),
            post(3, "2026-11-19", "Στον ΠΑΟΚ Infotrust ο Μανώλης Αλεξάκης!", "<p>Μεταγραφή.</p>", cat=58),
            post(4, "2026-11-21", "Στίβος: Μίτινγκ ΑμεΑ στο Καυτανζόγλειο!", "<p>Την Κυριακή 6/12, με τον Παραολυμπιονίκη μας.</p>",
                 cat=86),
        ]
        out = {e["sport"]: e for e in ev.events_from_posts(posts)}
        self.assertEqual(set(out), {"weightlifting", "athletics"})  # η μεταγραφή δεν είναι διοργάνωση
        w = out["weightlifting"]
        self.assertEqual((w["start"], w["end"]), ("2026-11-19", "2026-11-22"))
        self.assertEqual(w["title"], "Με στόχο τις διακρίσεις στο Πανελλήνιο Πρωτάθλημα ο ΠΑΟΚ στην Άρση Βαρών")
        self.assertEqual([p["url"] for p in w["posts"]], ["https://acpaok.gr/p1/", "https://acpaok.gr/p2/"])
        self.assertFalse(w["para"])
        a = out["athletics"]
        self.assertEqual(a["title"], "Μίτινγκ ΑμεΑ στο Καυτανζόγλειο")  # χωρίς το «Στίβος:»
        self.assertTrue(a["para"])
        self.assertEqual(a["id"], ev.event_id("athletics", D(2026, 12, 6), D(2026, 12, 6)))

    def test_merge_admin_wins_and_hides(self):
        auto = [{"id": "aaaaaaaaaaaa", "sport": "judo", "title": "Αυτόματο", "start": "2026-11-28", "end": "2026-11-29",
                 "para": False, "posts": [{"url": "u2", "date": "2026-11-22"}], "source": "acpaok"},
                {"id": "bbbbbbbbbbbb", "sport": "judo", "title": "Όχι διοργάνωση", "start": "2026-12-01", "end": "2026-12-01",
                 "para": False, "posts": [], "source": "acpaok"}]
        previous = [{"id": "aaaaaaaaaaaa", "sport": "judo", "title": "Πρώτος τίτλος", "start": "2026-11-28",
                     "end": "2026-11-29", "para": False, "posts": [{"url": "u1", "date": "2026-11-20"}], "source": "acpaok"},
                    {"id": "cccccccccccc", "sport": "boxing", "title": "Παλιά", "start": "2026-10-01", "end": "2026-10-02",
                     "posts": [], "source": "acpaok"}]
        admin = [{"id": "aaaaaaaaaaaa", "title": "Πανελλήνιο Τζούντο", "venue": "Ηλιούπολη", "para": True},
                 {"id": "bbbbbbbbbbbb", "hidden": True},
                 {"id": "dddddddddddd", "sport": "chess", "title": "Ατομικό Σκάκι", "start": "2026-12-10", "end": "2026-12-09"}]
        out = {e["id"]: e for e in ev.merge(auto, previous, admin)}
        self.assertNotIn("bbbbbbbbbbbb", out)
        self.assertIn("cccccccccccc", out)  # η παλιά αυτόματη μένει στα αποτελέσματα
        a = out["aaaaaaaaaaaa"]
        self.assertEqual((a["title"], a["venue"], a["para"]), ("Πανελλήνιο Τζούντο", "Ηλιούπολη", True))
        self.assertEqual([p["url"] for p in a["posts"]], ["u1", "u2"])
        self.assertEqual(out["dddddddddddd"]["end"], "2026-12-10")  # το τέλος όχι πριν από την αρχή
        self.assertEqual(out["dddddddddddd"]["source"], "admin")

    def test_ics_all_day_and_timed(self):
        events = [{"id": "x1", "sport": "swimming", "title": "Χειμερινό", "start": "2026-12-11", "end": "2026-12-13",
                   "para": True, "venue": "ΟΑΚΑ"},
                  {"id": "x2", "sport": "chess", "title": "Γρήγορο", "start": "2026-12-20", "end": "2026-12-20", "time": "17:30"}]
        ics = ev.build_ics("ΠΑΟΚ", events, "20261122T000000Z")
        self.assertIn("DTSTART;VALUE=DATE:20261211", ics)
        self.assertIn("DTEND;VALUE=DATE:20261214", ics)
        self.assertIn("(ΑμεΑ)", ics)
        self.assertIn("DTSTART;TZID=Europe/Athens:20261220T173000", ics)


if __name__ == "__main__":
    unittest.main()
