import datetime as dt, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import build_calendars as bc


class M:
    def __init__(self, uid, day):
        self.uid, self.day, self.home, self.away = uid, day, "ΠΑΟΚ", "X"


def test_friendly_on_official_day_is_dropped():
    d = dt.date(2026, 11, 7)
    ms = [M("a", d), M("b-friendly-1", d), M("c-friendly-2", dt.date(2026, 11, 14))]
    assert [m.uid for m in bc.drop_shadow_friendlies(ms)] == ["a", "c-friendly-2"]
