#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
gh run view 40932773378 -R GabrielChatzi/PAOK-calendar --log | grep -E "! |push |Νέος" | cut -f3- | cut -c1-250 | head -20
