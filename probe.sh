#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
U="https://europeanaquatics.org/sports/water-polo/club-competitions/schedule/"
curl -sSL -m 40 -A "Mozilla/5.0" "$U" -o docs/sched.html; wc -c docs/sched.html
grep -oE '(https?:)?//[^"'"'"' )]+' docs/sched.html | grep -iE "api|microplus|json|wp-json|schedule|calendar|\.js" | sort -u | head -60
grep -oE '<iframe[^>]+' docs/sched.html | head
