#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import json, urllib.request, html, re
def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"}), timeout=30).read())
posts = get("https://acpaok.gr/wp-json/wp/v2/posts?search=TV&per_page=15&_fields=date,title,content")
for p in posts:
    t = html.unescape(p["title"]["rendered"])
    if "TV" not in t: continue
    print("=====", p["date"], t)
    c = p["content"]["rendered"]
    print(re.sub(r"\s+", " ", c)[:1500])
PY
echo; echo "== ESPN broadcasts football"
curl -sS "https://site.api.espn.com/apis/site/v2/sports/soccer/gre.1/scoreboard?dates=20261108" -A "Mozilla/5.0" | python3 -c "
import json,sys; d=json.load(sys.stdin)
for e in d.get('events',[]): 
  c=e['competitions'][0]; print(e['name'], c.get('broadcasts'), c.get('geoBroadcasts', [])[:3])"
