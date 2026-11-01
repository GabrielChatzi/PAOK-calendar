#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import club, build_calendars as b, html, re
cats = club.get_json("categories?per_page=100&_fields=id,name")
sec = {c["id"]: (c["name"], club.section_of(c["name"])) for c in cats}
for p in club.recent_posts()[:10]:
    t = html.unescape(p["title"]["rendered"]); x = b.clean(p["content"]["rendered"])
    print(p["date"], t[:50], [sec.get(c) for c in p["categories"]])
    for m in re.finditer(r"\d{1,3}\D{1,3}\d{1,3}", t + " | " + x[:300]):
        print("   ", repr(m.group(0)), [hex(ord(c)) for c in m.group(0) if not c.isdigit()])
PY
