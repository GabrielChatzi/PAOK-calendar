#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
npm i --silent playwright@1.48.2 >/dev/null 2>&1 && npx playwright install --with-deps chromium >/dev/null 2>&1
node net.js "https://www.cev.eu/club/cev-volleyball-cup/2027/men/" "https://ehfel.eurohandball.com/women/2026-27/" "https://ehfec.eurohandball.com/men/2026-27/" 2>&1 | head -150
