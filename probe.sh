#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
echo "=== eope live"
curl -sS -m 30 -A "$UA" "https://eope-web.dataproject.com/MainLiveScore.aspx" -o /tmp/l.html; wc -c < /tmp/l.html
grep -oiE '(src)="[^"]+"' /tmp/l.html | head -20
grep -oiE '.{0,100}(signalr|hub|livescore|azurewebsites).{0,150}' /tmp/l.html | head -20
python3 - <<'PY'
import re
s=open('/tmp/l.html',encoding='utf-8',errors='replace').read()
t=re.sub(r"<script.*?</script>|<style.*?</style>","",s,flags=re.S); t=re.sub(r"<[^>]+>"," ",t); t=re.sub(r"\s+"," ",t)
print(t[:1500])
PY
echo "=== esake home genius"
for u in https://www.esake.gr/ https://www.esake.gr/el/action/EsakeResults; do curl -sS -m 30 -A "$UA" "$u" | grep -oiE '.{0,80}(genius|livestats|fibalive|synergy|live\.).{0,120}' | head -8; done
