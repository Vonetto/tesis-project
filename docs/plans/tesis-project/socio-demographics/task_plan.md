# Task Plan — Socio-demographic Integration (Censo/CASEN ↔ Zonas777)

## Goal
Integrate socio-demographic data (Censo 2024; CASEN if needed) with Zonas777 geometry to enrich OD/buffer analyses.

## Constraints / Guardrails
- Prefer the most disaggregated spatial level available (manzana/entidad).
- Use existing Zonas777 geometry.
- Keep outputs in project data folders; planning files stored in 3 locations.
- No interpretations in notes; only objective results.

## Milestones
- [x] Identify official download sources for Censo 2024 cartography + manzana/entidad base (links + file sizes).
- [x] Decide storage path (external drive) and download cartography ZIP.
- [x] Obtain manzana/entidad base table (official zip).
- [x] Download microdatos (personas/hogares/viviendas) + dictionary.
- [x] Inspect variables and pick candidate socio-demographic columns.
- [x] Build a spatial join plan (Zonas777 ↔ manzana/entidad) and aggregation strategy.
- [x] Validate join coverage using **Manzanas cartography + MANZENT** (diagnostics now non‑zero).
- [x] Propose integration paths for origin-only and OD (origin/destination) joins.
- [x] Confirm methodological preference with profesora (prioritize origin; evaluate both).
- [ ] Implement model-ready outputs for both variants (origin-only and OD origin+destination) in OD buffers pipeline.
- [ ] Run comparative estimations with socio-demo variants and archive objective stats/params.

## Next Actions
- [x] Choose default output: **intersects_area** (due to ~17% multi‑zone).
- [x] Quick sanity: verify shares within [0,1] or document if certain counts can exceed denominators.
- [x] Run buffers ↔ Censo join and validate coverage (pct_missing_censo_*).
- [ ] Attach socio-demo features to Option1 dataset (origin baseline first).
- [x] Attach socio-demo features to Option1 dataset (origin baseline first).
- [ ] Extend notebook section for socio-demo OD variant and side-by-side results.
