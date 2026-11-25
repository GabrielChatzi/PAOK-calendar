import wiki_standings as ws
page, real = ws.article_html("en", "1997–98 Alpha Ethniki")
ws._LINKS.clear(); k, rows = ws.standings_from_html(page)
logos, names = ws.clubs("en", [r["raw"] for r in rows])
print("NAMES", len(rows), len(logos), len(names), names)
