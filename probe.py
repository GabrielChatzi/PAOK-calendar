import urllib.request, re
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
for u in ("paok.ics", "cal.ics?t=football,basketball-women&v=home", "cal.ics?t=futsal", "cal.ics?t=all&v=away", "cal.ics?t=nope", "football-home.ics"):
    try:
        r = urllib.request.urlopen(urllib.request.Request("https://paokalendar.gr/" + u, headers={"User-Agent": UA}), timeout=30)
        b = r.read().decode(); s = b.replace("\r\n ", "")
        name = re.search(r"^X-WR-CALNAME:(.*)$", s, re.M)
        days = [l for l in s.splitlines() if l.startswith("SUMMARY")]
        nov22 = [re.search(r"SUMMARY:(.*)", e).group(1) for e in s.split("BEGIN:VEVENT") if "DTSTART;TZID=Europe/Athens:20261122" in e]
        print(u, r.status, r.headers.get("content-type"), r.headers.get("cache-control"), "|", name and name.group(1).strip(), "|", len(days), "αγώνες |", "VTIMEZONE x", b.count("BEGIN:VTIMEZONE"), "| crlf", b.count("\r\n") == b.count("\n"), "| 22/11:", nov22)
    except Exception as e:
        print(u, "ERR", e)
