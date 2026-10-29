#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
echo "== ESPN"; for lg in all uefa.weuropa uefa.wchampions; do curl -sS -m 30 "https://site.api.espn.com/apis/site/v2/sports/soccer/$lg/summary?event=401916430" | python3 -c "
import json,sys
try:
  d=json.load(sys.stdin); h=d['header']; c=h['competitions'][0]
  print('$lg', h.get('league',{}).get('slug'), h.get('league',{}).get('name'), [(t['team']['id'], t['team']['displayName']) for t in c['competitors']])
except Exception as e: print('$lg ERR', e)"; done
echo "== EHF"; curl -sSL -m 40 -A "$UA" "https://www.eurohandball.com/en/search/?q=PAOK" -o docs/ehf.html; wc -c docs/ehf.html
grep -oE '(https?:)?//[^"'"'"' )]*(api|Api)[^"'"'"' )]*' docs/ehf.html | sort -u | head -20
curl -sSL -m 40 -A "$UA" "https://ehfel.eurohandball.com/women/2026-27/" -o docs/ehfel.html; wc -c docs/ehfel.html
grep -oE '(https?:)?//[^"'"'"' )]*(api|Api|json)[^"'"'"' )]*' docs/ehfel.html | sort -u | head -30
grep -oE '"[^"]*/umbraco/[^"]*"' docs/ehfel.html | sort -u | head -20
echo "== CEV"; curl -sSL -m 40 -A "$UA" "https://www.cev.eu/club/cev-volleyball-cup/2027/men/" -o docs/cev.html -w "%{http_code} %{url_effective}\n"; wc -c docs/cev.html
grep -oE '(https?:)?//[^"'"'"' )]*(api|Api|json|dataproject)[^"'"'"' )]*' docs/cev.html | sort -u | head -30
grep -oiE 'href="[^"]*(cup|match|schedule)[^"]*"' docs/cev.html | sort -u | head -30
