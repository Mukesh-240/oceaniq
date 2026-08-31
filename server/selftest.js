/**
 * Self-check for the non-trivial pure logic in rank.js.
 *   node selftest.js         asserts only
 *   node selftest.js --live  also runs one real GFW sweep and prints candidates
 *
 * This exists so a broken haversine or a silently-swallowed GFW failure fails
 * here rather than in a demo.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { haversineKm, bboxPolygon, mergeByMmsi, parseRanking, findCandidates } from "./rank.js";

/* haversine — known pair: roughly 5 570 km London->New York */
const d = haversineKm(-0.1276, 51.5072, -74.006, 40.7128);
assert.ok(Math.abs(d - 5570) < 30, `London->NY expected ~5570 km, got ${d.toFixed(1)}`);
assert.equal(haversineKm(10, 10, 10, 10), 0, "identical points must be 0 km");

/* one degree of latitude is ~111.2 km anywhere */
const oneDeg = haversineKm(0, 0, 0, 1);
assert.ok(Math.abs(oneDeg - 111.2) < 0.5, `1 deg lat expected ~111.2 km, got ${oneDeg.toFixed(2)}`);

/* bbox — closed ring, and the corner must be at least radius away */
const poly = bboxPolygon(6.7, 61.02, 50);
const ring = poly.coordinates[0];
assert.equal(ring.length, 5, "ring must be closed with 5 points");
assert.deepEqual(ring[0], ring[4], "first and last point must match");
const edge = haversineKm(61.02, 6.7, 61.02, ring[2][1]);
assert.ok(Math.abs(edge - 50) < 1, `north edge should sit ~50 km out, got ${edge.toFixed(2)}`);

/* longitude must stretch with latitude, or high-latitude boxes come out too narrow */
assert.ok(
  bboxPolygon(60, 0, 50).coordinates[0][1][0] > bboxPolygon(0, 0, 50).coordinates[0][1][0],
  "a box at 60N must span more degrees of longitude than one at the equator"
);

/* merge — closest approach wins, and a real gap survives the merge */
const merged = mergeByMmsi([
  { mmsi: "1", vessel_name: "A", flag: "IRN", distance_km: 30, ais_gap_hours: 6 },
  { mmsi: "1", vessel_name: null, flag: null, distance_km: 4, ais_gap_hours: null },
  { mmsi: "2", vessel_name: "B", flag: null, distance_km: 12, ais_gap_hours: null },
]);
assert.equal(merged.length, 2, "one row per MMSI");
const one = merged.find((r) => r.mmsi === "1");
assert.equal(one.distance_km, 4, "closest approach must win");
assert.equal(one.ais_gap_hours, 6, "a real AIS gap must survive the merge");
assert.equal(one.vessel_name, "A", "identity must not be lost to the closer row");

/* parseRanking — must survive the fences models emit despite being told not to */
assert.equal(parseRanking('```json\n{"ranked_vessels":[]}\n```').ranked_vessels.length, 0);
assert.throws(() => parseRanking('{"nope":1}'), /ranked_vessels/, "must reject a wrong-shaped object");
assert.throws(() => parseRanking("not json at all"), "must reject non-JSON");

console.log("pure logic: all assertions passed");

/* ── optional live sweep ───────────────────────────────────────────────── */
if (process.argv.includes("--live")) {
  for (const line of readFileSync(new URL("../.env", import.meta.url), "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)$/i);
    if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2].trim();
  }

  const t0 = Date.now();
  const r = await findCandidates({
    spill_lat: 6.6962, spill_lon: 61.0212,
    detected_time_utc: "2024-01-03T00:00:00Z",
    radius_km: 50, window_hours: 24,
  });

  console.log(`\nlive GFW sweep  ${Date.now() - t0} ms`);
  for (const q of r.queried) console.log(`  answered  ${q.dataset}  total=${q.total}`);
  for (const f of r.failed) console.log(`  FAILED    ${f}`);
  console.log(`\ncandidates: ${r.candidates.length}`);
  for (const c of r.candidates) {
    console.log(`  ${c.vessel_name ?? "(unnamed)"}  mmsi=${c.mmsi}  flag=${c.flag}  ` +
      `type=${c.vessel_type}  ${c.distance_km} km  dt=${c.time_gap_hours}h  ` +
      `gap=${c.ais_gap_hours}  course_dev=${c.course_deviation}`);
  }
  if (!r.candidates.length && !r.failed.length) console.log("  (confirmed zero: every dataset answered)");
  if (r.failed.length) console.log("\n  NOT a confirmed zero - some datasets failed.");
}
