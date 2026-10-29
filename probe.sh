#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
gh run view 40869925427 -R GabrielChatzi/PAOK-calendar --log | grep -E "!|αγώνες|Error|error" | cut -f3- | cut -c1-250 | head -40
