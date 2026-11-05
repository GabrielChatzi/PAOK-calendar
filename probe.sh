#!/usr/bin/env bash
mkdir -p docs/logos; cd docs/logos
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
while read n u; do curl -sSL -m 30 -A "$UA" -o "$n" "$u"; echo "$n $(stat -c %s "$n" 2>/dev/null) $(file -b "$n" | cut -c1-30)"; done <<'L'
bw-paok https://apps.basket.gr/clubs/2/logo
bw-ath https://apps.basket.gr/clubs/51/logo
fw-ody https://www.epo.gr/sites/default/files/styles/matches_club_logo/public/externals/d073e52756ee5f17232394ecaf0b0ec1.jpg?itok=QE7RdbHR
fw-paok https://www.epo.gr/sites/default/files/styles/matches_club_logo/public/externals/5772cc001561692e7ac1a3fa2b9cd87f.jpg?itok=adMbVNvk
ww-paok https://koecdn.twic.pics/media/paok-1757496962-8dCOYNiE.png
ww-lar https://koecdn.twic.pics/media/larisa-f-1789898479-XJuZR95A.png
w-paok https://koecdn.twic.pics/media/paok-1757496942-PvyEbv6R.png
w-voul https://koecdn.twic.pics/media/nov-logo-gr-1758965899-UA7wQDNs.png
b-paok https://www.esake.gr/dat/esaketeam/0000000C/photo_new_13BEDD3A.png
b-vik https://www.esake.gr/dat/esaketeam/0041ADCB/photo_new_FE76D0B4.png
fs-sal https://epssalas.gr/wp-content/uploads/2023/07/olympakos-salaminas.png
vw-pao https://images.dataproject.com/eope/TeamLogo/40/30/TeamLogo_119.jpg
vw-paok https://images.dataproject.com/eope/TeamLogo/40/30/TeamLogo_118.jpg
f-oly https://a.espncdn.com/i/teamlogos/soccer/500/435.png
f-paok https://a.espncdn.com/i/teamlogos/soccer/500/605.png
hw-pan https://www.handball.org.gr/media/yootheme/cache/84/panorama-new-84c6b388.jpg
hw-paok https://www.handball.org.gr/media/yootheme/cache/2a/PAOK-01-2a789158.jpg
v-kal https://www.volleyleague.gr/media/bearleague/logos/bl16909759871795.gif
v-paok https://www.volleyleague.gr/media/bearleague/logos/bl14724677852741.gif
L
