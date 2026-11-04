#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
for u in "https://www.handball.org.gr/" "https://handball.org.gr/" "https://www.handballpremier.gr/" "https://handballpremier.gr/" "https://www.handball.org.gr/omades/" "https://www.handball.org.gr/handball-premier/"; do
  code=$(curl -sSL -m 30 -A "$UA" -o /tmp/p.html -w "%{http_code} %{url_effective}" "$u"); echo "== $u -> $code $(wc -c </tmp/p.html)"
  grep -oiE '<img[^>]+(src|data-src)="[^"]+"[^>]*>' /tmp/p.html | grep -iE 'logo|team|club|σημ|emblem|uploads' | head -12
  grep -oiE 'href="[^"]*(team|omad|club|standings|vathmolog|premier)[^"]*"' /tmp/p.html | sort -u | head -10
done
