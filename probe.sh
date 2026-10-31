#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
curl -sS -m 40 "https://paokalendar.vercel.app/api/live?src=dp&fed=hvl&day=2026-10-31&side=h"; echo
