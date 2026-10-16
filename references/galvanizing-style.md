# Approved galvanizing reference style

This preset records the user's approved 2026-10-15 figure decisions. Apply when reproducing that project or when explicitly requested; coordinates, values, and camera are not defaults for unrelated vessels.

- English manuscript text, Arial, white background, subdued bath/roller outlines, 1 m scale reference where physically appropriate.
- Camera elevation 23 degrees, azimuth -60 degrees, roll 180 degrees. Rotate the view with camera roll; keep text upright and data coordinates unchanged.
- Steel strip: sloping plane, curved wrap, vertical plane as one visually continuous ribbon. Same gray `#A8ADB3`, alpha 0.35. No internal seam or join lines; outer perimeter only. Preserve actual straight-strip positions/width. The curved connector is illustrative display geometry and must be disclosed; it never modifies fields, fluid masks, or tracks.
- Three quantity columns: dissolved Fe concentration change, dissolved Al concentration change, absolute precipitated Fe2Al5 mass concentration. Use separate concentration legends and an independent `viridis` path-time legend.
- For the approved baseline only: `delta c = rho(t)*Y(t) - rho0*Y0`, with rho0=6600 kg/m3, YFe0=3.5e-5, YAl0=0.003. Initial Fe reference is 0.231 kg/m3; Al is 19.8 kg/m3. Recompute for a different actual reference state; do not reuse these values by habit.
- Fe/Al: `RdBu_r`, blue depletion, red increase. The approved project uses explicit asymmetric zero-centered limits and fixed levels from its display manifest; disclose different slopes either side of zero. Do not infer exact numeric ranges from this document. Fe2Al5: `YlOrBr`, positive absolute-concentration surfaces; preserve signed undershoots in arrays.
- Source locations follow the actual UDF. Fe near-wall volumetric band: x=-0.40 +/-0.04, y=-0.95..0.95, z=-1.20..0 m. Use an orange leader label `Fe source band`. It is not a strict implemented surface-flux boundary. Al fixed volumetric feed: x=-1.80..-1.20, y=-0.45..0.45, z=1.60..2.30 m. Draw a black dashed box. These are independent of plume shape. Verify UDF coordinates again if model versions change.
- Initial panel: actual births during 0–10 s together with saved concentration at 10 s. It is not an instantaneous release at t=0. Then stages 15,30,50,80,120,160,200 s for the approved 1 m/s,455 C example.
- Original cohort selection includes visibility at 15 s; disclose this survival condition. Connect consecutive available 5 s particle checkpoints only. Birth-to-first-observation motion is unavailable and must not be invented.
- The existing project used a 0.1 m volume-weighted grid, nearest-occupied display gap filling, roller masking, and linear marching cubes with no smoothing. Preserve its published aggregation/extrapolation disclosure when reproducing it. New projects should choose their own resolution and use bounded fill only when justified.
- Output: eight three-quantity stage figures, one eight-stage overview per quantity, 600 dpi PNG/LZW TIFF, editable-text SVG, and 11-page PDF. Other requested layouts/stage counts take precedence.

`assets/galvanizing.style.json` provides a portable configuration fragment. Merge it with real data keys, source mapping, stage indices, limits, and provenance. It is intentionally not a ready-to-run solver case or data extractor.
