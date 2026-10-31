#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
echo "=== signalr js"
curl -sS -m 30 -A "$UA" "https://eope-web.dataproject.com/Scripts/LiveScoreListSignalR.js" -o /tmp/s.js; wc -c < /tmp/s.js
grep -oE '(hub|server|client)\.[A-Za-z_]+|connection\.[A-Za-z_]+|\$\.connection\.[A-Za-z_]+|hubName[^,;]*|url *= *[^;]+' /tmp/s.js | sort | uniq -c | sort -rn | head -40
head -c 2500 /tmp/s.js; echo
echo "=== hubs"
curl -sS -m 30 -A "$UA" "https://dataprojectservicesignalr.azurewebsites.net/signalr/hubs" | grep -oE "proxies\['[a-zA-Z]+'\]|proxies\['[a-zA-Z]+'\]\.server\.[a-zA-Z]+|[a-zA-Z]+: function \([^)]*\)" | head -40
echo "=== genius widget"
curl -sS -m 30 -A "$UA" "https://widget.wh.geniussports.com/widget//?RFJIN037I07QV520B7WEXKV1GYNA31" -o /tmp/w.js; wc -c < /tmp/w.js; grep -oE 'https?://[A-Za-z0-9./_-]+' /tmp/w.js | sort -u | head -30
