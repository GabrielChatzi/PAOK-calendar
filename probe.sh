#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import urllib.request, json
UA={"User-Agent":"Mozilla/5.0"}
EA="https://ea.microplustimingservices.com/api/wp"
t=json.loads(urllib.request.urlopen(urllib.request.Request(EA+"/site/token",headers=UA)).read())["data"]["token"]
h={**UA,"Authorization":"Bearer "+t}
for path in ["groupstandings/ASF/2","groupstandings/ASF/2/001","groupstandings/ASF/2/001/3","groupstandings/ASF/2/*/*","groupstandings/ASF","brackets/ASF/2","rounds/ASF/2"]:
    try:
        d=urllib.request.urlopen(urllib.request.Request(f"{EA}/EACLUB27/get/{path}",headers=h),timeout=40).read().decode()
        print("==", path, d[:700])
    except Exception as e: print("==",path,e)
PY
