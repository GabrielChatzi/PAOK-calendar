"""Β' ομάδα και ακαδημίες από το paokfc.gr (build_calendars.paokfc_*)."""
import datetime as dt
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.pop("PUSH", None)

import build_calendars as b  # noqa: E402

SEASON = '''<a href="https://www.paokfc.gr/programma-kai-apotelesmata/2026-2027/k20-nchc/k20-programma-16-nch/">Π</a>
<a href="https://www.paokfc.gr/programma-kai-apotelesmata/2026-2027/k20-nchc/k20-apotelesmata/">Α</a>
<a href="https://www.paokfc.gr/programma-kai-apotelesmata/2026-2027/k20-nchc/vathmologia-u20/">Β</a>'''

# Αποτέλεσμα (εκτός: πρώτα το σκορ του αντιπάλου) και λάθος έτος στην πηγή.
RESULTS = '''
<li class="away  youth-league"><div class="col-lg-12 away"><div class="match-away-right">
<!--<div class="row"><span>Youth League | 28.10.2026</span></div>-->
<div class="row"><span>Youth League | 28.10.2026 ,17:00</span></div>
<div class="row"><div class="one-third rival-team">HSK Zrinjski</div>
<div class="one-third final-score"><!--<span class="rival-score">1</span>--><span class="rival-score">1</span>
<span class="score-separator"> - </span><span class="paok-score">3</span></div>
<div class="one-third team-logos"><img src="https://www.paokfc.gr/wp-content/uploads/z.png" alt=""/>
<img src="https://www.paokfc.gr/wp-content/themes/paokv2/images/logo-paok-small.png" alt=""/></div></div>
<a class="fr-buy" href="https://www.paokfc.gr/matches/k19-hsk-zrinjski-paok-27/#match-report">Match Report</a>
</div></div></li>
<li class="home  super-league"><div class="col-lg-12 home"><div class="match-home-right">
<div class="row"><span>Super League | 27.09.2006 ,11:45</span></div>
<div class="row"><div class="one-third rival-team">ΠΟΤ Ηρακλής</div>
<div class="one-third final-score"><span class="paok-score">4</span><span class="score-separator"> - </span><span class="rival-score">0</span></div>
</div></div></div></li>'''

# Πρόγραμμα, στη δεύτερη μορφή της πηγής: χωρίς ημερομηνία (μόνο στο σχόλιο), με ώρα, και ένας
# αγώνας που αναβλήθηκε (η ημερομηνία του σχολίου πέρασε). Η λίστα εμφανίζεται δύο φορές.
FIXTURES = '''
<li class="home  super-league"><div>
<!--<section class="row fr-info-row"><span>Super League | 21.11.2026</span></section>-->
<section class="row fr-info-row"><span>Super League | Ημερομηνία: N/A</span></section>
<div class="match-between"><span class="rival-teamname">PAOK</span><span class="score-separator"> - </span>
<span class="home-teamname">Kifisia</span></div></div></li>
<li class="away  youth-league"><div>
<section class="row fr-info-row"><span>Youth League | 25.11.2026 ,19:00</span></section>
<div class="match-between"><span class="rival-teamname">Hoffenheim</span><span class="score-separator"> - </span>
<span class="home-teamname">PAOK</span></div></div></li>
<li class="away  super-league"><div>
<!--<section class="row fr-info-row"><span>Super League | 07.11.2026</span></section>-->
<section class="row fr-info-row"><span>Super League | Ημερομηνία: N/A</span></section>
<div class="match-between"><span class="rival-teamname">Olympiakos</span><span class="score-separator"> - </span>
<span class="home-teamname">PAOK</span></div></div></li>'''


