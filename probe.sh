#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sSL -m 60 -A "$UA" "https://acpaok.gr/" -o docs/ac.html; wc -c docs/ac.html
grep -oiE 'href="[^"]*(program|agon|calendar|fixtures|match|schedule|πρόγρ)[^"]*"' docs/ac.html | sort -u | head -30
python3 - <<'PY'
import re, html
t = open("docs/ac.html", encoding="utf-8", errors="replace").read()
x = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " | ", re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S))))
x = re.sub(r"(\|\s*)+", "| ", x)
for k in ("Πανα", "Πόλαρ", "League Cup", "Νοεμβρίου"):
    i = x.find(k); print(k, "::", x[max(0, i-600):i+600] if i >= 0 else "-")
print(re.findall(r'(https?://[^"\']+(?:wp-json|admin-ajax)[^"\']*)', t)[:10])
PY
