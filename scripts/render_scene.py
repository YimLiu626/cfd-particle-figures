"""Generic, read-only-input CFD field / particle / wall figure renderer.

See references/data-contract.md. No native solver file assumptions.
"""
import argparse
import hashlib
import itertools
import json
import math
import re
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.ticker import FormatStrFormatter
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

from figure_tools import fill_display_gaps, isosurface, track_segments


def require(condition, message):
    if not condition:
        raise ValueError(message)


def match_time(times, value):
    found = np.flatnonzero(np.isclose(times, value, atol=1e-7, rtol=0))
    require(len(found) == 1, f'Exact saved time unavailable or ambiguous: {value}')
    return int(found[0])


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def scale_for(spec, values, fluid=None):
    samples = values[np.isfinite(values) & fluid] if fluid is not None else values[np.isfinite(values)]
    require(samples.size > 0, f'No valid observations for {spec["id"]}')
    lo, hi = float(samples.min()), float(samples.max())
    change = spec.get('mode', 'absolute') == 'change'
    positive = spec.get('positive_surfaces_only', False)
    if 'limits' in spec:
        limits = list(map(float, spec['limits']))
    elif change:
        bound = max(abs(lo), abs(hi), 1e-12)
        limits = [-bound, bound]
    else:
        limits = [min(lo, 0.), max(hi, 1e-12)] if positive else [lo, hi]
        if limits[0] == limits[1]:
            pad = max(abs(lo)*0.01, 1e-12)
            limits = [lo-pad, hi+pad]
    require(len(limits) == 2 and np.isfinite(limits).all() and limits[0] < limits[1], 'Invalid fixed scalar limits')
    if change:
        require(limits[0] < 0 < limits[1], 'Change scale must span zero')
        norm = TwoSlopeNorm(vmin=limits[0], vcenter=0, vmax=limits[1])
        defaults = np.r_[limits[0]*np.array([.75, .25, .04]), limits[1]*np.array([.04, .25, .75])]
    else:
        norm = Normalize(*limits)
        defaults = (limits[1]*np.array([.04, .12, .35, .65]) if positive
                    else np.linspace(*limits, 6)[1:-1])
    levels = np.asarray(spec.get('levels', defaults), float)
    require(levels.ndim == 1 and len(levels) > 0 and np.isfinite(levels).all(), 'Invalid isosurface levels')
    require(np.all((levels >= limits[0]) & (levels <= limits[1])), 'Levels outside color limits')
    if positive:
        levels = levels[levels > 0]
    alpha = np.broadcast_to(np.asarray(spec.get('opacity', .16), float), levels.shape)
    require(np.isfinite(alpha).all() and np.all((alpha >= 0) & (alpha <= 1)), 'Invalid opacity')
    cmap = plt.colormaps[spec.get('cmap', 'RdBu_r' if change else 'YlOrBr')]
    report = {'observed_min': lo, 'observed_max': hi, 'limits': limits, 'levels': levels.tolist(),
              'opacity': alpha.tolist(), 'negative_observations': int(np.count_nonzero(samples < 0)),
              'asymmetric_zero_scale': bool(change and not math.isclose(-limits[0], limits[1], rel_tol=1e-7)),
              'outside_legend_range': int(np.count_nonzero((samples < limits[0]) | (samples > limits[1])))}
    return norm, cmap, levels, alpha, report


