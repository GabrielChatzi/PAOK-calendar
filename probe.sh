#!/usr/bin/env bash
mkdir -p docs
for u in "" matches.json standings.json football-home.ics volley-women-away.ics sw.js manifest.webmanifest icons/icon-192.png; do
  echo "== /$u"
  curl -sS -o "docs/body" -D - "https://paokalendar.vercel.app/$u" | grep -i -E "^HTTP|^content-type|^cache-control|^location"
  case "$u" in *.ics) head -c 300 docs/body; echo; grep -c BEGIN:VEVENT docs/body;; *.json) head -c 120 docs/body; echo;; "") grep -o '<link rel="manifest"[^>]*>' docs/body;; esac
done
