#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
curl -sSL -A "$UA" -w "\n[%{http_code}]\n" "https://acpaok.gr/feed/" -o /tmp/f.xml; head -c 300 /tmp/f.xml; echo
python3 - <<'PY'
import re, html
x=open('/tmp/f.xml',encoding='utf-8',errors='replace').read()
for it in re.findall(r'<item>(.*?)</item>', x, re.S)[:25]:
    t=html.unescape(re.search(r'<title>(.*?)</title>',it,re.S).group(1))
    d=re.search(r'<pubDate>(.*?)</pubDate>',it).group(1)
    cats=[html.unescape(c) for c in re.findall(r'<category><!\[CDATA\[(.*?)\]\]></category>',it)]
    print(d, '|', t, '|', ','.join(cats))
PY
curl -sSL -A "$UA" -o /dev/null -w "wp-json %{http_code}\n" "https://acpaok.gr/wp-json/wp/v2/posts?per_page=1"
