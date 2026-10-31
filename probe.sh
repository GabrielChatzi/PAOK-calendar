#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
B=https://live.koe.org.gr/waterpolo
curl -sS -m 20 -A "$UA" "$B/assets/api_config.json"; echo
echo "== ls export"; curl -sS -m 20 -A "$UA" -D - "$B/assets/export/WP/" -o /tmp/x | head -3; head -c 500 /tmp/x; echo
