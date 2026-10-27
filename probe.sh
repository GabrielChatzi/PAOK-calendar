#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
R=GabrielChatzi/PAOK-calendar
echo "== reminders run"; gh run view 40531266407 -R $R --log | grep -vE "^\S+\s+\S+\s+[0-9T:.Z-]+ *$" | grep -E "push|Υπενθυμ|ειδοποίηση|!|Σε |live|Error|error" | cut -c1-400 | head -40
echo "== live run"; gh run view 40531309855 -R $R --log | grep -E "push|ειδοποίηση|!|Error|error|Αγώνες|in |pre " | cut -c1-400 | head -60
