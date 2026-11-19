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

    def test_u16(self):
        links = {"k15-nchc": {"fixtures": "a"}, "k16-u16-nchc": {"fixtures": "b"}}
        self.assertEqual(b.paokfc_team(links, "football-u16"), {"fixtures": "b"})
        self.assertEqual(b.paokfc_team({"k15-nchc": {}}, "football-u16"), {})
        season = SEASON.replace("k20-nchc", "k16-nchc")
        pages = {"https://www.paokfc.gr/programma-kai-apotelesmata/2026-2027/": season,
                 "https://www.paokfc.gr/programma-kai-apotelesmata/2026-2027/k16-nchc/k20-programma-16-nch/": FIXTURES,
                 "https://www.paokfc.gr/programma-kai-apotelesmata/2026-2027/k16-nchc/k20-apotelesmata/": ""}
        with mock.patch.object(b, "paokfc_fetch", lambda url, *a, **k: pages[url]):
            comps = {m.competition for m in b.paokfc_matches("football-u16", dt.date(2026, 11, 17))}
        self.assertEqual(comps, {"Super League 2 Κ19", "UEFA Youth League"})


class SL2(unittest.TestCase):
    """ΠΑΟΚ Β και Κ16 από το API του sl2.gr (δείγμα από τον Νοέμβριο του 2026)."""

    def setUp(self):
        import json
        with open(os.path.join(os.path.dirname(__file__), "fixtures_sl2.json"), encoding="utf-8") as f:
            d = json.load(f)
        paths = {"competitions": d["competitions"], "competitions/sl219a2627/matches": d["u19a_matches"],
                 "competitions/sl2-2627/matches": d["b_matches"], "competitions/sl219a2627/standings": d["u19a_standings"]}
        patcher = mock.patch.object(b, "sl2_json", lambda path: paths.get(path, []))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_u16(self):
        ms = {m.day: m for m in b.sl2_matches("football-u16", dt.date(2026, 11, 18))}
        first = ms[dt.date(2026, 10, 24)]
        self.assertEqual((first.home, first.away, first.score, first.time, first.competition, first.round),
                         ("ΠΑΟΚ", "Νίκη Βόλου", "1-1", dt.time(13, 45), "Super League 2 Κ19", "1η Αγωνιστική"))
        self.assertEqual(first.venue, "ΑΘΛΗΤΙΚΟ ΚΕΝΤΡΟ ΛΩΛΑΣ")
        self.assertTrue(first.away_logo.startswith("https://sl2-backend.sportsdata.gr/"))
        self.assertEqual(first.home_logo, "")
        later = ms[dt.date(2026, 11, 29)]  # χωρίς ορισμένη μέρα: η ημερομηνία της αγωνιστικής, χωρίς ώρα
        self.assertEqual((later.time, later.home, later.away, later.venue), (None, "ΠΑΟΚ", "Πανθρακικός", ""))

    def test_b(self):
        (m, *_rest) = sorted(b.sl2_matches("football-b", dt.date(2026, 11, 18)), key=lambda m: m.day)
        self.assertEqual((m.home, m.away, m.score, m.competition, m.tv), ("ΠΑΟΚ", "Ολυμπιακός Β", "1-1", "Super League 2", "ΕΡΤ"))

    def test_table(self):
        import standings
        with mock.patch.object(standings, "sl2_json", b.sl2_json), \
                mock.patch.object(standings, "sl2_competitions", lambda s: b.sl2_competitions(s, dt.date(2026, 11, 18))):
            (t,) = standings.sl2_table("football-u16")
        self.assertEqual(t["title"], "Super League 2 Κ19, Α' όμιλος")
        paok = [r for r in t["rows"] if r["paok"]][0]
        self.assertEqual((paok["pos"], paok["cells"][-1]), (4, "4"))


