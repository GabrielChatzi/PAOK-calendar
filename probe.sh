#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
echo "== ntfy live topic"; curl -sS -m 30 "https://ntfy.sh/paokcal-x7q3-basketball-live/json?poll=1&since=3h" | cut -c1-300
echo "== ntfy match live"; curl -sS -m 30 "https://ntfy.sh/paokcal-x7q3-m-32aab779be-live/json?poll=1&since=3h" | cut -c1-300
echo "== header"; python3 - <<'PY'
import json,urllib.request
d=json.load(open("docs/../matches.json")) if False else None
PY
curl -sS -m 30 "https://paokalendar.vercel.app/matches.json" | python3 -c "
import json,sys; d=json.load(sys.stdin)
for m in d['matches']:
  if m['nt']=='32aab779be': print(m)"
