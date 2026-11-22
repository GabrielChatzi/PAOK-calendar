"""Αρχείο σεζόν (archive.py) και τρόπαια (trophies.py)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.pop("PUSH", None)

import archive  # noqa: E402
import build_calendars as bc  # noqa: E402
import trophies as tr  # noqa: E402


def m(uid, start, section="volley", score="", **kw):
    return {"uid": uid, "nt": uid[-4:], "section": section, "start": start, "timeKnown": True, "home": "ΠΑΟΚ",
            "away": "Άρης", "paokHome": True, "venue": "", "competition": "Volley League", "round": "1η",
            "score": score, "live": {"src": "x"}, "stats": {"big": 1}, **kw}


class Archive(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = (bc.OUT_DIR, archive.ARCHIVE)
        bc.OUT_DIR = Path(self.tmp.name)
        archive.ARCHIVE = bc.OUT_DIR / "archive"

    def tearDown(self):
        bc.OUT_DIR, archive.ARCHIVE = self.old
        self.tmp.cleanup()

    def write(self, matches, standings):
        (bc.OUT_DIR / "matches.json").write_text(json.dumps({"matches": matches}), encoding="utf-8")
        (bc.OUT_DIR / "standings.json").write_text(json.dumps(standings), encoding="utf-8")

    def test_season_of(self):
        self.assertEqual(archive.season_of("2026-06-30T20:00:00+03:00"), "2025-26")
        self.assertEqual(archive.season_of("2026-07-01T20:00:00+03:00"), "2026-27")
        self.assertEqual(archive.season_label(1999), "1999-00")

    def test_snapshot_keeps_scores_and_slims(self):
        table = [{"title": "Volley League", "columns": [], "rows": []}]
        self.write([m("v-1", "2026-10-03T18:00:00+03:00", score="3-1"), m("v-2", "2026-12-03T18:00:00+02:00")],
                   {"volley": table})
        archive.snapshot()
        d = json.loads((archive.ARCHIVE / "2026-27.json").read_text(encoding="utf-8"))
        sec = d["sections"]["volley"]
        self.assertEqual(len(sec["matches"]), 2)
        self.assertNotIn("live", sec["matches"][0])
        self.assertNotIn("stats", sec["matches"][0])
        self.assertEqual(sec["standings"], table)
        # Η επόμενη ενημέρωση χάνει το σκορ (π.χ. η πηγή δεν απαντά): το αρχείο το κρατά.
        self.write([m("v-1", "2026-10-03T18:00:00+03:00", score="")], {"volley": table})
        archive.snapshot()
        d = json.loads((archive.ARCHIVE / "2026-27.json").read_text(encoding="utf-8"))
        self.assertEqual(next(x for x in d["sections"]["volley"]["matches"] if x["uid"] == "v-1")["score"], "3-1")
        idx = json.loads((archive.ARCHIVE / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["seasons"][0]["season"], "2026-27")
        self.assertEqual(idx["seasons"][0]["sections"]["volley"], {"matches": 2, "standings": True})

    def test_standings_go_to_season_of_last_played_match(self):
        # Ιούλιος: η νέα σεζόν δεν έχει αγώνες ακόμα, η βαθμολογία είναι της προηγούμενης.
        table = [{"title": "Handball Premier", "columns": [], "rows": []}]
        self.write([m("h-1", "2026-05-10T18:00:00+03:00", section="handball", score="30-25"),
                    m("h-2", "2026-09-20T18:00:00+03:00", section="handball")], {"handball": table})
        archive.snapshot()
        old = json.loads((archive.ARCHIVE / "2025-26.json").read_text(encoding="utf-8"))
        new = json.loads((archive.ARCHIVE / "2026-27.json").read_text(encoding="utf-8"))
        self.assertEqual(old["sections"]["handball"]["standings"], table)
        self.assertNotIn("standings", new["sections"]["handball"])

    def test_backfill_keeps_only_season_matches(self):
        class FakeMatch:
            def __init__(self, d): self.d = d
            def to_json(self): return self.d
        seen = []

        def getter():
            seen.append(bc.season_start_year())
            return [FakeMatch(m("v-old", "2023-11-01T18:00:00+02:00", score="3-0")),
                    FakeMatch(m("v-now", "2026-11-01T18:00:00+02:00"))]
        real = bc.SOURCES
        bc.SOURCES = {"volley": [("test", getter)]}
        try:
            import standings as st
            real_st = st.STANDINGS
            st.STANDINGS = {"volley": lambda: [{"title": "VL 2023-24", "columns": [], "rows": []}]}
            try:
                archive.backfill(2023)
            finally:
                st.STANDINGS = real_st
        finally:
            bc.SOURCES = real
        self.assertEqual(seen, [2023])
        self.assertIsNone(bc.ARCHIVE_YEAR)
        self.assertNotEqual(bc.season_start_year(), 2023)
        d = json.loads((archive.ARCHIVE / "2023-24.json").read_text(encoding="utf-8"))
        self.assertEqual([x["uid"] for x in d["sections"]["volley"]["matches"]], ["v-old"])
        self.assertEqual(d["sections"]["volley"]["standings"][0]["title"], "VL 2023-24")
        self.assertTrue(d["sections"]["volley"]["backfilled"])


class Trophies(unittest.TestCase):
    def test_season_format(self):
        text = ("Κύπελλο Ελλάδος 2001-2002 Πρωτάθλημα Ελλάδος 2001-2002 Πρωτάθλημα Ελλάδος 2005-2006 "
                "Σούπερ Καπ 2023 Κύπελλο Ελλάδος 2023-2024")
        t, p, n = tr.parse_trophy_text(text)
        got = {x["name"]: x["years"] for x in t}
        self.assertEqual(got, {"Κύπελλο Ελλάδας": ["2001-02", "2023-24"], "Πρωτάθλημα Ελλάδας": ["2001-02", "2005-06"],
                               "Σούπερ Καπ": ["2023"]})
        self.assertEqual((p, n), ([], []))

    def test_parentheses_and_places(self):
        text = ("7 Πρωταθλήματα Ελλάδος Ανδρών (2006, 2017, 2019) 6 Πανελλήνια πρωταθλήματα εφήβων (2004, 2005) "
                "και 1 Πανελλήνιο πρωτάθλημα παίδων (2012) Πανελλήνιες Θέσεις 2η θέση Άνδρες (2004, 2005)")
        t, p, _ = tr.parse_trophy_text(text)
        self.assertEqual({x["name"]: x["years"] for x in t}, {
            "Πρωτάθλημα Ελλάδας Ανδρών": ["2006", "2017", "2019"], "Πανελλήνιο Πρωτάθλημα εφήβων": ["2004", "2005"],
            "Πανελλήνιο Πρωτάθλημα παίδων": ["2012"]})
        self.assertEqual(p, [{"name": "2η θέση Άνδρες", "years": ["2004", "2005"]}])

    def test_winners_wording_notes_and_glued_years(self):
        text = ("Πρωταθλητές Ελλάδος Παίδων 2016 Πρωταθλητής Ελλάδος Παίδων 2024 Συμμετοχή στο Παγκόσμιο Κύπελλο "
                "Συλλόγων στο ISFAHAN – IRAN το 2017. 2η θέση Εφήβων 20253η θέση Παμπαίδων 2025")
        t, p, n = tr.parse_trophy_text(text)
        self.assertEqual(t, [{"name": "Πρωτάθλημα Ελλάδας Παίδων", "years": ["2016", "2024"]}])
        self.assertEqual(p, [{"name": "2η θέση Εφήβων", "years": ["2025"]}, {"name": "3η θέση Παμπαίδων", "years": ["2025"]}])
        self.assertEqual(n, ["Συμμετοχή στο Παγκόσμιο Κύπελλο Συλλόγων στο ISFAHAN – IRAN το 2017"])

    def test_trophy_block(self):
        html = "<h2>ΤΡΟΠΑΙΟΘΗΚΗ</h2><p>Futsal League 2023-2024</p><h2>ΡΟΗ ΕΙΔΗΣΕΩΝ</h2><p>Νέα 2026</p>"
        self.assertEqual(tr.trophy_block(html), "Futsal League 2023-2024")
        self.assertIsNone(tr.trophy_block("<p>τίποτα</p>"))

    def test_static_sections_exist(self):
        for key in tr.STATIC:
            self.assertIn(key, bc.SECTIONS)
        for key in tr.ACPAOK_PAGES.values():
            if not key.startswith("event:"):
                self.assertIn(key, bc.SECTIONS)


if __name__ == "__main__":
    unittest.main()
