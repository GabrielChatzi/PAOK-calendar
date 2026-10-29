#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
gh run view 40935545238 -R GabrielChatzi/PAOK-calendar --log | grep -E "! |Έλεγχοι|- \*\*|handball-women|Αλλαγή|Καμία" | cut -f3- | cut -c1-250 | head -20