class Epesth(unittest.TestCase):
    """Βόλεϊ ακαδημίες από το epesth.gr: πρόγραμμα από PDF (κείμενο του pdftotext), σκορ από τη σελίδα."""
    PDF = """                             ΠΡΟΓΡΑΜΜΑ ΑΓΩΝΩΝ ΠΡΩΤΑΘΛΗΜΑΤΟΣ Κ18 ΑΓΟΡΙΩΝ (ΕΦΗΒΩΝ)
       ΗΜΕΡ/ΝΙΑ           ΓΗΠΕΔΟ                       ΩΡΑ                   ΣΥΝΑΝΤΗΣΗ                        AΠ.
1η Αγωνιστική
 Σάββατο 17/10/2026 Αλ. Νικολαΐδης                     15:00   ΠΗΓΑΣΟΣ ΠΟΛΙΧΝΗΣ - ΝΓΣΘ ΗΡΑΚΛΗΣ 1908            -
 Σάββατο 17/10/2026 Κλ. Βικελίδης                      20:00            ΑΣ ΑΡΗΣ - ΠΑΟΚ                         -
2η Αγωνιστική
 Σάββατο 31/10/2026 ΠΑΟΚ Sports Arena (Βοηθητικό)      18:00                ΠΑΟΚ - ΑΣ ΕΛΠΙΣ                    -
 5η Αγωνιστική
 Σάββατο 21/11/2026 Γ. Κατσάνης                        15:00   ΝΓΣΘ ΗΡΑΚΛΗΣ 1908 - ΠΑΟΚ                        -
"""
    PAGE = """<table><tr><td>1η Αγωνιστική</td><td>Σκορ</td></tr><tr><td>ΑΡΗΣ-ΠΑΟΚ</td><td>3-2</td></tr></table>
<table><tr><td>2η Αγωνιστική</td><td>Σκορ</td></tr><tr><td>ΠΑΟΚ-ΑΣ ΕΛΠΙΣ</td><td>0-3</td></tr></table>
<table><tr><td>5η Αγωνιστική</td><td>Σκορ</td></tr><tr><td>ΗΡΑΚΛΗΣ-ΠΑΟΚ</td><td></td></tr></table>
<table><tr><td>α.α</td><td>Ομάδα</td><td>Αγ</td><td>Ν</td><td>Η</td><td>Σετ</td><td>Β</td></tr>
<tr><td>1</td><td>ΑΣ ΕΛΠΙΣ</td><td>4</td><td>4</td><td>0</td><td>12-0</td><td>8</td></tr>
<tr><td>9</td><td>ΠΑΟΚ</td><td>4</td><td>0</td><td>4</td><td>4-12</td><td>4</td></tr></table>"""
    LIST = '<a href="https://epesth.gr/wp-content/uploads/2026/10/%CE%A0%CE%A1%CE%9F%CE%93%CE%A1%CE%91%CE%9C%CE%9C%CE%91-%CE%9A18-%CE%91%CE%93%CE%9F%CE%A1%CE%99%CE%91.pdf">x</a>'

    def run_section(self):
        pages = {"https://epesth.gr/programmata/": self.LIST, "https://epesth.gr/k18-agorion-2026-2027/": self.PAGE}
        with mock.patch.object(b, "fetch", lambda url, *a, **k: pages[url]), \
                mock.patch.object(b, "epesth_pdf_text", lambda url: self.PDF):
            return sorted(b.epesth_matches("volley-u18", dt.date(2026, 11, 19)), key=lambda m: m.day)

    def test_matches(self):
        ms = self.run_section()
        self.assertEqual([(m.home, m.away, m.score) for m in ms],
                         [("ΑΡΗΣ", "ΠΑΟΚ", "3-2"), ("ΠΑΟΚ", "ΕΛΠΙΣ", "0-3"), ("ΗΡΑΚΛΗΣ 1908", "ΠΑΟΚ", "")])
        self.assertEqual((ms[1].venue, ms[1].time, ms[1].round), ("ΠΑΟΚ Sports Arena (Βοηθητικό)", dt.time(18, 0), "2η αγωνιστική"))

    def test_table(self):
        import standings
        with mock.patch.object(standings, "fetch", lambda url, *a, **k: self.PAGE), \
                mock.patch.object(standings, "epesth_season", lambda: "2026-2027"):
            (t,) = standings.epesth_table("volley-u18")
        self.assertEqual([(r["pos"], r["paok"], r["cells"][-1]) for r in t["rows"]], [(1, False, "8"), (9, True, "4")])


if __name__ == "__main__":
    unittest.main()


class EpesthCrests(unittest.TestCase):
    def test_match(self):
        import build_calendars as b
        old = b._EPESTH_CRESTS
        b._EPESTH_CRESTS = [(set(b.epesth_words(n)), {w[:5] for w in b.epesth_words(n) if len(w) > 3}, u) for n, u in [
            ("Α.Σ. AΡΗΣ", "aris"), ("Ν.Γ.Σ ΘΕΣΣΑΛΟΝΙΚΗΣ ΗΡΑΚΛΗΣ 1908", "iraklis"), ("Χ.Α.Ν.Θ.", "hanth"),
            ("Π.Ο. ΝΕΩΝ ΜΟΥΔΑΝΙΩΝ", "moudania")]]
        try:
            self.assertEqual(b.epesth_crest("ΗΡΑΚΛΗΣ 1908"), "iraklis")
            self.assertEqual(b.epesth_crest("ΧΑΝΘ"), "hanth")
            self.assertEqual(b.epesth_crest("ΠΟ ΜΟΥΔΑΝΙΩΝ"), "moudania")
            self.assertEqual(b.epesth_crest("ΑΡΗΣ"), "aris")
            self.assertEqual(b.epesth_crest("ΑΓΝΩΣΤΟΣ"), "")
        finally:
            b._EPESTH_CRESTS = old


