#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import json, build_calendars as b
for sec in ("waterpolo","waterpolo-women"):
    for fn in (b.waterpolo_matches, b.european_waterpolo_matches):
        for m in fn(sec):
            if m.live: print(sec, m.day, m.home, "-", m.away, json.dumps(m.live))
PY
cat > /tmp/t.mjs <<'JS'
import handler from "/home/runner/work/PAOK-calendar/PAOK-calendar/api/live.js";
const qs = [
  { src: "koe", cat: "ASM", gara: "65", tur: "A01", gru: "1", a: "9175200", b: "9175106" },
  { src: "ea", code: "EACLUB27", cat: "ASF", gara: "2", tur: "001", a: "ZVL", b: "PAOK" },
  { src: "ea", code: "EACLUB27", cat: "ASF", gara: "2", tur: "001", a: "URA", b: "PAOK" },
];
for (const q of qs) {
  await new Promise((done) => {
    const res = { h: {}, setHeader(k, v) { this.h[k] = v; }, status(c) { this.c = c; return this; },
      json(o) { console.log(q.src, q.a, this.c, JSON.stringify(o)); done(); } };
    handler({ query: q }, res);
  });
}
JS
node /tmp/t.mjs
