import re, build_calendars as b
from build_calendars import fetch, HANDBALL
form = fetch(HANDBALL + "scorestats.asp", encoding="cp1253")
blocks = form.split("var ap = root.findchild(")[1:]
for block in blocks[:4]:
    print(re.findall(r'new cri\((\d+),"([^"]*)"\)', block)[:5])
i = form.find("<form"); print(form[i:i+3000])
nodes = re.findall(r'new cri\((\d+),"([^"]*)"\)', blocks[0])
ids = [n[0] for n in nodes[:4]]
data = [("obj", x) for x in ids] + [("agper", "x"), ("category", "x"), ("diorg", "x"), ("group", "x"), ("B1", "x")]
page = fetch(HANDBALL + "scorestatsres.asp", data=data, encoding="cp1253")
open("docs/hb_st.html", "w", encoding="utf-8").write(page)
print(len(page), ids)
