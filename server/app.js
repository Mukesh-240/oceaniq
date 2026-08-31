/**
 * OceanIQ backend. Serves the dashboard and the ranking API from one origin so
 * the frontend fetch needs no CORS handling.
 *
 *   npm install && npm start   ->  http://127.0.0.1:3000/index.html
 */
import express from "express";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import rankRouter from "./rank.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(HERE, "..");

/**
 * Minimal .env loader — one dependency less than `dotenv` for ~10 lines.
 * Does not override anything already set in the real environment.
 */
function loadEnv(path) {
  let raw;
  try {
    raw = readFileSync(path, "utf8");
  } catch {
    return; // no .env is fine; the checks below report what is actually missing
  }
  for (const line of raw.split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)$/i);
    if (!m) continue;
    const [, k, v] = m;
    if (process.env[k] === undefined) {
      process.env[k] = v.trim().replace(/^["']|["']$/g, "");
    }
  }
}
loadEnv(resolve(REPO_ROOT, ".env"));

const app = express();
app.use(express.json({ limit: "1mb" }));

app.use("/api", rankRouter);

app.get("/api/health", (_req, res) => {
  // Report which secrets are present WITHOUT echoing them.
  res.json({
    ok: true,
    gfw_token: Boolean(process.env.GFW_API_TOKEN),
    gemini_key: Boolean(process.env.GEMINI_API_KEY),
  });
});

// Static last, so /api never gets shadowed by a file of the same name.
app.use(express.static(REPO_ROOT, { extensions: ["html"] }));

const PORT = Number(process.env.PORT) || 3000;
app.listen(PORT, "127.0.0.1", () => {
  const miss = ["GFW_API_TOKEN", "GEMINI_API_KEY"].filter((k) => !process.env[k]);
  console.log(`OceanIQ server  http://127.0.0.1:${PORT}/index.html`);
  if (miss.length) console.warn(`  WARNING: missing env: ${miss.join(", ")} — /api/rank-vessels will 502`);
});
