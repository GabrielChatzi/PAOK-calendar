import json, os, re, sys, traceback
import wiki_standings as ws
OUT = "probe_out"; os.makedirs(OUT, exist_ok=True)
keys = [k for k in ws.SPECS if k != "football"]
report = {}
for key in keys:
    try:
        arts = ws.season_articles(key)
    except Exception as e:
        report[key] = {"error": repr(e)}; continue
    res = {}
    for y in sorted(arts):
        try:
            t = ws.season_table(key, y, arts)
        except Exception as e:
            res[y] = {"error": repr(e)[:200], "articles": arts[y]}; continue
        if t:
            paok = next(r for r in t["rows"] if r["paok"])
            res[y] = {"ok": True, "title": t["title"], "cols": t["columns"], "n": len(t["rows"]), "paok": [paok["pos"]] + paok["cells"], "table": t}
        else:
            # Για διόρθωση: οι κεφαλίδες των πινάκων με ΠΑΟΚ
            heads = []; paok_in = []
            for lang, title in arts[y]:
                page, real = ws.article_html(lang, title)
                paok_in.append([real, len(page), page.count("ΠΑΟΚ") + page.count("Π.Α.Ο.Κ") + page.count("PAOK"), len(ws._tables(page))])
                for tb in ws._tables(page):
                    rows = ws._rows(tb)
                    if any(ws.is_paok(c[0]) or "ΠΑΟΚ" in c[0] for r in rows for c in r):
                        heads.append([real, [c[0][:20] for c in rows[0]][:14], [c[0][:20] for c in rows[1]][:14] if len(rows) > 1 else []])
            res[y] = {"ok": False, "articles": arts[y], "heads": heads[:4], "paok_in_page": paok_in}
        print(key, y, "OK" if res[y].get("ok") else "—", flush=True)
    report[key] = res
    json.dump(report, open(f"{OUT}/standings.json", "w"), ensure_ascii=False, indent=0)
