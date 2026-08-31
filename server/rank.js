/**
 * POST /api/rank-vessels — real GFW AIS pull, then Gemini ranking.
 *
 * Hard constraint, probed against this token rather than assumed:
 *   GET /v3/vessels/{vesselId}/tracks?datasets[0]=public-global-all-tracks:latest
 *     -> 403 "You do not have permission to access this dataset"
 *   GET /v3/vessels/{vesselId}/tracks?datasets[0]=public-global-fishing-tracks:latest
 *     -> 404
 * Multi-point tracks are unavailable, so everything below is built on
 * /v3/events, which returns ONE position per event. Consequence: course_deviation
 * cannot be computed (it needs heading before vs after closest approach, i.e. >=2
 * positions) and is emitted as null, never guessed. ais_gap_hours comes from the
 * gaps-events dataset, which is a real measurement rather than an interpolation.
 */
import express from "express";
import { GoogleGenAI } from "@google/genai";

const router = express.Router();

const GFW_BASE = "https://gateway.api.globalfishingwatch.org";
// Cloudflare in front of the API blocks the default Node user agent.
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OceanIQ/0.1";
const EARTH_RADIUS_KM = 6371.0;
const DEG_LAT_KM = 111.32;
const GFW_TIMEOUT_MS = 90_000;

const EVENT_DATASETS = {
  gaps: "public-global-gaps-events:latest",
  fishing: "public-global-fishing-events:latest",
  loitering: "public-global-loitering-events:latest",
  encounters: "public-global-encounters-events:latest",
  port_visits: "public-global-port-visits-events:latest",
};

/* ────────────────────────── geometry ────────────────────────── */

export function haversineKm(lon1, lat1, lon2, lat2) {
  const rad = (d) => (d * Math.PI) / 180;
  const p1 = rad(lat1);
  const p2 = rad(lat2);
  const a =
    Math.sin(rad(lat2 - lat1) / 2) ** 2 +
    Math.cos(p1) * Math.cos(p2) * Math.sin(rad(lon2 - lon1) / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(a));
}

/** Closed GeoJSON Polygon bbox around a point. GFW wants [lon, lat]. */
export function bboxPolygon(lat, lon, radiusKm) {
  const dLat = radiusKm / DEG_LAT_KM;
  // cos(lat) -> 0 at the poles; floor it so the box stays finite.
  const dLon =
    radiusKm / (DEG_LAT_KM * Math.max(0.01, Math.cos((lat * Math.PI) / 180)));
  const [w, e, s, n] = [lon - dLon, lon + dLon, lat - dLat, lat + dLat];
  return { type: "Polygon", coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] };
}

/* ────────────────────────── GFW ────────────────────────── */

function gfwToken() {
  const t = process.env.GFW_API_TOKEN;
  if (!t) throw new Error("GFW_API_TOKEN is not set");
  return t.trim();
}

/**
 * Spatial filter goes in the BODY as `geometry` — query-param bbox and
 * `region.geojson` both return 422 here. Success is HTTP 201, not 200.
 */
async function fetchEvents(dataset, startDate, endDate, geometry, limit = 50) {
  const qs = new URLSearchParams({ limit: String(limit), offset: "0" });
  const res = await fetch(`${GFW_BASE}/v3/events?${qs}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${gfwToken()}`,
      "User-Agent": UA,
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ datasets: [dataset], startDate, endDate, geometry }),
    signal: AbortSignal.timeout(GFW_TIMEOUT_MS),
  });

  const text = await res.text();
  if (res.status !== 200 && res.status !== 201) {
    throw new Error(`${dataset} HTTP ${res.status}: ${text.slice(0, 180)}`);
  }
  return JSON.parse(text);
}

const hoursBetween = (a, b) => Math.abs(new Date(a) - new Date(b)) / 3.6e6;

function normaliseOne(entry, kind, spillLat, spillLon, detectedTime) {
  const v = entry.vessel || {};
  const lat = entry.position?.lat ?? entry.lat;
  const lon = entry.position?.lon ?? entry.lon;
  if (lat == null || lon == null) return null;

  const start = entry.start || entry.eventStart || null;
  const dur = Number(entry.durationHours ?? entry.duration ?? 0) || null;

  return {
    vessel_name: v.name || v.shipname || null,
    mmsi: v.ssvid || v.mmsi || null,
    flag: v.flag || null,
    vessel_type: v.type || kind,
    distance_km: Number(haversineKm(lon, lat, spillLon, spillLat).toFixed(2)),
    time_gap_hours: start ? Number(hoursBetween(start, detectedTime).toFixed(2)) : null,
    course_deviation: null, // see file header: needs >=2 positions, token has none
    ais_gap_hours: kind === "gaps" ? dur : null,
    past_violations: [], // GFW exposes no violation history on this token
    _position: [lon, lat],
    _event_time: start,
  };
}

