# Adapt to other process vessels

These are figure modes, not prescribed physical models. Read the mode that matches the user's data. The shared renderer and style must not imply an unimplemented reaction, wall flux, or capture model.

## Ladle refining and gas stirring

Show actual bath, plug/nozzle and interface geometry. Choose dissolved solute, temperature, reaction-product concentration, or gas volume fraction as separate quantities with explicit units/phase basis. Distinguish tracked inclusions from gas bubbles and from Eulerian phases. Draw a fixed stirring source from boundary/UDF geometry; do not call the whole gas plume a release surface. Use real inclusion births if a population model saves them; otherwise say injection sites or first observed sites. Gas fraction is dimensionless and must not inherit kg/m3 concentration labels.

## Tundish, RH, and vacuum refining

Show actual inlet/outlet, weirs/baffles or snorkels, and the actual liquid domain. Keep connected channels and vessel scale consistent. Compare a stable cohort or a documented seeded population; distinguish injection time, transit time, and physical simulation time. Respect domain exits and missing checkpoints. A particle disappearing from data is not automatically a trapped/removed particle. Removal efficiency needs saved fate/flux statistics and a defined denominator.

## Precipitation, inclusion growth, and reactive baths

Show dissolved reactant changes and absolute product concentration in independent panels. Use reaction-rate fields for generation regions only if that quantity was actually saved. A tracked product cohort can demonstrate sampled motion; an Eulerian concentration cannot establish individual particle paths. Separate equivalent precipitation mass concentration from a physical number-density distribution. Record stoichiometry/species mapping from the implemented model before interpreting release/generation.

## Wall adsorption, deposition, and capture

Select the quantity actually available:

| Available data | Defensible output | Required normalization |
| --- | --- | --- |
| Face-associated capture events with mass/parcel weight | Cumulative deposited mass per area | `sum(captured mass)/face area`, kg/m2 |
| Face-associated events during a fixed interval | Mean deposition mass flux | `sum(mass)/(area*interval)`, kg/(m2 s) |
| Adsorption coverage state solved on wall | Surface coverage | Use actual state and unit, often dimensionless |
| Face hit counts only | Computational parcel-hit count or count/area | Say parcels, not physical particles |
| Final near-wall fluid concentration only | Near-wall fluid concentration | Say kg/m3, not adsorption/deposited mass |

For moving walls, choose and state material-face versus spatial-frame association, face area basis, and time interval. If remeshing changes IDs, use a verified mapping; static face IDs alone are insufficient. Preserve restart event/counter continuity. Do not reconstruct full-run cumulative capture from a counter that restarted at zero unless earlier contributions exist.

Use actual surface triangles, not a visually added bridge. Render a surface map plus subdued surrounding equipment and a separate scalar bar. Compare maps with fixed limits and the same visible wall/camera. Mark uncovered/missing faces, retain true zero values, and exclude unavailable faces from statistics rather than converting them to zero.

## Source mechanisms and language

Parameterize source type: surface flux, volumetric feed, injected particle distribution, gas inlet, or reaction-generated particles. Annotate the implemented source, even if a different mechanism would be more physically detailed. Keep figure work separate from a request to improve the model. English manuscript labels and a Chinese explanation to the user can coexist.
