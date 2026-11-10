import json, re, os, urllib.request
OUT = "docs/probe"; os.makedirs(OUT, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def get(url, headers=None):
    h = {"User-Agent": UA}; h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r: return r.status, r.read().decode("utf-8-sig", "replace")
    except Exception as e: return 0, str(e)
for name in ("Header", "PlayByPlay"):
    st, b = get(f"https://live.euroleague.net/api/{name}?gamecode=14&seasoncode=U2026"); print(name, st, len(b))
    open(f"{OUT}/el-{name}.json", "w").write(b)
st, js = get("https://widget.wh.geniussports.com/widget//?RFJIN037I07QV520B7WEXKV1GYNA31", {"Referer": "https://www.esake.gr/"})
raw = re.search(r'var html = "(.*?)";\n', js, re.S); html = json.loads(f'"{raw.group(1)}"') if raw else ""
ids = re.findall(r"webcast/\w+/(\d+)", html); print("gs ids", ids[:10])
for i in ids[:12]:
    st, b = get(f"https://fibalivestats.dcd.shared.geniussports.com/data/{i}/data.json")
    if st == 200 and re.search(r"P\.?A\.?O\.?K", b):
        open(f"{OUT}/gs-{i}.json", "w").write(b); print("gs paok", i, len(b)); break
