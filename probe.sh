#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
gh run view 40935107506 -R GabrielChatzi/PAOK-calendar --log | grep -E "! |Αποτυχίες|Έλεγχοι|^.*- \*\*|issue|github.com/.*/issues" | cut -f3- | cut -c1-220 | head -20
