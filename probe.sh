#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
curl -sSL -A "Mozilla/5.0" "https://eope-web.dataproject.com/CompetitionStandings.aspx?ID=19&PID=20" -o /tmp/st.html
python3 - <<'PY'
import re
p=open('/tmp/st.html',encoding='utf-8',errors='replace').read()
i=p.find('lbl_title')
seg=p[i:i+6000]
print(re.sub(r'\s+',' ',seg)[:5000])
PY
