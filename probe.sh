#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
for r in 20260620-20260720 20260720-20260820; do
curl -sS -A "Mozilla/5.0" "https://site.api.espn.com/apis/site/v2/sports/soccer/club.friendly/scoreboard?dates=$r&limit=1000" | python3 -c "
import json,sys; d=json.load(sys.stdin); ev=d.get('events',[]); print('club.friendly $r', len(ev))
for e in ev:
  if 'PAOK' in e['name']: print(e['id'], e['date'][:16], e['name'], e['competitions'][0]['status']['type']['name'])"
done
python3 - <<'PY'
import json, urllib.request, html
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"}), timeout=30).read())
cats = {c["id"]: c["name"] for c in get("https://acpaok.gr/wp-json/wp/v2/categories?per_page=100&_fields=id,name")}
for q in ["%CF%86%CE%B9%CE%BB%CE%B9%CE%BA%CF%8C", "%CF%86%CE%B9%CE%BB%CE%B9%CE%BA%CE%AE", "%CF%86%CE%B9%CE%BB%CE%B9%CE%BA%CE%AD%CF%82"]:
    for p in get(f"https://acpaok.gr/wp-json/wp/v2/posts?search={q}&per_page=30&_fields=date,title,categories"):
        print(p["date"][:10], html.unescape(p["title"]["rendered"])[:90], "|", ",".join(cats.get(c,"?") for c in p["categories"]))
PY
