#!/usr/bin/env bash
# Όλοι οι έλεγχοι τοπικά, πριν από push (ίδιοι με το .github/workflows/tests.yml).
set -e
cd "$(dirname "$0")/.."
python3 -m unittest discover tests
node --test tests/*.test.mjs
python3 - <<'PY'
import re
s = open("docs/index.html", encoding="utf-8").read()
open("/tmp/page.js", "w", encoding="utf-8").write(max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len))
PY
node --check /tmp/page.js
for f in api/*.js docs/sw.js; do node --check "$f"; done
if [ -f docs/matches.json ] && node -e "import('playwright')" 2>/dev/null; then node tests/page-smoke.mjs; fi
echo "Όλα εντάξει."
