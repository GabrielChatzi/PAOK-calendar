#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 cev4.py 2>&1 | head -60
