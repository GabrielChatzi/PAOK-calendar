#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
cat > /tmp/t.mjs <<'JS'
import handler from "/home/runner/work/PAOK-calendar/PAOK-calendar/api/live.js";
for (const q of [{ src: "gs", key: "RFJIN037I07QV520B7WEXKV1GYNA31", day: "2026-10-31", side: "a" }, { src: "gs", key: "RFJIN037I07QV520B7WEXKV1GYNA31", day: "2026-11-01", side: "h" }]) {
  await new Promise((done) => handler({ query: q }, { setHeader() {}, status(c) { this.c = c; return this; }, json(o) { console.log(JSON.stringify(q), this.c, JSON.stringify(o)); done(); } }));
}
JS
node /tmp/t.mjs
