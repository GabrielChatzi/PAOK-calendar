#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
curl -sS -m 60 -A "$UA" "https://acpaok.gr/wp-json/wp/v2/posts?per_page=40&_fields=id,date,modified,title,link,categories,content" -o docs/recent.json
curl -sS -m 60 -A "$UA" "https://acpaok.gr/wp-json/wp/v2/posts?search=%CE%B1%CE%BA%CE%BF%CE%BB%CE%BF%CF%85%CE%B8%CE%AC%CE%BC%CE%B5&per_page=3&_fields=id,date,modified,title,link" -o docs/progs.json
