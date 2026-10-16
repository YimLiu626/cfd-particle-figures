# Portable scene contract

Use JSON configuration plus non-pickled NumPy NPZ arrays. All paths are relative to the JSON unless absolute. The renderer reads inputs and creates a new output directory. Adapt solver exports locally; the generic renderer does not know native Fluent HDF5 zone ordering, partition IDs, UDS meanings, or injection metadata.

## Configuration

Start from `assets/scene.example.json`. Required entries: `data`, `output`, `bounds` (three `[min,max]` pairs), `stages`, at least one `fields` entry, and `provenance` describing the simulation/extraction basis. Coordinate unit is metres and timestamps are physical seconds. `provenance_files` optionally lists existing extraction manifests/UDF summaries to hash. Do not include credentials or confidential account configuration.

Each stage has a `label`, `field_time_s` (must exist exactly in field times within numerical tolerance), and `particle_time_s` (must exist in particle times unless `birth_window_s` is provided). A birth stage has `birth_window_s: [start,end]`; its panel label is supplemented with both birth-window and field timestamps. Birth stages use true birth positions and birth times, not tracks collapsed to a point.

Each field has a unique ASCII `id`, `key` naming its NPZ array, `label`, `units`, `mode` (`absolute` or `change`), and `quantity_basis` describing how it was derived. For change fields, provide `reference` as a scalar or `reference_key` as a grid array. The renderer subtracts it once. If input already contains changes, use `reference: 0` and say so in the basis. Optional `limits`, `levels`, `opacity` (scalar or one per level), and `cmap` control fixed scales. `positive_surfaces_only` limits displayed isosurfaces, not source arrays. Automatic signed scales are symmetric; explicit asymmetric limits trigger a disclosure. Constant fields use a nonzero legend span and report no isosurface.

`sources` contains `label` plus either `bounds` or `points` (physical polyline). Coordinates must follow the actual source model. Optional `color` and `linestyle` only affect display. Sources do not move with camera rotation.

`meshes` contains actual surface vertices/faces keys, optional `label`, `color`, and `alpha`. Faces are triangular integer vertex indices. Internal edges are not drawn. Optional `outline_key` names a polyline with NaN-separated disconnected lines. `display_only: true` requires a `disclosure`; such geometry is never used by the field mask. Moving `vertices` can be `(F,V,3)` with constant topology and field frame count F; adapters with remeshing must adapt per-frame geometry separately.

Optional `wall_maps` adds a quantity column per wall map, with unique `id`, mesh `vertices_key`, `faces_key`, scalar `key`, `label`, `units`, and `quantity_basis`. Values are per triangular face `(F,Ntri)`; split original polygonal faces into triangles and copy the polygon's intensive value, or distribute an extensive value correctly. Fixed `limits`/`cmap` are optional. Scalar wall maps use actual geometry and are not drawn on illustrative connectors. Paths may be overlaid for context. Field and wall values get independent legends.

`style` includes camera `[elevation,azimuth,roll]`, `font`, `font_pt`, `path_cmap`, optional fixed `path_limits_s`, and figure width/height in millimetres. `overview_columns` defaults to 4. `export` includes `dpi`, `formats` (`png`,`tif`,`svg`,`pdf`), `overview` and `multipage_pdf`. With `pdf` selected, both individual vector PDFs and, when enabled, the multipage PDF are produced. Reusing an output folder with colliding generated names is refused; select another output directory to preserve prior work.

## NPZ arrays

| Key | Shape | Meaning |
| --- | --- | --- |
| `field_times_s` | `(F,)` | Strictly increasing saved physical times |
| `x_m`, `y_m`, `z_m` | `(Nx,)`, `(Ny,)`, `(Nz,)` | Increasing uniformly spaced display cell centres, at least 2 each |
| `fluid_mask` | `(Nx,Ny,Nz)` or `(F,Nx,Ny,Nz)` | True actual fluid; false solids/outside domain |
| scalar key | `(F,Nx,Ny,Nz)` | Signed original display values; NaN means missing fluid observations |
| reference key | `(Nx,Ny,Nz)` | Initial/reference field on the aligned display grid |
| `particle_times_s` | `(P,)` | Strictly increasing saved particle times |
| `tracks_m` | `(N,P,3)` | Same real cohort at each time; whole xyz row NaN if not observed |
| `particle_ids` | `(N,)` | Unique stable strings/integers after composite-ID construction |
| `birth_positions_m` | `(N,3)` | Optional true recorded birth coordinates |
| `birth_times_s` | `(N,)` | Optional true recorded birth times |
| mesh vertices key | `(V,3)` or `(F,V,3)` | Actual/display surface positions in metres |
| mesh faces key | `(Ntri,3)` | Integer triangular connectivity |
| wall scalar key | `(F,Ntri)` | Quantity on each triangle, correctly associated |

Particles are optional as a group; birth metadata is required only for birth stages. Do not set missing positions to zero. Per-field NaNs are retained; infinities are rejected. Zero precipitate is valid data, not missing data. Mesh/scalar association must be validated before entering the generic renderer.

The renderer connects only consecutive, fully finite saved positions with time difference no greater than `max_path_gap_s`. Set that explicitly to the expected particle save interval to prevent bridging removed snapshots. The contract distinguishes frames of the Eulerian field from independently sampled particle times. No temporal interpolation is done.

## Extraction and scientific checks

For concentration from cells, use `volume_weighted_grid` on `c=rho*Y` where that definition is established. It returns `sum(V*c)/sum(V)` and sampled cell-volume sums. Centroid binning is a display aggregation, not geometric intersection remapping. Report discarded/outside cells rather than silently losing mass; the helper refuses out-of-bounds inputs. Check `sum(c_cell*V_cell)` against `sum(c_grid*V_sampled)` before filling. Never use voxel geometric volume in place of sampled volume for this check.

For DPM, construct identities using run/restart/injection/rank/particle components as needed. Matching IDs across a restart is valid only if their meanings are consistent. A computational parcel may represent many physical particles. Physical number/mass density needs saved parcel weights and the specified averaging volume/time; raw parcel density is a separate quantity. For surface capture, preserve event time, face association, particle mass/weight, and restart continuity.

The renderer defaults to no gap filling. Optional `gap_fill_m` performs bounded nearest-neighbour display extrapolation inside each connected fluid component, records the count and method, and leaves input arrays untouched. Connectivity alone cannot guarantee a nearest point does not cross a thin internal wall in a connected vessel; verify the filled region against geometry, or leave filling off. Marching-cubes faces that use invalid interpolation stencils are removed. No smoothing is applied.

Outputs include `figure_manifest.json` (full configuration, SHA256, scale choices, observations, display warnings, stage layer/particle counts) and `figure_caption.md`. Supplement the generated caption with scientific context and verify it before publication.
