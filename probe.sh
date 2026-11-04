#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
for u in handball-premier a1-gynaikon; do
curl -sSL -m 30 -A "$UA" "https://www.handball.org.gr/competitions/protathlimata/$u" -o /tmp/p.html
echo "##### $u"
python3 - <<'PY'
import re, html
p=open('/tmp/p.html',encoding='utf-8',errors='replace').read()
for m in re.finditer(r'<img[^>]+src="([^"]+)"[^>]*>', p):
    src=m.group(1)
    if re.search(r'favicon|HANDBALL-PREMIER|oxe-|Handball-white|IHF|european|Mediter|eoe-|gga-|yfipoy|e-genius|logo(-mobile)?\.png', src): continue
    before=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',p[max(0,m.start()-400):m.start()])))[-80:]
    after=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',p[m.end():m.end()+500])))[:100]
    href=re.findall(r'href="([^"]+)"', p[max(0,m.start()-300):m.start()])[-1:] 
    print(src.split('/')[-1], '| before:', before.strip()[-50:], '| after:', after.strip()[:70], '|', href)
PY
done
