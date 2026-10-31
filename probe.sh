#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
curl -sS -m 30 -A "$UA" "https://dataprojectservicesignalr.azurewebsites.net/signalr/hubs" -o /tmp/h.js
python3 - <<'PY'
import re
s=open('/tmp/h.js').read()
for hub in re.findall(r"proxies\['(\w+)'\] = this.createHubProxy\('(\w+)'\)", s): print("HUB", hub)
i=s.find("proxies['signalRLiveHubFederations'].server")
print(re.findall(r"(\w+): function \(([^)]*)\)", s[i:i+20000])[:40])
PY
echo "=== how list is requested"
curl -sS -m 30 -A "$UA" "https://eope-web.dataproject.com/Scripts/LiveScoreListSignalR.js" | grep -nE "livescoreSRHub\.(server|client)\.\w+" | head -20
for h in hvf-web eope-web; do echo "=== $h live page"; curl -sS -m 30 -A "$UA" "https://$h.dataproject.com/MainLiveScore.aspx" | python3 -c "
import re,sys
s=sys.stdin.read(); t=re.sub(r'<script.*?</script>|<style.*?</style>','',s,flags=re.S); t=re.sub(r'<[^>]+>',' ',t); t=re.sub(r'\s+',' ',t)
i=t.find('LIVE SCORE Streaming'); print(t[i:i+700]); print(sorted(set(re.findall(r'ID=(\d+)&amp;cmpID', s))))"; done