class Ekasth(unittest.TestCase):
    def setUp(self):
        import json
        import build_calendars as b
        self.b = b
        game = lambda gid, date, home, away, hs, as_, state: {
            "id": gid, "date": date, "state": state, "stadium": "PAOK SPORTS ARENA (ΠΑΛΑΤΑΚΙ)", "group": "1ος όμιλος",
            "home": {"name": home, "logo": "bgapi.php?action=img&t=h", "score": hs},
            "away": {"name": away, "logo": "bgapi.php?action=img&t=a", "score": as_}}
        chans = {"channels": [{"id": "P", "name": "ΠΑΙΔΩΝ 2026-2027"}, {"id": "G", "name": "GEN A RISING STARS U16"}]}
        paidon = {"channel": {"id": "P"}, "groups": [{"name": "1ος όμιλος", "standings": [
            {"team": "ΑΣ ΠΑΟΚ 1", "logo": "x", "played": 6, "wins": 6, "losses": 0, "diff": 150, "points": 12, "pos": 1},
            {"team": "ΧΑΝΘ", "logo": "bgapi.php?action=img&t=c", "played": 6, "wins": 3, "losses": 3, "diff": -4, "points": 9, "pos": 2}],
            "matchdays": [{"name": "1 ΑΓΩΝΙΣΤΙΚΗ", "games": [
                game("g1", "2026-10-07T20:00:00+03:00", "ΑΣ ΠΑΟΚ 1", "ΧΑΝΘ", 72, 45, "Completed"),
                game("g2", "2026-12-09T00:00:00+02:00", "ΧΑΝΘ", "ΑΣ ΠΑΟΚ 1", None, None, "Scheduled"),
                game("g3", "2026-12-10T20:00:00+02:00", "ΑΣ ΠΑΟΚ 2", "ΧΑΝΘ", None, None, "Scheduled")]}]}]}
        gen = {"channel": {"id": "G"}, "groups": [{"name": "ΠΡΟΚΡΙΜΑΤΙΚΗ ΦΑΣΗ · ΗΜΙΤΕΛΙΚΗ ΦΑΣΗ", "standings": [], "matchdays": [
            {"name": "1η ΑΓΩΝΙΣΤΙΚΗ", "games": [game("g4", "2026-09-14T17:30:00+03:00", "ΧΑΝΘ", "ΑΣ ΠΑΟΚ 1", 72, 81, "Completed")]}]}]}
        data = {"channels": chans, "P": paidon, "G": gen}

        def fake(url, *a, **k):
            q = dict(urllib.parse.parse_qsl(url.split("?", 1)[1]))
            return json.dumps(data["channels"] if q["action"] == "channels" else data[q["ch"]])
        import urllib.parse
        self.old, b.fetch = b.fetch, fake
        b._EKASTH.clear()

    def tearDown(self):
        self.b.fetch = self.old
        self.b._EKASTH.clear()

    def test_matches(self):
        ms = sorted(self.b.ekasth_matches("basketball-u16"), key=lambda m: m.start())
        self.assertEqual([m.uid for m in ms], ["basketball-u16-ek-g4", "basketball-u16-ek-g1", "basketball-u16-ek-g2"])
        self.assertEqual((ms[0].home, ms[0].away, ms[0].score, ms[0].round), ("ΧΑΝΘ", self.b.PAOK, "72-81", "Ημιτελική φάση, 1η αγωνιστική"))
        self.assertEqual(ms[0].competition, "Gen A Rising Stars U16 (ΕΚΑΣΘ)")
        self.assertEqual((ms[1].score, ms[1].round, ms[1].competition), ("72-45", "1η αγωνιστική", "Παίδων (ΕΚΑΣΘ)"))
        self.assertIsNone(ms[2].time)  # 00:00 = ώρα που δεν έχει οριστεί
        self.assertEqual(ms[2].home_logo, self.b.EKASTH + "bgapi.php?action=img&t=h")

    def test_table(self):
        import standings as st
        st.fetch = self.b.fetch
        t = st.ekasth_table("basketball-u16")
        self.assertEqual(t[0]["title"], "Παίδων (ΕΚΑΣΘ), 1ος όμιλος")
        self.assertEqual([r["cells"] for r in t[0]["rows"]], [["6", "6", "0", "+150", "12"], ["6", "3", "3", "-4", "9"]])
        self.assertTrue(t[0]["rows"][0]["paok"])


