#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import json, urllib.request
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
def get(url, hdr=None, show=False):
    h={"User-Agent":UA,"Origin":"https://paokalendar.vercel.app"}; h.update(hdr or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=40) as r:
            body=r.read().decode("utf-8","replace")
            if show: print("  CORS:", r.headers.get("access-control-allow-origin"), "| headers allowed:", r.headers.get_all("access-control-allow-headers"))
            return json.loads(body) if body.strip() else None
    except Exception as e:
        print("  ERR", url, e); return None
K="https://live.koe.org.gr/api-waterpolo/wp"
print("== KOE token"); t=get(K+"/token", show=True); print(" ", str(t)[:200])
tok=(t or {}).get("token")
H={"x-wp-token":tok} if tok else {}
for code in ["KOE","KOEW"]:
    print("== schedule", code)
    d=get(f"{K}/{code}/get/schedule/*/*/*/*/*", H, show=True)
    if not d: continue
    sch=d.get("Schedule") or d
    print("  keys", list(d.keys())[:5], "n", len(sch) if isinstance(sch,list) else "?")
    if isinstance(sch,list):
        for x in sch:
            s=json.dumps(x,ensure_ascii=False)
            if "PAOK" in s.upper() or "ΠΑΟΚ" in s:
                if x.get("OraMatchDate","").endswith("/2026") and x.get("OraMatchDate","")[3:5] in ("10","11"):
                    print(" ", s[:700])
    print("== events", code); e=get(f"{K}/{code}/get/events/*", H)
    if e: print(" ", json.dumps(e,ensure_ascii=False)[:1500])
print("== KOE result ASM/65/A01/1/9175200/9175106")
for code in ["KOE","KOEW"]:
    r=get(f"{K}/{code}/get/resultsDBlikeJSON/ASM/65/A01/1/9175200/9175106", H)
    if r: print(code, json.dumps(r,ensure_ascii=False)[:2500])
print("== EA result for ZVL-PAOK")
E="https://ea.microplustimingservices.com/api/wp"
tok2=get(E+"/site/token")["data"]["token"]
r=get(f"{E}/EACLUB27/get/resultsDBlikeJSON/ASF/2/001/3/ZVL/PAOK", {"Authorization":"Bearer "+tok2})
print(json.dumps(r,ensure_ascii=False)[:3000] if r else r)
PY
