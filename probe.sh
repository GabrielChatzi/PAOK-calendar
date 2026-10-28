#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
npm i --silent playwright@1.48.2 >/dev/null 2>&1 && npx playwright install --with-deps chromium >/dev/null 2>&1 && node shots.js
ls -la docs
