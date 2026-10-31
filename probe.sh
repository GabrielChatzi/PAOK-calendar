#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
curl -sS -m 30 -A "$UA" "https://www.esake.gr/el/action/EsakegameView?idgame=29CD5AD8&mode=3" -o /tmp/g.html; wc -c < /tmp/g.html
grep -oiE '(https?:)?//[^"'"'"' ]*(genius|fibalivestats|livestats|live)[^"'"'"' ]*' /tmp/g.html | sort -u | head -20
grep -oiE '.{0,80}(live|ζωντανά).{0,120}' /tmp/g.html | head -10
echo "== program page"
curl -sS -m 30 -A "$UA" "https://www.esake.gr/el/action/EsakeResults" -o /tmp/p.html; grep -oiE '.{0,200}29CD5AD8.{0,400}' /tmp/p.html | head -3
