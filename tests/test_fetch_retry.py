"""Επανάληψη σε προσωρινά σφάλματα πηγών (build_calendars._open_retry)."""
import io
import os
import sys
import unittest
import urllib.error
import urllib.request
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.pop("PUSH", None)

import build_calendars as bc  # noqa: E402


def http_error(code):
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(b""))


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class RetryTest(unittest.TestCase):
    def setUp(self):
        self.req = urllib.request.Request("https://x")
        p = mock.patch("time.sleep")
        self.sleep = p.start()
        self.addCleanup(p.stop)

    def test_502_then_ok(self):
        with mock.patch("urllib.request.urlopen", side_effect=[http_error(502), Resp(b"ok")]) as op:
            self.assertEqual(bc._open_retry(self.req), b"ok")
        self.assertEqual(op.call_count, 2)

    def test_gives_up_after_three(self):
        with mock.patch("urllib.request.urlopen", side_effect=[http_error(503)] * 3) as op:
            with self.assertRaises(urllib.error.HTTPError):
                bc._open_retry(self.req)
        self.assertEqual(op.call_count, 3)

    def test_403_not_retried(self):
        with mock.patch("urllib.request.urlopen", side_effect=[http_error(403)]) as op:
            with self.assertRaises(urllib.error.HTTPError):
                bc._open_retry(self.req)
        self.assertEqual(op.call_count, 1)

    def test_no_retry_flag(self):
        with mock.patch("urllib.request.urlopen", side_effect=[http_error(500)]) as op:
            with self.assertRaises(urllib.error.HTTPError):
                bc._open_retry(self.req, retry=False)
        self.assertEqual(op.call_count, 1)

    def test_timeout_retried(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=[urllib.error.URLError(TimeoutError("t")), Resp(b"ok")]):
            self.assertEqual(bc._open_retry(self.req), b"ok")


class WaterpoloAcademyTest(unittest.TestCase):
    def test_section_without_table(self):
        import standings
        self.assertIn("waterpolo-u18", bc.ACADEMY)
        self.assertIn("waterpolo-u18", bc.SOURCES)
        self.assertNotIn("waterpolo-u18", standings.STANDINGS)


if __name__ == "__main__":
    unittest.main()