/** Merge duplicate MMSIs across datasets; closest approach wins, real gaps stick. */
export function mergeByMmsi(rows) {
  const byId = new Map();
  for (const r of rows) {
    const key = r.mmsi || r.vessel_name;
    if (!key) continue;
    const prev = byId.get(key);
    if (!prev) {
      byId.set(key, r);
      continue;
    }
    const win = r.distance_km < prev.distance_km ? r : prev;
    win.ais_gap_hours = prev.ais_gap_hours ?? r.ais_gap_hours;
    win.vessel_name = win.vessel_name || prev.vessel_name || r.vessel_name;
    win.flag = win.flag || prev.flag || r.flag;
    byId.set(key, win);
  }
  return [...byId.values()];
}

export async function findCandidates({ spill_lat, spill_lon, detected_time_utc, radius_km, window_hours }) {
  const geometry = bboxPolygon(spill_lat, spill_lon, radius_km);
  const detected = new Date(detected_time_utc);

  // Discharge precedes detection — the slick drifts before anyone images it — so
  // the window runs backwards from detection, not symmetrically around it.
  const startDate = new Date(detected.getTime() - window_hours * 3.6e6).toISOString().slice(0, 10);
  const endDate = detected.toISOString().slice(0, 10);

  const settled = await Promise.allSettled(
    Object.entries(EVENT_DATASETS).map(async ([kind, ds]) => ({
      kind,
      ds,
      data: await fetchEvents(ds, startDate, endDate, geometry),
    }))
  );

  const queried = [];
  const failed = [];
  const rows = [];

  for (const r of settled) {
    if (r.status === "rejected") {
      // A failed request is NOT a zero result. Conflating them publishes a
      // network fault as evidence of absence.
      failed.push(String(r.reason?.message || r.reason).slice(0, 180));
      continue;
    }
    const { kind, ds, data } = r.value;
    queried.push({ dataset: ds, total: data.total ?? 0 });
    for (const e of data.entries || []) {
      const n = normaliseOne(e, kind, spill_lat, spill_lon, detected_time_utc);
      if (!n || n.distance_km > radius_km) continue;
      // GFW reports drifting fishing gear and AIS marker buoys as "vessels".
      // They carry no fuel or cargo and cannot discharge, so ranking them as
      // suspects is a category error - and they sit at 0 km, which would put
      // one straight at the top. The Python pipeline skips these too.
      if (n.vessel_type === "gear") continue;
      rows.push(n);
    }
  }

  return { candidates: mergeByMmsi(rows), queried, failed, startDate, endDate };
}

/* ────────────────────────── Gemini ────────────────────────── */

const SYSTEM_PROMPT = `You are a maritime forensics analyst supporting NTRO in identifying the vessel most likely responsible for a detected oil spill, using satellite spill-detection output correlated against nearby AIS vessel-track data.

TASK
For each candidate vessel, compute a suspicion_score (0-100) and a short reason (max 2 sentences), weighing:
- Proximity to spill (closer = higher)
- Time correlation (closer to detected_time = higher)
- Course deviation near the incident (sharp turns = higher)
- AIS transponder gaps just before/during the window (a gap = higher - vessels going dark to mask discharge is a known real-world pattern)
- Cargo/vessel type risk (tankers > cargo > other)
- Any past violation history

RULES
- Do not invent vessels not present in the input.
- Never assert guilt - scores represent statistical likelihood only, phrase reasons as "consistent with" / "elevated likelihood due to", not "this vessel caused the spill."
- If data for a vessel is sparse, say so in the reason and score it lower rather than guessing.
- Scores must be internally consistent - rank order should follow directly from the weighted factors above.
- A null field means the datum was UNAVAILABLE, not zero and not benign. Never read a null course_deviation or null ais_gap_hours as evidence of innocence OR of guilt; treat it as sparse data and score lower per the rule above.
- An AIS gap alone must never outrank a vessel that scores strongly on proximity and time. Going dark is one clue among several, not proof.

OUTPUT - return ONLY this JSON, ranked descending by suspicion_score:
{"incident":"","ranked_vessels":[{"rank":1,"vessel":"","mmsi":"","suspicion_score":0,"reason":""}]}`;

const STRICTER =
  "\n\nYour previous reply was not valid JSON. Return ONLY the JSON object. No prose, no markdown fences, no commentary.";

