#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
for s in 1.1.1.1 8.8.8.8 dns1.papaki.gr; do echo "== A @$s: $(dig +short A paokalendar.gr @$s | tr '\n' ' ')"; done
echo "== NS (gr registry): $(dig +short NS paokalendar.gr @grdns-a.ics.forth.gr | tr '\n' ' ')"
echo "== MX: $(dig +short MX paokalendar.gr @1.1.1.1 | tr '\n' ' ')"
whois paokalendar.gr 2>/dev/null | head -15
