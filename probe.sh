#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
echo "dp: $(curl -sS 'https://paokalendar.vercel.app/api/live?src=dp&fed=eope&id=756&side=h')"