def load_scene(config_path):
    cfg = json.loads(config_path.read_text(encoding='utf-8-sig'))
    root = config_path.parent
    require(bool(cfg.get('provenance')) and not cfg['provenance'].startswith('Replace with'), 'Supply actual data provenance')
    data_path = (root/cfg['data']).resolve()
    with np.load(data_path, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    axes = [np.asarray(data[k], float) for k in ('x_m', 'y_m', 'z_m')]
    for axis in axes:
        require(axis.ndim == 1 and len(axis) >= 2 and np.isfinite(axis).all() and np.all(np.diff(axis) > 0), 'Invalid display grid centres')
        require(np.allclose(np.diff(axis), axis[1]-axis[0], rtol=1e-5, atol=1e-10), 'Uniform display grid required')
    times = np.asarray(data['field_times_s'], float)
    require(times.ndim == 1 and len(times) and np.isfinite(times).all() and np.all(np.diff(times) > 0), 'Invalid field times')
    shape = (len(times), *(len(a) for a in axes))
    fluid = np.asarray(data['fluid_mask'], bool)
    require(fluid.shape in (shape, shape[1:]), 'Invalid fluid mask shape')
    fluid = np.broadcast_to(fluid, shape)
    bounds = np.asarray(cfg['bounds'], float)
    require(bounds.shape == (3, 2) and np.isfinite(bounds).all() and np.all(bounds[:, 1] > bounds[:, 0]), 'Invalid physical bounds')
    require(all(bounds[k, 0] <= a[0] and a[-1] <= bounds[k, 1] for k, a in enumerate(axes)), 'Grid outside scene bounds')
    require(bool(cfg.get('stages')), 'At least one stage required')
    field_specs, wall_specs = cfg.get('fields', []), cfg.get('wall_maps', [])
    require(bool(field_specs or wall_specs), 'At least one field or wall map required')
    ids = [s['id'] for s in field_specs+wall_specs]
    require(len(set(ids)) == len(ids) and all(re.fullmatch(r'[a-zA-Z0-9_-]+', i) for i in ids), 'Unique filename-safe quantity IDs required')
    for s in field_specs+wall_specs:
        require(all(s.get(k) for k in ('label', 'units', 'quantity_basis')), 'Supply quantity label, units and basis')
    for s in field_specs:
        a = np.asarray(data[s['key']], float)
        require(a.shape == shape and not np.isinf(a).any(), f'Invalid field {s["id"]}')
        require(s.get('mode', 'absolute') in ('absolute', 'change'), 'Unknown field mode')
        if s.get('mode') == 'change':
            require(('reference' in s) != ('reference_key' in s), 'Supply exactly one change-field reference')
            reference = np.asarray(data[s['reference_key']], float) if 'reference_key' in s else np.asarray(s['reference'], float)
            require(reference.shape in ((), shape[1:]) and not np.isinf(reference).any(), 'Invalid reference field')
            a = a-reference
        s['_values'] = a
    particles = 'tracks_m' in data
    if particles:
        pt = np.asarray(data['particle_times_s'], float)
        tr = data['tracks_m']
        require(pt.ndim == 1 and len(pt) and np.isfinite(pt).all() and np.all(np.diff(pt) > 0), 'Invalid particle times')
        require(tr.ndim == 3 and tr.shape[1:] == (len(pt), 3) and not np.isinf(tr).any(), 'Invalid track shape/values')
        finite = np.isfinite(tr).sum(axis=2)
        require(np.all((finite == 0) | (finite == 3)), 'Missing xyz observations must be wholly NaN')
        ids_array = data['particle_ids']
        require(ids_array.shape == (len(tr),) and len(np.unique(ids_array)) == len(tr), 'Unique stable particle IDs required')
        require(float(cfg.get('max_path_gap_s', 0)) > 0, 'Set max_path_gap_s explicitly')
    for stage in cfg['stages']:
        stage['_frame'] = match_time(times, stage['field_time_s'])
        require(bool(stage.get('label')), 'Stage label required')
        if 'birth_window_s' in stage:
            require(particles and 'birth_positions_m' in data and 'birth_times_s' in data, 'Birth stage needs recorded birth data')
            require(data['birth_positions_m'].shape == (len(tr), 3) and data['birth_times_s'].shape == (len(tr),), 'Birth metadata shape mismatch')
            require(np.isfinite(data['birth_positions_m']).all() and np.isfinite(data['birth_times_s']).all(), 'Birth metadata must be finite')
            require(len(stage['birth_window_s']) == 2 and stage['birth_window_s'][0] <= stage['birth_window_s'][1] <= stage['field_time_s'], 'Invalid birth window')
        elif particles:
            stage['_particle_frame'] = match_time(pt, stage['particle_time_s'])
    for mesh in cfg.get('meshes', [])+wall_specs:
        vertices = data[mesh['vertices_key']]
        faces = data[mesh['faces_key']]
        require(vertices.ndim in (2, 3) and vertices.shape[-1] == 3 and np.isfinite(vertices).all(), 'Invalid mesh vertices')
        require(vertices.ndim == 2 or vertices.shape[0] == len(times), 'Moving mesh not aligned with field times')
        require(faces.ndim == 2 and faces.shape[1] == 3 and np.issubdtype(faces.dtype, np.integer), 'Triangular integer faces required')
        require(faces.size > 0 and faces.min() >= 0 and faces.max() < vertices.shape[-2], 'Invalid face indices')
        require(not mesh.get('display_only') or bool(mesh.get('disclosure')), 'Disclose display-only connectors')
    for wall in wall_specs:
        a = np.asarray(data[wall['key']], float)
        require(a.shape == (len(times), len(data[wall['faces_key']])) and not np.isinf(a).any(), 'Invalid wall scalar association')
        require(not wall.get('display_only'), 'Wall values cannot use display-only geometry')
        wall['_values'] = a
    spacing = [float(a[1]-a[0]) for a in axes]
    return cfg, data, data_path, axes, fluid, spacing


def wire_box(bounds):
    corners = np.asarray(list(itertools.product(*bounds)))
    segments = []
    for i, p in enumerate(corners):
        for q in corners[i+1:]:
            if np.count_nonzero(p != q) == 1:
                segments.append([p, q])
    return segments


def vertices_at(data, spec, frame):
    vertices = data[spec['vertices_key']]
    return vertices[frame] if vertices.ndim == 3 else vertices


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    config_path = args.scene.resolve()
    cfg, data, data_path, axes, fluid, spacing = load_scene(config_path)
    clean_cfg = json.loads(config_path.read_text(encoding='utf-8-sig'))
    specs = cfg.get('fields', [])+cfg.get('wall_maps', [])
    selected = sorted({s['_frame'] for s in cfg['stages']})
    scales = {s['id']: scale_for(s, s['_values'][selected], fluid[selected] if s in cfg.get('fields', []) else None) for s in specs}
    if args.validate_only:
        print(json.dumps({'valid': True, 'stages': len(cfg['stages']), 'quantities': list(scales), 'particles': len(data.get('tracks_m', []))}))
        return
    output = (config_path.parent/cfg['output']).resolve()
    if args.preview:
        output = output/'preview'
    skill_dir = Path(__file__).resolve().parents[1]
    require(output != skill_dir and skill_dir not in output.parents, 'Output must be outside reusable skill')
    require(output != data_path.parent or output.name not in ('assets', 'scripts', 'references'), 'Choose a project figure directory')
    stages = cfg['stages'][:1] if args.preview else cfg['stages']
    export = cfg.get('export', {})
    formats = ['png'] if args.preview else export.get('formats', ['png', 'tif', 'svg', 'pdf'])
    require(formats and set(formats) <= {'png', 'tif', 'svg', 'pdf'}, 'Unsupported export format')
    dpi = 120 if args.preview else int(export.get('dpi', 600))
    require(dpi > 0, 'DPI must be positive')
    overview = not args.preview and export.get('overview', True)
    multi = not args.preview and export.get('multipage_pdf', True) and 'pdf' in formats
    names = [f'stage_{i+1:02d}' for i in range(len(stages))]
    if overview:
        names.extend('overview_'+s['id'] for s in specs)
    expected = [output/(n+'.'+ext) for n in names for ext in formats]
    expected += [output/'figure_manifest.json', output/'figure_caption.md']
    if multi:
        expected.append(output/'figures.pdf')
    require(not any(p.exists() for p in expected), 'Generated outputs already exist; choose a fresh output directory')
    require(not any(p.resolve() in (data_path, config_path) for p in expected), 'Output overlaps input')
    output.mkdir(parents=True, exist_ok=True)
    style = cfg.get('style', {})
    font = style.get('font', 'Arial')
    try:
        font_manager.findfont(font, fallback_to_default=False)
    except ValueError:
        font = 'DejaVu Sans'
    plt.rcParams.update({'font.family': font, 'font.size': style.get('font_pt', 8),
                         'svg.fonttype': 'none', 'pdf.fonttype': 42, 'figure.facecolor': 'white', 'savefig.facecolor': 'white'})
    manifest = {'configuration': clean_cfg, 'inputs': [], 'scales': {k: v[4] for k, v in scales.items()},
                'font_used': font, 'panels': [], 'outputs': [], 'warnings': [], 'preview': args.preview}
    for path in [config_path, data_path]+[(config_path.parent/p).resolve() for p in cfg.get('provenance_files', [])]:
        manifest['inputs'].append({'path': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size})
    if cfg.get('gap_fill_m', 0) > 0:
        manifest['warnings'].append('Bounded nearest-neighbour display extrapolation within connected fluid components; inspect thin internal walls.')
    for s in specs:
        if scales[s['id']][4]['asymmetric_zero_scale']:
            manifest['warnings'].append(s['id']+': asymmetric zero-centered color scale; unequal slopes either side of zero.')
        if scales[s['id']][4]['outside_legend_range']:
            manifest['warnings'].append(s['id']+': some observations lie outside the displayed legend range.')
    for mesh in cfg.get('meshes', []):
        if mesh.get('display_only'):
            manifest['warnings'].append(mesh['disclosure'])
    manifest['warnings'].append('Matplotlib transparent polygon depth ordering is approximate; inspect occlusion. Paths are sampled observations, not continuous integrations.')
    cache = {}
    path_norm = None
    if 'tracks_m' in data:
        limits = style.get('path_limits_s', [float(data['particle_times_s'][0]), float(data['particle_times_s'][-1])])
        require(len(limits) == 2 and np.isfinite(limits).all() and limits[0] < limits[1], 'Invalid path-time limits')
        path_norm = Normalize(*limits)
        path_cmap = plt.colormaps[style.get('path_cmap', 'viridis')]
        if 'birth_times_s' in data:
            require(np.min(data['birth_times_s']) >= limits[0] and np.max(data['birth_times_s']) <= limits[1], 'Path-time legend must include birth times')

    def base(ax, stage, current_spec):
        frame = stage['_frame']
        wall_geometry = {(w['vertices_key'], w['faces_key']) for w in cfg.get('wall_maps', []) if w is current_spec}
        for mesh in cfg.get('meshes', []):
            if (mesh['vertices_key'], mesh['faces_key']) not in wall_geometry:
                tris = vertices_at(data, mesh, frame)[data[mesh['faces_key']]]
                ax.add_collection3d(Poly3DCollection(tris, facecolor=mesh.get('color', '#A8ADB3'), edgecolor='none', alpha=mesh.get('alpha', .35), linewidth=0))
            if mesh.get('outline_key'):
                p = data[mesh['outline_key']]
                if p.ndim == 3:
                    p = p[frame]
                ax.plot(*p.T, color='#637080', lw=.5)
        ax.add_collection3d(Line3DCollection(wire_box(cfg['bounds']), colors='#8AA3BB', linewidths=.4, alpha=.6))
        for source in cfg.get('sources', []):
            color = source.get('color', '#C65D00')
            if 'bounds' in source:
                ax.add_collection3d(Line3DCollection(wire_box(source['bounds']), colors=color, linestyles=source.get('linestyle', '--'), linewidths=.65))
                p = np.asarray(source['bounds'])[:, 1]
            else:
                points = np.asarray(source['points'])
                ax.plot(*points.T, color=color, lw=.65, ls=source.get('linestyle', '-'))
                p = points[-1]
            ax.text(*p, source['label'], fontsize=6, color=color)
        if path_norm is not None:
            if 'birth_window_s' in stage:
                lo, hi = stage['birth_window_s']
                good = (data['birth_times_s'] >= lo) & (data['birth_times_s'] <= hi)
                p = data['birth_positions_m'][good]
                ax.scatter(*p.T, c=data['birth_times_s'][good], cmap=path_cmap, norm=path_norm, s=8, edgecolors='#293440', linewidths=.25, depthshade=False)
                particle_count = int(good.sum())
            else:
                end = stage['particle_time_s']
                seg, colors = track_segments(data['tracks_m'], data['particle_times_s'], end, cfg['max_path_gap_s'])
                if len(seg):
                    line = Line3DCollection(seg, cmap=path_cmap, norm=path_norm, linewidths=.75, alpha=.9)
                    line.set_array(colors)
                    ax.add_collection3d(line)
                p = data['tracks_m'][:, stage['_particle_frame']]
                p = p[np.isfinite(p).all(axis=1)]
                ax.scatter(*p.T, color=path_cmap(path_norm(end)), s=9, edgecolors='#293440', linewidths=.25, depthshade=False)
                particle_count = len(p)
            ax.text2D(.02, .015, f'Observed parcels: {particle_count}', transform=ax.transAxes, fontsize=6)
        else:
            particle_count = 0
        for setter, b in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), cfg['bounds']):
            setter(b)
        ax.set_box_aspect(np.diff(np.asarray(cfg['bounds']), axis=1).ravel())
        ax.view_init(*style.get('camera', [23, -60, 0]))
        ax.set_axis_off()
        return particle_count

    def panel(fig, ax, stage, spec, label):
        count = base(ax, stage, spec)
        frame = stage['_frame']
        norm, cmap, levels, alpha, _ = scales[spec['id']]
        key = (spec['id'], frame)
        if spec in cfg.get('fields', []):
            if key not in cache:
                values, filled = fill_display_gaps(spec['_values'][frame], fluid[frame], spacing, cfg.get('gap_fill_m', 0))
                layers = [(isosurface(values, fluid[frame], axes, level), level, a) for level, a in zip(levels, alpha)]
                cache[key] = layers, filled
            layers, filled = cache[key]
            n = 0
            for tris, level, a in layers:
                if len(tris):
                    ax.add_collection3d(Poly3DCollection(tris, facecolor=cmap(norm(level)), alpha=float(a), edgecolor='none', linewidth=0))
                    n += 1
            if not n:
                ax.text2D(.5, .45, 'No surface at selected levels', ha='center', transform=ax.transAxes, fontsize=6)
            entry = {'layers': n, 'filled_voxels': filled}
        else:
            values = spec['_values'][frame]
            valid = np.isfinite(values)
            tris = vertices_at(data, spec, frame)[data[spec['faces_key']]][valid]
            ax.add_collection3d(Poly3DCollection(tris, facecolors=cmap(norm(values[valid])), edgecolor='none', linewidth=0))
            entry = {'observed_wall_faces': int(valid.sum()), 'missing_wall_faces': int((~valid).sum())}
        ax.text2D(.02, .97, label, transform=ax.transAxes, fontsize=7, va='top')
        cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax, orientation='horizontal', fraction=.045, pad=.01, shrink=.8)
        cb.set_label(spec['label']+' ('+spec['units']+')', fontsize=7)
        if isinstance(norm, TwoSlopeNorm):
            # Automatic locators can omit a very small positive range on an
            # asymmetric change scale. Show both sides explicitly.
            cb.set_ticks([norm.vmin, norm.vmin/2, 0, norm.vmax/2, norm.vmax])
            cb.formatter = FormatStrFormatter('%.3g')
            cb.update_ticks()
        cb.ax.tick_params(labelsize=6, length=2)
        cb.ax.xaxis.get_offset_text().set_fontsize(6)
        manifest['panels'].append({'quantity': spec['id'], 'stage': stage['label'], 'field_time_s': stage['field_time_s'], 'observed_parcels': count, **entry})

    def timebar(fig):
        if path_norm is not None:
            cb = fig.colorbar(ScalarMappable(norm=path_norm, cmap=path_cmap), cax=fig.add_axes([.34, .045, .32, .014]), orientation='horizontal')
            cb.set_label('Particle path / birth time (s)', fontsize=7)
            cb.ax.tick_params(labelsize=6, length=2)

    pdf = PdfPages(output/'figures.pdf') if multi else None
    def save(fig, stem):
        for ext in formats:
            path = output/(stem+'.'+ext)
            kwargs = {'dpi': dpi}
            if ext == 'tif':
                kwargs['pil_kwargs'] = {'compression': 'tiff_lzw'}
            fig.savefig(path, **kwargs)
            manifest['outputs'].append(path.name)
        if pdf is not None:
            pdf.savefig(fig)
        plt.close(fig)

    width, height = style.get('width_mm', 180)/25.4, style.get('height_mm', 105)/25.4
    try:
        for i, stage in enumerate(stages):
            fig = plt.figure(figsize=(width, height))
            gs = fig.add_gridspec(1, len(specs), left=.015, right=.985, bottom=.22, top=.90, wspace=.10)
            for j, spec in enumerate(specs):
                panel(fig, fig.add_subplot(gs[0, j], projection='3d'), stage, spec, f'({chr(97+j)})')
            subtitle = f'Field at {stage["field_time_s"]:g} s'
            if 'birth_window_s' in stage:
                subtitle += f'; births during {stage["birth_window_s"][0]:g}–{stage["birth_window_s"][1]:g} s'
            elif 'particle_time_s' in stage:
                subtitle += f'; particles at {stage["particle_time_s"]:g} s'
            fig.text(.5, .975, stage['label'], ha='center', va='top', fontsize=8)
            fig.text(.5, .93, subtitle, ha='center', va='top', fontsize=7)
            timebar(fig)
            save(fig, f'stage_{i+1:02d}')
        if overview:
            cols = int(style.get('overview_columns', 4))
            require(cols > 0, 'Invalid overview column count')
            cols = min(cols, len(stages))
            rows = math.ceil(len(stages)/cols)
            for spec in specs:
                fig = plt.figure(figsize=(width, max(height, rows*1.5)))
                gs = fig.add_gridspec(rows, cols, left=.01, right=.99, bottom=.16, top=.98, wspace=.12, hspace=.3)
                for i, stage in enumerate(stages):
                    panel(fig, fig.add_subplot(gs[i//cols, i%cols], projection='3d'), stage, spec, f'({chr(97+i)}) '+stage['label'])
                timebar(fig)
                save(fig, 'overview_'+spec['id'])
    finally:
        if pdf is not None:
            pdf.close()
    if multi:
        manifest['outputs'].append('figures.pdf')
    caption = ['# Figure caption and provenance', '', cfg['provenance'], '',
               'Three-dimensional saved fields and sampled particle observations are shown with a fixed camera and fixed scalar scales over the configured comparison set. Paths connect consecutive available observations only; missing data and excessive time gaps are not bridged. Birth-window panels use recorded birth locations with explicitly labeled field timestamps. No synthetic simulation states are generated.', '',
               'Scalar definitions:']
    caption += [f'- {s["label"]}: {s["quantity_basis"]}; units {s["units"]}; scale and reference in figure_manifest.json.' for s in specs]
    caption += ['', 'Display processing: uniform grid spacing '+str(spacing)+' m; optional filling distance '+str(cfg.get('gap_fill_m', 0))+' m; linear marching cubes without smoothing. Signed input arrays are preserved. Positive-only surfaces and numerical undershoots are recorded in the manifest.', '', 'Limitations and display disclosures:']
    caption += ['- '+warning for warning in manifest['warnings']]
    caption += ['', f'Exports: {dpi} dpi raster; editable SVG text where requested; font {font}. Verify requested journal production specifications separately.']
    (output/'figure_caption.md').write_text('\n'.join(caption)+'\n', encoding='utf-8')
    (output/'figure_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'output': str(output), 'figures': len(manifest['outputs']), 'panels': len(manifest['panels'])}))


if __name__ == '__main__':
    main()
