// Μεταβιβάσεις: τα σημεία που δεν πρέπει να χαλάσουν (χωρίς βάση).
import assert from "node:assert/strict";
import { test } from "node:test";

const tx = await import("../api/tx.js");
const H = 3600e3;
const athens = (s) => new Date(s).getTime(); // με ρητή μετατόπιση ώρας στο κείμενο

test("χρονόμετρο: 3 «ενεργές» ώρες, παγώνει 00:00–08:00 ώρα Ελλάδας", () => {
  const cases = [
    ["2026-11-07T14:00+02:00", 3, "2026-11-07T17:00+02:00"], // μέρα
    ["2026-11-07T23:00+02:00", 3, "2026-11-08T10:00+02:00"], // 1 ώρα πριν τα μεσάνυχτα, 2 μετά τις 08:00
    ["2026-11-07T21:30+02:00", 3, "2026-11-08T08:30+02:00"],
    ["2026-11-08T02:00+02:00", 3, "2026-11-08T11:00+02:00"], // ξεκινά μέσα στη νύχτα
    ["2026-11-07T22:00+02:00", 1, "2026-11-07T23:00+02:00"],
    ["2026-07-10T23:00+03:00", 3, "2026-07-11T10:00+03:00"], // θερινή ώρα
    ["2026-03-28T23:00+02:00", 3, "2026-03-29T10:00+03:00"], // αλλαγή σε θερινή μέσα στη νύχτα
    ["2026-10-24T23:00+03:00", 3, "2026-10-25T10:00+02:00"], // αλλαγή σε χειμερινή μέσα στη νύχτα
  ];
  for (const [from, h, want] of cases) assert.equal(new Date(tx.addActive(athens(from), h * H)).toISOString(), new Date(want).toISOString(), from);
});

test("νύχτα", () => {
  assert.equal(tx.isQuiet(athens("2026-11-08T00:00+02:00")), true);
  assert.equal(tx.isQuiet(athens("2026-11-08T07:59+02:00")), true);
  assert.equal(tx.isQuiet(athens("2026-11-08T08:00+02:00")), false);
  assert.equal(tx.isQuiet(athens("2026-11-07T23:59+02:00")), false);
});

test("θύρα: «Θύρα 4», «θ4», « 4 » είναι η ίδια", () => {
  for (const g of ["Θύρα 4", "θύρα 4", "θ4", "Θ.4", " 4 "]) assert.equal(tx.gateKey(g), "4", g);
  assert.notEqual(tx.gateKey("14"), tx.gateKey("4"));
});

test("ΑΦΜ με ψηφίο ελέγχου", () => {
  assert.equal(tx.validAfm("123456783"), true);
  assert.equal(tx.validAfm("123456789"), false);
  assert.equal(tx.validAfm("000000000"), false);
  assert.equal(tx.validAfm("12345678"), false);
});
