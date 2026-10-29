#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
echo "== EHF js"
for js in $(curl -sSL -m 40 -A "$UA" "https://ehfel.eurohandball.com/women/2026-27/" | grep -oE 'src="/frontend\.kw/[^"]+\.js[^"]*"' | sed 's/src="//;s/"//' | sort -u); do
  curl -sSL -m 40 -A "$UA" "https://ehfel.eurohandball.com$js" -o /tmp/e.js; echo "-- $js $(wc -c </tmp/e.js)"
  grep -oE '"?/umbraco/api/[A-Za-z]+/[A-Za-z]+[^"]{0,80}' /tmp/e.js | sort -u | head -40
done
echo "== CEV dataproject"; curl -sS -m 30 -o /dev/null -w "%{http_code} %{url_effective}\n" -L "https://cev-web.dataproject.com/MainHome.aspx"
echo "== CEV entry js"; curl -sSL -m 40 -A "$UA" "https://www.cev.eu/assets/scripts/entry.9f8slv.js" -o /tmp/c.js; wc -c </tmp/c.js
grep -oE '"[^"]{0,40}(/api/|\.json|dataproject|ashx|svc)[^"]{0,80}"' /tmp/c.js | sort -u | head -30
curl -sSL -m 40 -A "$UA" "https://www.cev.eu/_framework/blazor.boot.json" | head -c 600; echo
curl -sSL -m 40 -A "$UA" "https://www.cev.eu/club/cev-volleyball-cup/2027/men/" | grep -oE '(data-[a-z-]+="[^"]{0,120}"|<[a-z-]+ [^>]*component[^>]*>)' | sort -u | head -30