class Epsm(unittest.TestCase):
    PROGRAM = """<p>ΠΡΟΓΡΑΜΜΑ  ΑΓΩΝΩΝ ΠΡΩΤΑΘΛΗΜΑΤΩΝ ΥΠΟΔΟΜΩΝ<br>
ΣΑΒΒΑΤΟΥ 21ΝΟΕΜΒΡΙΟΥ 2026<br><br>
ΚΑΤΗΓΟΡΙΑ Κ-15 LEAGUE1 (2012 και νεότεροι)<br>
Κ15 LEAGUE 1(5η αγωνιστική)<br>--------------------------<br>
ΣΚΙΟΥΡΟΙ (1) - ΠΑΕ ΠΑΟΚ Κ14<br>
</font><b>Γήπεδο: </b> ΠΥΛΑΙΑΣ ΔΗΜΟΤΙΚΟ - Πλαστικό - <b>ώρα: </b>09.00<br>
Γιατρός: Χ.<br>
ΠΑΕ ΠΑΟΚ Κ14 – ΔΟΞΑ ------ΘΑ ΓΙΝΕΙ ΚΥΡΙΑΚΗ 22-11-2026<br>
</font><b>Γήπεδο: </b> ΤΣΑΚ ΜΠΑΜ ΑΡΕΝΑ - <b>ώρα: </b> 12.30<br>
ΚΑΤΗΓΟΡΙΑ Κ-15 ΓΥΝΑΙΚΩΝ (2012 και νεότερες)<br>
Κ15 ΓΥΝΑΙΚΩΝ(4η αγωνιστική)<br>
ΑΣ ΠΑΟΚ (1) - ΑΟ ΛΕΟΝΤΕΣ ----- ΑΝΑΒΟΛΗ<br>
</p>"""
    ROUNDS = ("<b>1</b><sup>η</sup> ΑΓΩΝΙΣΤΙΚΗ<br><td>ΠΑΕ ΠΑΟΚ Κ14  - ΖΗΤΑ ΕΠΤΑ (1) 4 - 1</td>"
              "<td>Α - Β 1 - 0</td><b>5</b><sup>η</sup> ΑΓΩΝΙΣΤΙΚΗ<td>ΣΚΙΟΥΡΟΙ (1) - ΠΑΕ ΠΑΟΚ Κ14 -</td>"
              "<b>6</b><sup>η</sup> ΑΓΩΝΙΣΤΙΚΗ<td>ΠΑΕ ΠΑΟΚ Κ14 - ΟΛΥΜΠΙΑΚΟΣ -</td>")

    def test_program(self):
        import build_calendars as b
        rows = b.epsm_program(self.PROGRAM)
        self.assertEqual([(r["cat"], r["round"], r["day"], r["time"], r["home"], r["away"], r["status"]) for r in rows], [
            ("Κ15LEAGUE1", "5", "2026-11-21", "09:00", "ΣΚΙΟΥΡΟΙ (1)", "ΠΑΕ ΠΑΟΚ Κ14", ""),
            ("Κ15LEAGUE1", "5", "2026-11-22", "12:30", "ΠΑΕ ΠΑΟΚ Κ14", "ΔΟΞΑ", ""),
            ("Κ15ΓΥΝΑΙΚΩΝ", "4", "2026-11-21", "", "ΑΣ ΠΑΟΚ (1)", "ΑΟ ΛΕΟΝΤΕΣ", "postponed")])
        self.assertEqual(rows[0]["venue"], "ΠΥΛΑΙΑΣ ΔΗΜΟΤΙΚΟ - Πλαστικό")

    def test_matches(self):
        import build_calendars as b
        rounds = b.epsm_rounds(self.ROUNDS)
        self.assertEqual(rounds[0], {"round": "1", "home": "ΠΑΕ ΠΑΟΚ Κ14", "away": "ΖΗΤΑ ΕΠΤΑ (1)", "score": "4-1"})
        ms = b.epsm_matches("football-u14", {"programs": {"1": b.epsm_program(self.PROGRAM)}}, rounds)
        by = {m.round: m for m in ms}
        self.assertNotIn("1η αγωνιστική", by)  # χωρίς γνωστή μέρα για την 1η αγωνιστική
        self.assertEqual((by["5η αγωνιστική"].home, by["5η αγωνιστική"].time), ("ΣΚΙΟΥΡΟΙ (1)", dt.time(9)))
        self.assertEqual((by["6η αγωνιστική"].day, by["6η αγωνιστική"].time), (dt.date(2026, 11, 28), None))


