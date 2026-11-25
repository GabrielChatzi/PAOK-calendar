import json, wiki_standings as ws
d = ws._get("en", {"action": "query", "prop": "pageimages|langlinks", "piprop": "thumbnail", "pithumbsize": 96, "pilicense": "any",
                   "redirects": 1, "lllang": "el", "lllimit": "max", "titles": "Olympiacos F.C.|AEK Athens F.C.|Iraklis F.C. (Thessaloniki)"})
print(json.dumps(d, ensure_ascii=False)[:3000])
page, real = ws.article_html("en", "1997–98 Alpha Ethniki")
ws._LINKS.clear(); k, rows = ws.standings_from_html(page)
print([(r["raw"], ws._LINKS.get(r["raw"])) for r in rows[:5]])
print(ws.clubs("en", [r["raw"] for r in rows[:5]]))
