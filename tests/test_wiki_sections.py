"""Περίληψη ανά σεζόν από τα άρθρα των τμημάτων (wiki_sections.py) και archive.py summaries."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import archive  # noqa: E402
import build_calendars as bc  # noqa: E402
import wiki_sections as ws  # noqa: E402

BC = """==Season-by-season==
{| class="wikitable"
|-
! style="color:white;" | Season
!style="color:white;"|[[Greek Basket League|{{color|white|Greek League}}]]
!style="color:white;"|[[Greek Basketball Cup|{{color|white|Greek Cup}}]]
!style="color:white;"|[[PAOK B.C. in international competitions|{{color|white|Europe}}]]
|-
| style="white-space:nowrap;" | '''1990–91'''
| bgcolor= silver|[[A1 1990–91|Runner Up]]
| [[Greek Cup 1991|Final]]
| [[FIBA Saporta Cup]] <br>[[1990–91 FIBA Saporta Cup|Champion]]
|-
| '''2008–09'''
| 7th place
| Last 16
| Not participated
|}
"""

GRID = """{| class="wikitable"
|-
!Θ.
!'''[[Πρωτάθλημα 1964-65|65]]'''
!'''99'''
!'''[[Πρωτάθλημα 1999-2000|00]]'''
|-
!1
|
|
|style="background:#000"|'''1'''
|-
!4
|'''4'''
|
|
|}"""


class Sections(unittest.TestCase):
    def test_vertical_bc(self):
        r = ws.vertical(BC)
        self.assertEqual(r["1990-91"], {"league": "2η θέση", "cups": [{"name": "Κύπελλο Ελλάδας", "result": "Φιναλίστ"},
                                                                      {"name": "FIBA Saporta Cup", "result": "Πρωταθλητής"}]})
        self.assertEqual(r["2008-09"], {"league": "7η θέση", "cups": [{"name": "Κύπελλο Ελλάδας", "result": "Φάση των 16"}]})

    def test_grid(self):
        self.assertEqual(ws.grid(GRID), {"1999-00": {"league": "Πρωταθλητής"}, "1964-65": {"league": "4η θέση"}})

    def test_bullets(self):
        r = ws.bullets("* 2018-19: Πρε Λιγκ 1η {{προβιβασμός}}\n* 2024-25: Βόλεϊ Λιγκ 2η\n* 1987-88: ")
        self.assertEqual(r, {"2018-19": {"league": "Πρε Λιγκ, 1η θέση (άνοδος)"}, "2024-25": {"league": "Βόλεϊ Λιγκ, 2η θέση"}})

    def test_archive_summaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = (bc.OUT_DIR, archive.ARCHIVE)
            bc.OUT_DIR = Path(tmp)
            archive.ARCHIVE = bc.OUT_DIR / "archive"
            try:
                archive.save({"season": "1990-91", "sections": {"football": {"matches": [], "summary": {
                    "league": "4η θέση", "source": "https://en.wikipedia.org/wiki/1990%E2%80%9391_PAOK_FC_season"}}}})
                archive.summaries({"basketball": {"1990-91": {"league": "2η θέση"}},
                                   "football": {"1990-91": {"league": "άλλο"}}})
                d = json.loads((archive.ARCHIVE / "1990-91.json").read_text(encoding="utf-8"))
                self.assertEqual(d["sections"]["basketball"]["summary"], {"league": "2η θέση"})
                self.assertEqual(d["sections"]["football"]["summary"]["league"], "4η θέση")  # η σελίδα σεζόν μένει
                idx = json.loads((archive.ARCHIVE / "index.json").read_text(encoding="utf-8"))
                self.assertTrue(idx["seasons"][0]["sections"]["basketball"]["summary"])
            finally:
                bc.OUT_DIR, archive.ARCHIVE = old


if __name__ == "__main__":
    unittest.main()
