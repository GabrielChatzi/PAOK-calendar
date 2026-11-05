#!/usr/bin/env bash
mkdir -p docs/logos; cd docs/logos
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
while read n u; do curl -sSL -m 30 -A "$UA" -o "$n" "$u"; echo "$n $(file -b "$n" | cut -c1-40)"; done <<'L'
ethnikos https://koecdn.twic.pics/media/shma-ethniku-ofpf-1758038638-0PxACujw.png
iraklis-b https://www.esake.gr/dat/esaketeam/00000011/photo_new_212846DF.png
athinaikos-hb https://www.handball.org.gr/media/yootheme/cache/c0/athinaikos-logo-c0953da2.jpg
kifisia-v https://www.volleyleague.gr/media/bearleague/logos/bl14424751662839.gif
protea https://apps.basket.gr/clubs/659/logo
korydallos https://epssalas.gr/wp-content/uploads/2020/10/PNG-ΚΟΡΥΔΑΛΛΟΣ2.png
asteras https://a.espncdn.com/i/teamlogos/soccer/500/8354.png
zaon https://images.dataproject.com/eope/TeamLogo/40/30/TeamLogo_121.jpg
L
