#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import json, urllib.request, html, re
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"}), timeout=30).read())
posts = get("https://acpaok.gr/wp-json/wp/v2/posts?search=%CE%B1%CE%BA%CE%BF%CE%BB%CE%BF%CF%85%CE%B8%CE%AC%CE%BC%CE%B5&per_page=3&_fields=date,title,content")
for p in posts[:2]:
    print("=====", p["date"], html.unescape(p["title"]["rendered"]))
    c = html.unescape(re.sub(r"<[^>]+>", " | ", p["content"]["rendered"])); c = re.sub(r"(\s*\|\s*)+", " | ", c)
    print(c[:2500])
PY
