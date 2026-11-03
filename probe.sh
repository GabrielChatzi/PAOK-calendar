#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import json, urllib.request, html, re
def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"}), timeout=30).read())
posts = get("https://acpaok.gr/wp-json/wp/v2/posts?search=%CF%83%CF%84%CE%B7%CE%BD%20TV&per_page=10&_fields=date,title,content")
for p in posts[:6]:
    t = html.unescape(p["title"]["rendered"])
    c = p["content"]["rendered"]
    c = re.sub(r'<iframe[^>]*title="([^"]*)"[^>]*src="([^"]*)"[^>]*>', r' [VIDEO: \1 | \2] ', c)
    c = re.sub(r'<a [^>]*href="([^"]*)"[^>]*>', r' [LINK \1] ', c)
    c = html.unescape(re.sub(r"<[^>]+>", " ", c)); c = re.sub(r"\s+", " ", c)
    print("=====", p["date"], t); print(c[:1400])
PY
