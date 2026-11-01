#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
cat > /tmp/t.mjs <<'JS'
const live = (await import(process.cwd() + "/api/live.js")).default;
const q = { src: "ea", code: "EACLUB27", cat: "ASF", gara: "2", tur: "001", gru: "3", a: "PBE", b: "ZVL" };
for (const query of [q, { ...q, a: "URA", b: "PAOK" }]) {
  await new Promise((r) => live({ query }, { setHeader() {}, status(c) { this.c = c; return this; },
    json(o) { console.log(this.c, JSON.stringify(o)); r(); } }));
}
JS
node /tmp/t.mjs
