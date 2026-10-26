#!/usr/bin/env bash
mkdir -p docs/extra; UA="Mozilla/5.0 Chrome/130"
for q in "CompetitionMatches.aspx?ID=19&PID=20&type=LegList" "CompetitionMatches.aspx?ID=19&PID=20&type=All" "CompetitionCalendar.aspx?ID=19" "MatchesCalendar.aspx?ID=19" "CompetitionMatches.aspx?ID=19&PID=20"; do
  f="docs/extra/$(echo "$q" | tr -c 'A-Za-z0-9' _).html"
  curl -sSL -A "$UA" --max-time 40 -o "$f" -w "$q %{http_code} %{size_download}\n" "https://eope-web.dataproject.com/$q" >> docs/extra/log.txt || echo "FAIL $q" >> docs/extra/log.txt
done
