#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
for i in 1 2 3; do
python3 - <<'PY'
import json, urllib.request, time
d=json.loads(urllib.request.urlopen(urllib.request.Request(f"https://fibalivestats.dcd.shared.geniussports.com/data/2902720/data.json?t={time.time()}",headers={"User-Agent":"Mozilla/5.0"}),timeout=30).read())
print(time.strftime("%H:%M:%S"), d["period"], d["clock"], d["tm"]["1"]["score"], d["tm"]["2"]["score"], len(d["pbp"]), json.dumps(d["pbp"][0], ensure_ascii=False)[:300])
PY
sleep 45; done
curl -sSI "https://fibalivestats.dcd.shared.geniussports.com/data/2902720/data.json" | grep -iE "access-control|cache|age|last-mod"
