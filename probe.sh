#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import datetime as dt, club, build_calendars as b
day=dt.date(2026,11,1); d2=dt.date(2026,10,31)
M=lambda s,h,a,ph,d=day,t=(14,0): b.Match(section=s,uid=s+h,day=d,time=dt.time(*t),home=h,away=a,paok_home=ph)
ms=[M("football-women","ΠΑΣ ΠΥΡΓΟΣ","ΠΑΟΚ",False), M("futsal","ΠΑΟΚ","ΚΟΡΥΔΑΛΛΟΥ ΑΟΔ",True),
    M("basketball-women","ΑΕΟ ΠΡΩΤΕΑΣ ΒΟΥΛΑΣ","ΠΑΟΚ",False,t=(16,0)), M("volley-women","ΠΑΟΚ","Z.A.O.N.",True,t=(19,0)),
    M("handball-women","ΠΑΟΚ","ΑΘΗΝΑΪΚΟΣ",True,d=d2,t=(17,30)), M("volley","ΠΑΟΚ","Α.Ο.Π.Κηφισιάς",True,d=d2,t=(18,0)),
    M("waterpolo","ΠΑΟΚ","ΕΘΝΙΚΟΣ ΟΦΠΦ",True,d=d2,t=(16,0))]
now=dt.datetime(2026,10,30,12,0,tzinfo=b.ATHENS)
for m in ms:
    club.tv(m.section,[m],now=now); print(m.section, "|", m.tv, "|", m.tv_url)
PY
