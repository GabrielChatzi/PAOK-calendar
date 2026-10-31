#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
cat > /tmp/t.mjs <<'JS'
import handler from "/home/runner/work/PAOK-calendar/PAOK-calendar/api/live.js";
const qs = [
  { src: "ehf", id: "202712020703021" },
  { src: "ehf", id: "202712020703006" },
  { src: "eok", day: "2026-10-31", side: "a", comp: "RISING" },
  { src: "eok", day: "2026-11-07", side: "h", comp: "WOMEN" },
];
for (const q of qs) await new Promise((done) => handler({ query: q }, { setHeader() {}, status(c) { this.c = c; return this; }, json(o) { console.log(JSON.stringify(q), this.c, JSON.stringify(o)); done(); } }));
JS
node /tmp/t.mjs
python3 - <<'PY'
import json, urllib.request
UA="Mozilla/5.0"; base="https://ehfec.eurohandball.com"
q="competitionId=HUvNPxVw-FYaDNYG5p1ZLw&roundId=&currentContentId=138879"
d=json.loads(urllib.request.urlopen(urllib.request.Request(f"{base}/umbraco/api/competitionmatchesapi/GetInitMatches?{q}",headers={"User-Agent":UA}),timeout=40).read())["matches"]
print("finished ids:", [m["matchID"] for m in d if m.get("isFinished")][:3])
PY