class Academy(unittest.TestCase):
    def matches(self):
        pages = {
            "https://www.paokfc.gr/programma-kai-apotelesmata/2026-2027/": SEASON,
            "https://www.paokfc.gr/programma-kai-apotelesmata/2026-2027/k20-nchc/k20-programma-16-nch/": FIXTURES * 2,
            "https://www.paokfc.gr/programma-kai-apotelesmata/2026-2027/k20-nchc/k20-apotelesmata/": RESULTS * 2,
        }
        with mock.patch.object(b, "paokfc_fetch", lambda url, *a, **k: pages[url]):
            ms = b.paokfc_matches("football-u19", dt.date(2026, 11, 17))
        return {(m.home, m.away): m for m in ms}

    def test_parse(self):
        ms = self.matches()
        self.assertEqual(len(ms), 4)  # χωρίς διπλά, χωρίς τον αγώνα που αναβλήθηκε
        z = ms[("HSK Zrinjski", "ΠΑΟΚ")]
        self.assertEqual((z.score, z.competition, z.time), ("1-3", "UEFA Youth League", dt.time(17, 0)))
        self.assertEqual(z.url, "https://www.paokfc.gr/matches/k19-hsk-zrinjski-paok-27/")
        self.assertEqual(z.home_logo, "https://www.paokfc.gr/wp-content/uploads/z.png")
        h = ms[("ΠΑΟΚ", "Ηρακλής")]
        self.assertEqual((h.day, h.score, h.competition), (dt.date(2026, 9, 27), "4-0", "Super League Κ19"))
        k = ms[("ΠΑΟΚ", "Κηφισιά")]
        self.assertEqual((k.day, k.time), (dt.date(2026, 11, 21), None))  # μέρα αγωνιστικής, ώρα αναμένεται
        self.assertNotIn(("Ολυμπιακός", "ΠΑΟΚ"), ms)

    def test_uid_survives_date_change(self):
        ms = self.matches()
        uid = ms[("ΠΑΟΚ", "Κηφισιά")].uid
        pages_date = FIXTURES.replace("Super League | Ημερομηνία: N/A</span></section>\n<div class=\"match-between\"><span class=\"rival-teamname\">PAOK",
                                      "Super League | 22.11.2026 ,13:00</span></section>\n<div class=\"match-between\"><span class=\"rival-teamname\">PAOK")
        self.assertNotEqual(pages_date, FIXTURES)
        with mock.patch.object(b, "paokfc_fetch", lambda url, *a, **k: {
                "https://www.paokfc.gr/programma-kai-apotelesmata/2026-2027/": SEASON}.get(url, pages_date if "programma-16" in url else "")):
            moved = {(m.home, m.away): m for m in b.paokfc_matches("football-u19", dt.date(2026, 11, 17))}
        self.assertEqual(moved[("ΠΑΟΚ", "Κηφισιά")].day, dt.date(2026, 11, 22))
        self.assertEqual(moved[("ΠΑΟΚ", "Κηφισιά")].uid, uid)

    def test_names(self):
        self.assertEqual(b.paokfc_name("Eλλάς Σύρου "), "Ελλάς Σύρου")  # λατινικό E
        self.assertEqual(b.paokfc_name("Ολυμπιακός B"), "Ολυμπιακός Β")
        self.assertEqual(b.paokfc_name("Asteras AKTOR B"), "Αστέρας Τρίπολης Β")
        self.assertEqual(b.paokfc_name("Hoffenheim"), "Hoffenheim")

    def test_hidden_sections(self):
        for key in b.ACADEMY:
            self.assertTrue(b.SECTIONS[key]["academy"])
            self.assertIn(key, b.SOURCES)

    def test_manual_score(self):
        import json, tempfile, pathlib
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "manual.json"
            path.write_text(json.dumps([{"section": "football-u17", "date": "2026-11-22", "time": "15:00",
                                         "home": "Κηφισιά", "away": "ΠΑΟΚ", "score": "0-2"}]), encoding="utf-8")
            with mock.patch.object(b, "MANUAL_PATH", path):
                (m,) = b.manual_matches("football-u17", [])
        self.assertEqual((m.score, m.paok_home, m.time), ("0-2", False, dt.time(15, 0)))

    def test_custom_matches(self):
        c = {"section": "football-u15", "uid": "football-u15-custom-a1b2c3d4e5f6", "start": "2026-11-30T12:30:00+02:00",
             "timeKnown": True, "home": "Ηρακλής", "away": "ΠΑΟΚ", "paokHome": False, "competition": "Super League Κ15",
             "score": "0-3"}
        official = b.Match(section="football-u15", uid="x", day=dt.date(2026, 11, 29), time=None, home="Ηρακλής",
                           away="ΠΑΟΚ", paok_home=False)
        with mock.patch.dict(b._ADMIN, {"entries": {}, "live": {}, "custom": [c]}):
            (m,) = b.custom_matches("football-u15", [])
            self.assertEqual((m.day, m.time, m.score, m.home), (dt.date(2026, 11, 30), dt.time(12, 30), "0-3", "Ηρακλής"))
            self.assertEqual(m.to_json()["nt"], b.match_topic_id(c["uid"]))
            # Η πηγή έχει ήδη τον αγώνα (μέρα ±1, ίδια έδρα): μετρά εκείνος, χωρίς διπλό.
            self.assertEqual(b.custom_matches("football-u15", [official]), [])
            self.assertEqual(b.custom_matches("football-u17", []), [])


if __name__ == "__main__":
    unittest.main()