export function parseRanking(text) {
  // Models fence JSON even when told not to; strip it before parsing.
  const cleaned = text.trim().replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
  const parsed = JSON.parse(cleaned);
  if (!Array.isArray(parsed.ranked_vessels)) throw new Error("missing ranked_vessels array");
  return parsed;
}

async function rankWithGemini(payload) {
  const key = process.env.GEMINI_API_KEY;
  if (!key) throw new Error("GEMINI_API_KEY is not set");
  const ai = new GoogleGenAI({ apiKey: key });

  const call = (system) =>
    ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: JSON.stringify(payload),
      config: {
        systemInstruction: system,
        responseMimeType: "application/json",
        temperature: 0, // an attribution ranking should not vary run to run
      },
    });

  let lastErr;
  for (const system of [SYSTEM_PROMPT, SYSTEM_PROMPT + STRICTER]) {
    const res = await call(system);
    const text = res.text ?? "";
    try {
      return parseRanking(text);
    } catch (e) {
      lastErr = new Error(
        `Gemini returned unparseable JSON: ${e.message}. Raw: ${text.slice(0, 300)}`
      );
    }
  }
  throw lastErr; // fail loudly rather than guessing a ranking
}

/* ────────────────────────── route ────────────────────────── */

router.post("/rank-vessels", async (req, res) => {
  const {
    incident_id = "unnamed-incident",
    spill_lat,
    spill_lon,
    detected_time_utc,
    radius_km = 50,
    window_hours = 24,
  } = req.body || {};

  // Validate at the boundary: a NaN latitude silently becomes a worldwide query.
  const bad = [];
  if (!Number.isFinite(spill_lat) || Math.abs(spill_lat) > 90) bad.push("spill_lat");
  if (!Number.isFinite(spill_lon) || Math.abs(spill_lon) > 180) bad.push("spill_lon");
  if (!detected_time_utc || Number.isNaN(new Date(detected_time_utc).getTime()))
    bad.push("detected_time_utc");
  if (!Number.isFinite(radius_km) || radius_km <= 0 || radius_km > 500) bad.push("radius_km");
  if (!Number.isFinite(window_hours) || window_hours <= 0 || window_hours > 8760)
    bad.push("window_hours");
  if (bad.length) return res.status(400).json({ error: `invalid or missing: ${bad.join(", ")}` });

  const t0 = Date.now();
  try {
    const { candidates, queried, failed, startDate, endDate } = await findCandidates({
      spill_lat, spill_lon, detected_time_utc, radius_km, window_hours,
    });

    const provenance = {
      source: "Global Fishing Watch /v3/events",
      datasets_queried: queried,
      datasets_failed: failed,
      window: { startDate, endDate, window_hours, radius_km },
      limitations: [
        "course_deviation is null for every vessel: multi-point AIS tracks need public-global-all-tracks, which returns 403 for this token.",
        "past_violations is empty: no violation history is exposed on this token.",
      ],
      gfw_ms: Date.now() - t0,
    };

    if (!candidates.length) {
      // Never fabricate. Distinguish a real empty result from a broken query.
      const partial = failed.length > 0;
      return res.json({
        incident: incident_id,
        ranked_vessels: [],
        message: partial
          ? `No AIS traffic resolved in range, but ${failed.length} of ${Object.keys(EVENT_DATASETS).length} GFW datasets failed — this is NOT a confirmed zero.`
          : "No AIS traffic in range. All GFW datasets answered and reported no vessels within the search radius and time window.",
        complete: !partial,
        provenance,
      });
    }

    const ranked = await rankWithGemini({
      incident: incident_id,
      spill: { spill_lat, spill_lon, detected_time_utc, radius_km, window_hours },
      candidates: candidates.map(({ _position, _event_time, ...c }) => c),
    });

    // The model ranks; it does not get to invent. Drop anything not in the input.
    const known = new Set(candidates.map((c) => String(c.mmsi)));
    const kept = (ranked.ranked_vessels || []).filter((v) => known.has(String(v.mmsi)));
    const dropped = (ranked.ranked_vessels || []).length - kept.length;

    res.json({
      incident: ranked.incident || incident_id,
      ranked_vessels: kept.map((v, i) => ({ ...v, rank: i + 1 })),
      complete: failed.length === 0,
      candidates, // raw normalised input, so the ranking stays auditable
      provenance: { ...provenance, total_ms: Date.now() - t0, hallucinated_vessels_dropped: dropped },
    });
  } catch (err) {
    console.error("[rank-vessels]", err);
    res.status(502).json({ error: String(err.message || err), incident: incident_id });
  }
});

export default router;
