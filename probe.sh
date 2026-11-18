mkdir -p out
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
i=0
while read -r url; do
  i=$((i+1))
  code=$(curl -sSL -A "$UA" -H "Accept-Language: el-GR,el" --max-time 25 -o "out/$i.html" -w "%{http_code} %{size_download} %{url_effective}" "$url")
  echo "$i $code  <= $url"
done <<'L'
https://www.matchmoney.com.gr/athlitikes-metadosis/programma-tv-18-11-2026/
https://www.matchmoney.com.gr/athlitikes-metadosis/programma-tv-19-11-2026/
https://www.matchmoney.com.gr/athlitikes-metadosis/
https://www.novasports.gr/tv-program/
https://www.novasports.gr/programma/
https://www.cosmotetv.gr/portal/residential/program
https://www.cosmotetv.gr/portal/residential/program/sports
https://www.ertsports.gr/programma/
https://www.sport24.gr/tv/
https://www.gazzetta.gr/tv-program
https://www.contra.gr/tv/
https://www.sportime.gr/tv-program/
https://www.athlitiko-programma.gr/
https://www.agones.gr/tv
https://paok24.com/mpasket
https://www.paokbc.gr/el/news
https://www.paokfc.gr/nea/
https://www.betarades.gr/athlitikes-metadoseis/
https://www.metadoseis.gr/
https://www.tvguide.gr/
https://www.programmatileorasis.gr/
L
