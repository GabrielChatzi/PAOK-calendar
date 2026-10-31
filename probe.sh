#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
S=https://paokalendar.vercel.app
curl -sS "$S/api/live?src=ehf&id=202712020702020"; echo
curl -sS "$S/api/live?src=eok&day=2026-11-07&side=h&comp=WOMEN"; echo
curl -sS "$S/api/health?selftest=1"; echo
curl -sS -o /dev/null -w "page %{http_code}\n" "$S/"
