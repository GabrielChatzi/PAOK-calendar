import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_calendars as b  # noqa: E402
import tvguide  # noqa: E402

AGONES = """
<a class="nav-link active" id="day_0-tab" href="#day_0" role="tab"><span class="date__day">Τετάρτη</span>
<date class="date__date">18/11/2026</date></a>
<a class="nav-link" id="day_1-tab" href="#day_1" role="tab"><span class="date__day">Πέμπτη</span>
<date class="date__date">19/11/2026</date></a>
<div class="tab-pane active" id="day_0"><table>
<tr><td class="cell-wrap align-top"><i class="icon icon-tv fal fa-basketball-ball clr-orange"></i>
<span class="ii__localtime">21:30</span></td><td class="text-left"><div class="teams mb-2"><a href="/basket/x">
<div class="team_row"><img alt="Μανρέσα"><span>Μανρέσα</span></div><div class="team_row"><img alt="Μανρέσα">
<span>ΠΑΟΚ</span></div></a></div></td><td class="text-left align-top"><img><span>Ευρώπη Γιούροκαπ</span></td>
<td class="align-top">Novasports 4HD</td></tr>
</table></div>
<div class="tab-pane" id="day_1"><table>
<tr><td class="cell-wrap align-top"><i class="icon icon-tv clr-grey fas fa-futbol"></i>
<span class="ii__localtime">19:30</span></td><td class="text-left"><div class="teams mb-2"><a href="/x">
<div class="team_row"><img><span>ΠΑΟΚ</span></div><div class="team_row"><img><span>Κηφισιά</span></div></a></div></td>
<td class="text-left align-top"><span>ΕΛΛΑΔΑ: Σούπερ Λιγκ 1</span></td><td class="align-top">Novasports1 League</td></tr>
</table></div>
"""

MATCHMONEY = """<table><thead><tr><td>Ώρα</td><td>Αγώνας / Διοργάνωση</td><td>Κανάλι</td></tr></thead><tbody>
<tr><td><span>20:00</span></td><td><span>🏐 ΠΑΟΚ – Πανιώνιος ΓΣΣ (Volley League Γυναικών)</span></td><td><span>ΕΡΤ2 ΣΠΟΡ</span></td></tr>
<tr><td><span>21:00</span></td><td><span>🏐 ΠΑΟΚ – Φοίνικας Σύρου (Volley League)</span></td><td><span>ΕΡΤ3</span></td></tr>
</tbody></table>"""

DAY = dt.date(2026, 11, 18)
NOW = dt.datetime(2026, 11, 18, 12, 0, tzinfo=b.ATHENS)


def match(section, home, away, day=DAY, time=dt.time(21, 30), **kw):
    return b.Match(section=section, uid=f"{section}-{home}-{away}", day=day, time=time, home=home, away=away,
                   paok_home=b.is_paok(home), **kw)


class TvGuide(unittest.TestCase):
    def setUp(self):
        tvguide._ENTRIES["all"] = tvguide.parse_agones(AGONES) + tvguide.parse_matchmoney(MATCHMONEY, DAY)

    def tearDown(self):
        tvguide._ENTRIES.clear()

    def test_parse(self):
        a = tvguide.parse_agones(AGONES)
        self.assertEqual([(e["day"], e["time"], e["home"], e["away"], e["channel"], e["sport"]) for e in a], [
            (DAY, "21:30", "Μανρέσα", "ΠΑΟΚ", "Novasports 4HD", "basketball"),
            (dt.date(2026, 11, 19), "19:30", "ΠΑΟΚ", "Κηφισιά", "Novasports1 League", "football")])
        mm = tvguide.parse_matchmoney(MATCHMONEY, DAY)
        self.assertEqual((mm[0]["home"], mm[0]["away"], mm[0]["competition"], mm[0]["sport"]),
                         ("ΠΑΟΚ", "Πανιώνιος ΓΣΣ", "Volley League Γυναικών", "volley"))

    def test_latin_name_matches_greek(self):
        m = match("basketball", "Manresa", "ΠΑΟΚ")
        tvguide.tv("basketball", [m], NOW)
        self.assertEqual(m.tv, "Novasports 4HD")

    def test_existing_channel_kept_and_other_sport_ignored(self):
        m = match("basketball", "Manresa", "ΠΑΟΚ", tv="ΕΡΤ")
        w = match("basketball-women", "Manresa", "ΠΑΟΚ")
        f = match("football", "Manresa", "ΠΑΟΚ")
        for x in (m, w, f):
            tvguide.tv(x.section, [x], NOW)
        self.assertEqual((m.tv, w.tv, f.tv), ("ΕΡΤ", "", ""))

    def test_women_and_men_separate(self):
        w = match("volley-women", "ΠΑΟΚ", "ΠΑΝΙΩΝΙΟΣ Γ.Σ.Σ.", time=dt.time(20, 0))
        men = match("volley", "ΠΑΟΚ", "Φοίνικας Σύρου", time=dt.time(21, 0))
        tvguide.tv("volley-women", [w], NOW)
        tvguide.tv("volley", [men], NOW)
        self.assertEqual((w.tv, men.tv), ("ΕΡΤ2 ΣΠΟΡ", "ΕΡΤ3"))

    def test_unknown_name_needs_same_time_and_side(self):
        a = match("basketball", "Bàsquet X", "ΠΑΟΚ")
        c = match("basketball", "Bàsquet X", "ΠΑΟΚ", time=dt.time(20, 30))
        tvguide.tv("basketball", [a, c], NOW)
        self.assertEqual((a.tv, c.tv), ("Novasports 4HD", ""))

    def test_wrong_day_and_academy(self):
        m = match("football", "ΠΑΟΚ", "Κηφισιά", time=dt.time(19, 30))
        tvguide.tv("football", [m], NOW)
        self.assertEqual(m.tv, "")
        u = match("football-u19", "ΠΑΟΚ", "Κηφισιά", day=dt.date(2026, 11, 19), time=dt.time(19, 30))
        tvguide.tv("football-u19", [u], NOW, academy=True)
        self.assertEqual(u.tv, "")
        m = match("football", "ΠΑΟΚ", "Κηφισιά", day=dt.date(2026, 11, 19), time=dt.time(19, 30))
        tvguide.tv("football", [m], NOW)
        self.assertEqual(m.tv, "Novasports1 League")


if __name__ == "__main__":
    unittest.main()