class KoeWatch(unittest.TestCase):
    def test_relevant(self):
        import koe_watch as k
        self.assertTrue(k.relevant("https://koe.org.gr/article/x", "Προκήρυξη Πανελληνίου Πρωταθλήματος Παίδων 2026-27"))
        self.assertTrue(k.relevant("https://koe.org.gr/article/to-programma-ton-korasidon", "ΥΔΑΤΟΣΦΑΙΡΙΣΗ"))
        self.assertFalse(k.relevant("https://koe.org.gr/article/x", "ΠΑΓΚΟΣΜΙΟ ΠΡΩΤΑΘΛΗΜΑ ΝΕΑΝΙΔΩΝ Κ18: αναχώρησε η αποστολή"))
        self.assertFalse(k.relevant("https://koe.org.gr/article/x", "Κλήση 19 αθλητριών"))


class Crests(unittest.TestCase):
    def test_kind(self):
        import crests
        self.assertEqual(crests.kind(b"\x89PNG\r\n"), "png")
        self.assertEqual(crests.kind(b"\xff\xd8\xff"), "jpg")
        self.assertEqual(crests.kind(b"RIFF\0\0\0\0WEBPVP8"), "webp")
        self.assertEqual(crests.kind(b"<?xml version='1.0'?><svg></svg>"), "svg")
        self.assertEqual(crests.kind(b"<!DOCTYPE html><title>403</title>"), "")

    def test_same_club(self):
        import crests
        same = lambda a, b: crests.same_club(crests.words(a), crests.words(b))  # noqa: E731
        self.assertTrue(same("Μ.ΑΛΕΞΑΝΔΡΟΣ ΘΕΣΣΑΛΟΝΙΚΗΣ", "Γ.Σ. Μέγας Αλέξανδρος Θεσσαλονίκης"))
        self.assertTrue(same("ΜΑΚΕΔΟΝΙΚΟΣ (1)", "Α.Σ. Μακεδονικός"))
        self.assertTrue(same("ΠΑΟ ΚΟΥΦΑΛΙΩΝ", "Π.Α.Ο. Κουφαλίων"))
        self.assertFalse(same("ΙΩΝΙΚΟΣ", "Α.Ο. Ιωνικός Νίκαιας"))  # μία λέξη: μόνο ακριβώς ίδιο
        self.assertFalse(same("ΑΙΑΝΤΑΣ ΠΥΛΑΙΑΣ", "Α.Ε. Πυλαίας"))
        self.assertFalse(same("ΑΣ ΠΟΔ. ΤΟΥΜΠΑΣ", "Μ.Ε.Ν. ΤΟΥΜΠΑΣ"))
        self.assertFalse(same("ΑΟ ΚΑΡΔΙΑΣ", "ΚΑΡΔΙΤΣΑ"))

    def test_rewrite(self):
        import json
        import tempfile
        from pathlib import Path
        import crests
        with tempfile.TemporaryDirectory() as d:
            docs = Path(d)
            (docs / "matches.json").write_text(json.dumps({
                "sections": [{"key": "football-u19", "academy": True}, {"key": "football"}],
                "matches": [{"section": "football-u19", "homeLogo": "https://www.paokfc.gr/a.png", "awayLogo": ""},
                            {"section": "football", "homeLogo": "https://espn.com/b.png", "awayLogo": ""}]}))
            (docs / "standings.json").write_text(json.dumps({"football-u19": [{"rows": [{"logo": "https://www.paokfc.gr/a.png"}]}]}))
            seen = []

            def fake_run(cmd, **k):
                seen.append(cmd[-1])
                return mock.Mock(returncode=0, stdout=b"\x89PNG fake")
            with mock.patch.object(crests, "DOCS", docs), mock.patch.object(crests, "DIR", docs / "crests"), \
                    mock.patch.object(crests.subprocess, "run", fake_run):
                crests.main()
                crests.main()  # δεύτερη φορά: από το αντίγραφο, χωρίς κατέβασμα
            m = json.loads((docs / "matches.json").read_text())["matches"]
            self.assertTrue(m[0]["homeLogo"].startswith(crests.SITE) and m[0]["homeLogo"].endswith(".png"))
            self.assertEqual(m[1]["homeLogo"], "https://espn.com/b.png")  # μόνο οι ακαδημίες
            st = json.loads((docs / "standings.json").read_text())
            self.assertEqual(st["football-u19"][0]["rows"][0]["logo"], m[0]["homeLogo"])
            self.assertEqual(seen, ["https://www.paokfc.gr/a.png"])

