#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 ehf3.py 2>&1 | head -80
