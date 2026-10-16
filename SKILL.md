---
name: cfd-particle-figures
description: "Create reproducible publication figures from CFD and particle-tracking results: birth regions, sampled trajectories, semitransparent 3D concentration fields, and surface deposition maps in metallurgical refining, galvanizing, ladles, tundishes, and related process vessels. Use for simulation postprocessing figures; schematic-only illustrations and solver setup are outside this skill."
---

# CFD Particle Figures

Turn saved simulation results into scientifically traceable, reusable manuscript figures. Preserve the user's chosen solver, actual data, geometry, and approved visual style. This skill authorizes figure work within the user's request; it does not authorize new simulations, remote deletion, or changes to physical models.

## Choose the output

Use the requested plot type. For particle generation and motion, prefer the same actual cohort across a sequence of saved times. Eight stages are a useful default when the user asks for a process sequence, not a universal requirement. For field comparison, use one panel per quantity and a common stage/camera. For adsorption or deposition, map the actual wall-associated quantity on the actual wall mesh; see [references/scenarios.md](references/scenarios.md).

The bundled renderer handles time sequences, transparent scalar isosurfaces, sampled particle paths, triangular equipment surfaces, and triangular wall scalar maps. It accepts a portable NPZ plus JSON scene, not native Fluent CAS/DAT. Write a small project-local adapter for the actual solver export. Read [references/data-contract.md](references/data-contract.md) before creating that adapter or using the renderer. Reuse existing verified extraction code rather than guessing binary field names or cell ordering.

Read [references/galvanizing-style.md](references/galvanizing-style.md) when the user requests the previously approved galvanizing style. For other refining equipment, read only the relevant mode in [references/scenarios.md](references/scenarios.md). Keep species, source coordinates, camera orientation, temperatures, and time windows in project configuration.

## Establish meaning before drawing

- Inspect physical timestamps, coordinates/units, scalar definitions, density basis, source hooks, wall IDs, and particle identity/parcel weights. Map fields by actual exported metadata or UDF, never by cloud shape. Distinguish dissolved Al from the letters "AI" where context establishes aluminium.
- Mass concentration is `rho * Y` only if the saved scalar is a mass fraction on that same phase/density basis. A UDS may instead be concentration, moments, or another quantity. State absolute concentration versus change from a documented initial reference. For nonuniform references, compare aligned spatial fields.
- Eulerian precipitate concentration, particle parcel count, physical particle number density, volume fraction, reaction rate, and deposited mass are different outputs. Label the implemented quantity. Do not double-count a precipitate tracked in both Eulerian and Lagrangian descriptions.
- Derive source markers from the configured boundary, UDF, injection file, or a documented measured region. Label a near-wall volume-source approximation as such; a cloud is not a source map.
- Select a real birth region/window and retain stable composite particle IDs. If selection requires particles to survive to a later checkpoint, disclose this survival bias. Missing positions stay gaps. Do not invent common origins, trajectories, particle births, or states between missing snapshots.
- If birth metadata is absent, label the first observed positions as first observed. A birth-window panel with a later concentration snapshot must display both times. Restarted in-memory capture counters may be incomplete; never label them as full-run deposition without evidence.

## Render consistently

Use English labels for manuscript figures unless the user requests otherwise. Prefer Arial if installed, white background, readable text at final physical size, restrained outlines, and separate field and path-time colorbars. Use equal physical scaling on the spatial axes.

Keep camera, aspect ratio, scalar limits, isosurface levels, and opacity fixed across the stated comparison set. Fit ranges across all compared times/cases or accept documented explicit limits. Use a sequential palette for positive absolute quantities and a diverging palette centered on zero for signed changes. Symmetric change limits are the general default. If an asymmetric zero-centered scale is necessary, state its two slopes and numeric limits; color intensity cannot be compared across signs directly. A one-sided field needs no invented opposite-sign values.

Use a few transparent isosurfaces with moderate opacity, and preserve trajectory visibility. Empty or spatially constant fields may have no surfaces; show a truthful annotation rather than manufacturing a cloud. Preserve signed numerical undershoots and report their scale. Display-only clipping or positive-only precipitate surfaces must be recorded.

Keep original equipment coordinates. A display connector may join visually separate segments only when requested or warranted by established physical continuity. Match width, color, and opacity, hide internal seam lines, retain only outer boundaries, and disclose the connector. Never use illustrative connectors as CFD walls, field masks, sampling surfaces, or modified trajectories. For moving geometry, use the matching time's actual geometry/mask.

Use the original mesh or a justified display grid. If gridding cells, weight concentration by fluid cell volume; do not average unweighted samples. Keep solids and missing fluid data separate. Gap filling is optional display extrapolation: bound its distance, avoid disconnected fluid regions, record it, and keep original arrays. Never smooth paths or clouds to conceal unresolved data.

For overlapping translucent surfaces where depth ordering materially changes interpretation, prefer a suitable VTK/ParaView/PyVista renderer if already available. Matplotlib's polygon sorting is a preview limitation; inspect output before claiming accurate occlusion.

## Reusable implementation

Dependencies: Python, NumPy, Matplotlib, SciPy, scikit-image, Pillow. Use available workspace runtimes; install only if needed within the authorized environment.

Copy [assets/scene.example.json](assets/scene.example.json) into the project and adapt it to actual exported fields. The executable helper keeps raw inputs read-only, refuses output into the skill folder or existing generated files, records input hashes and rendering choices, and exports selected stages.

```text
python <skill-dir>/scripts/render_scene.py <project>/scene.json --validate-only
python <skill-dir>/scripts/render_scene.py <project>/scene.json --preview
python <skill-dir>/scripts/render_scene.py <project>/scene.json
```

`--preview` writes a small PNG of the first stage into a separate preview folder; inspect it before full export. `--validate-only` checks shapes, timestamps, scales, and identities without writing figures. `scripts/figure_tools.py` provides volume-weighted gridding, gap-safe trajectory segments, bounded display filling, and seamless ribbon faces for adapters.

The helper is a starting renderer, not a native solver reader or an automatic publication guarantee. Adapt it project-locally when a different layout, geometry representation, or journal format is required. Keep this reusable skill free of project datasets, absolute machine paths, account credentials, and solver-specific assumptions.

## Verify and deliver

Inspect a representative stage and overview at manuscript size: physical orientation, real source positions, solids exclusion, field/path alignment, birth labels, continuous surfaces, colorbar units, transparency, text overlap, and missing-data gaps. Check an early and late stage if the evolution is the main claim. Record selection, any aggregation/extrapolation, fixed color limits, and input timestamps/hashes in the manifest and caption.

General manuscript defaults are 600 dpi PNG and LZW TIFF, SVG with editable text, and multipage PDF. These are configurable, not universal journal requirements. Verify file counts, dimensions, requested DPI, and the SVG text setting. A figure rendering from 3D data is a 2D projection; SVG text can be editable without retaining an editable 3D scene. Retain configuration, adapter, manifest, and data provenance so the figures can be regenerated.

If the task requests a current journal's exact production compliance, verify that journal's current requirements before claiming compliance. Finish with the delivered file links and any material scientific limitation; do not merely propose a workflow.
