#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
cat > /tmp/t.mjs <<'JS'
import handler from "/home/runner/work/PAOK-calendar/PAOK-calendar/api/live.js";
const qs = [
  { src: "dp", fed: "hvl", day: "2026-10-31", side: "h" },
  { src: "dp", fed: "eope", id: "752" },
  { src: "dp", fed: "hvl", day: "2026-11-04", side: "h" },
];
for (const q of qs) {
  await new Promise((done) => {
    const res = { setHeader() {}, status(c) { this.c = c; return this; }, json(o) { console.log(JSON.stringify(q), this.c, JSON.stringify(o)); done(); } };
    handler({ query: q }, res);
  });
}
JS
node /tmp/t.mjs
