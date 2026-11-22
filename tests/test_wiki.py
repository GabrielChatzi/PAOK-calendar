"""Παλιές σεζόν ποδοσφαίρου από τη Wikipedia (wiki.py)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import wiki  # noqa: E402

PAGE = """{{Infobox football club season
| club = [[PAOK FC|PAOK]]
| league result = ''4th (1st at Playoffs)''
| cup1 = [[1999–2000 Greek Football Cup|Greek Cup]]
| cup1 result = '''Winners'''
| cup2 = [[UEFA Cup]]
| cup2 result = 1st round
| league topscorer = [[Zisis Vryzas]] (12)
}}
== Pre-season ==
{{footballbox collapsible
|round = [[Exhibition game|Friendly]]
|date = 2 August 1999
|team1 = [[Grazer AK]]
|score = 5–3
|team2 = [[PAOK FC|PAOK]]
}}
== Competitions ==
=== Alpha Ethniki ===
==== Matches ====
{{football box collapsible
|round = 1
|date = {{Start date|1999|9|12}}
|team1 = [[PAOK FC|PAOK]]
|score = 3–1 {{aet}}
|team2 = [[Olympiacos F.C.|Olympiacos]]
|goals1 = [[Zisis Vryzas|Vryzas]] {{goal|12||45+2|pen.}} <br> [[Giorgos Toursounidis|Toursounidis]] {{goal|80}}
|goals2 = {{goal|30}}
|stadium = [[Toumba Stadium]]
}}
=== Greek Cup ===
{{Footballbox collapsible
|round = Final
|date = Saturday, 6 May 2000
|team1 = [[AEK Athens F.C.|AEK Athens]]
|score = 0–2
|team2 = PAOK
|goals2 = * [[Zisis Vryzas|Vryzas]] {{goal}} {{goal}}
|location = [[Athens]]
}}
"""


class Wiki(unittest.TestCase):
    def test_matches(self):
        ms = wiki.season_matches(PAGE, 1999)
        self.assertEqual([(m["start"][:10], m["home"], m["away"], m["score"], m["competition"], m["round"]) for m in ms], [
            ("1999-09-12", "ΠΑΟΚ", "Olympiacos", "3-1", "Πρωτάθλημα", "1η αγωνιστική"),
            ("2000-05-06", "AEK Athens", "ΠΑΟΚ", "0-2", "Κύπελλο Ελλάδας", "Τελικός")])
        self.assertEqual(ms[0]["goals"]["home"], [{"name": "Vryzas", "min": "12"}, {"name": "Vryzas", "min": "45+2", "pen": True},
                                                 {"name": "Toursounidis", "min": "80"}])
        self.assertEqual(ms[0]["goals"]["away"], [{"name": "", "min": "30"}])
        self.assertEqual(ms[1]["goals"]["away"], [{"name": "Vryzas"}, {"name": "Vryzas"}])
        self.assertEqual(ms[0]["venue"], "Toumba Stadium")
        self.assertIn("1999%E2%80%932000_PAOK_FC_season", ms[0]["url"])

    def test_summary(self):
        self.assertEqual(wiki.season_summary(PAGE), {
            "league": "4η θέση (1η στα πλέι οφ)",
            "cups": [{"name": "Κύπελλο Ελλάδας", "result": "Κατάκτηση"}, {"name": "Κύπελλο UEFA", "result": "1ος γύρος"}],
            "topscorer": "Zisis Vryzas (12)"})

    def test_title(self):
        self.assertEqual(wiki.page_title(1985), "1985–86 PAOK FC season")
        self.assertEqual(wiki.page_title(1999), "1999–2000 PAOK FC season")


if __name__ == "__main__":
    unittest.main()
