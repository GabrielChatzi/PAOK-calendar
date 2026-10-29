#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 ehf.py 2>&1 | head -80
