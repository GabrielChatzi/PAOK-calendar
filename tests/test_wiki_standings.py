"""Βαθμολογίες παλιών σεζόν από τη Wikipedia (wiki_standings.py)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.pop("PUSH", None)

import wiki_standings as ws  # noqa: E402

TEAMS = ["Ολυμπιακός", "Π.Α.Ο.Κ.", "Άρης", "Χανιά", "Πατρών"]


class ParseTest(unittest.TestCase):
    def test_two_row_header(self):
        head = ("<tr><th rowspan=2>Θέση</th><th rowspan=2>Ομάδα</th><th colspan=4>Σύνολο</th><th colspan=2>Εντός</th></tr>"
                "<tr><th>Βαθ.</th><th>Ν.</th><th>Ι.</th><th>Η.</th><th>Ν</th><th>Η</th></tr>")
        body = "".join(f"<tr><td>{i}</td><td>{t}</td><td>{30 - i}</td><td>{9 - i}</td><td>1</td><td>{i}</td><td>1</td><td>1</td></tr>"
                       for i, t in enumerate(TEAMS, 1))
        kinds, rows = ws.standings_from_html("<div><table><tr><td><table>" + head + body + "</table></td></tr></table></div>")
        self.assertEqual(kinds, ["w", "d", "l", "pts"])
        self.assertEqual(rows[1], {"pos": 2, "team": "Π.Α.Ο.Κ.", "raw": "Π.Α.Ο.Κ.", "w": "7", "d": "1", "l": "2", "pts": "28"})

    def test_group_title_and_unlabelled_team(self):
        head = ("<tr><th colspan=7>Βαθμολογία Κανονικής</th></tr><tr><th></th><th>Α1 Εθνική Κατηγορία</th><th>Βαθμ</th>"
                "<th>Αγων</th><th>Νικ</th><th>Ηττ</th><th>Πόντοι</th></tr>")
        body = "".join(f"<tr><td>{i}</td><td>{t}</td><td>{30 - i}</td><td>10</td><td>{9 - i}</td><td>{i}</td><td>800-700</td></tr>"
                       for i, t in enumerate(TEAMS, 1))
        kinds, rows = ws.standings_from_html("<table>" + head + body + "</table>")
        t = ws.to_table("basketball-women", "Πρωτάθλημα καλαθοσφαίρισης Α1 εθνικής κατηγορίας γυναικών 2013-2014", "u", kinds, rows)
        self.assertEqual(t["columns"], ["Αγ", "Ν", "Η", "Πόντοι", "Β"])
        self.assertEqual(t["title"], "Πρωτάθλημα καλαθοσφαίρισης Α1 εθνικής κατηγορίας γυναικών")
        self.assertEqual(t["rows"][1]["cells"], ["10", "7", "2", "800-700", "28"])
        self.assertTrue(t["rows"][1]["paok"])
        self.assertEqual(t["rows"][1]["team"], "ΠΑΟΚ")

    def test_no_paok_no_table(self):
        head = "<tr><th>Θέση</th><th>Ομάδα</th><th>Β</th><th>Ν</th></tr>"
        body = "".join(f"<tr><td>{i}</td><td>Ομάδα {i}</td><td>{i}</td><td>1</td></tr>" for i in range(1, 7))
        self.assertIsNone(ws.standings_from_html("<table>" + head + body + "</table>"))

    def test_season_start(self):
        self.assertEqual(ws.season_start("Α1 Κατηγορία υδατοσφαίρισης ανδρών 2009-2010"), 2009)
        self.assertEqual(ws.season_start("Α1 Εθνική υδατοσφαίρισης ανδρών 2013–14"), 2013)
        self.assertEqual(ws.season_start("Α2 Εθνική υδατοσφαίρισης ανδρών 1988−89"), 1988)
        self.assertEqual(ws.season_start("1999–2000 Alpha Ethniki"), 1999)
        self.assertIsNone(ws.season_start("Πανελλήνιο πρωτάθλημα 1959"))

    def test_greek_title(self):
        self.assertEqual(ws.greek_title("Παναθηναϊκός (ποδόσφαιρο)"), "Παναθηναϊκός")
        self.assertEqual(ws.greek_title("Ολυμπιακός Σ.Φ.Π."), "Ολυμπιακός")
        self.assertEqual(ws.greek_title("Α.Ο. Ξάνθη"), "Ξάνθη")
        self.assertEqual(ws.greek_title("Γ.Α.Σ. Βέροια"), "Βέροια")
        self.assertEqual(ws.greek_title("Α.Ε.Κ."), "Α.Ε.Κ.")
        self.assertEqual(ws.greek_title("Ο.Φ.Η."), "Ο.Φ.Η.")

    def test_merged_team_is_paok(self):
        self.assertTrue(ws._paok("Φιλαθλητικός / ΠΑΟΚ"))
        self.assertFalse(ws._paok("Παναθηναϊκός"))



class LinkTest(unittest.TestCase):
    def test_team_link_kept(self):
        head = "<tr><th>Θέση</th><th>Ομάδα</th><th>Β</th><th>Ν</th></tr>"
        body = "".join(f'<tr><td>{i}</td><td><span><a href="/wiki/File:Flag.svg">x</a></span><a href="/wiki/Club_{i}">{t}</a></td>'
                       f"<td>{20 - i}</td><td>1</td></tr>" for i, t in enumerate(TEAMS, 1))
        ws._LINKS.clear()
        kinds, rows = ws.standings_from_html("<table>" + head + body + "</table>")
        self.assertEqual(ws._LINKS[rows[0]["raw"]], "Club 1")
        t = ws.to_table("waterpolo", "x 2009-2010", "u", kinds, rows, logos={rows[0]["raw"]: "https://img/1.png", rows[1]["raw"]: "z"})
        self.assertEqual(t["rows"][0]["logo"], "https://img/1.png")
        self.assertEqual(t["rows"][1]["logo"], "")  # ΠΑΟΚ: το δικό μας σήμα


if __name__ == "__main__":
    unittest.main()
