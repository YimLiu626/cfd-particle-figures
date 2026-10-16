"""Small, data-preserving building blocks for CFD figure adapters."""
import numpy as np
from scipy.ndimage import distance_transform_edt, label
from skimage.measure import marching_cubes


def volume_weighted_grid(points, volumes, values, edges):
    """Centroid binning; returns mean concentration and sampled fluid volume."""
    p, v, c = (np.asarray(x, dtype=float) for x in (points, volumes, values))
    if p.ndim != 2 or p.shape[1] != 3 or v.shape != (len(p),) or c.shape != v.shape:
        raise ValueError('Expected points (N,3), positive volumes (N,), values (N,)')
    if not (np.isfinite(p).all() and np.isfinite(v).all() and np.isfinite(c).all()) or np.any(v <= 0):
        raise ValueError('Cell inputs must be finite, with strictly positive volume')
    if len(edges) != 3 or any(np.any(np.diff(e) <= 0) for e in edges):
        raise ValueError('Three increasing bin-edge arrays required')
    if any(np.any((p[:, k] < e[0]) | (p[:, k] > e[-1])) for k, e in enumerate(edges)):
        raise ValueError('Cells outside display grid: expand bounds or explicitly account for exclusions')
    sampled, _ = np.histogramdd(p, bins=edges, weights=v)
    mass, _ = np.histogramdd(p, bins=edges, weights=v*c)
    mean = np.full(sampled.shape, np.nan)
    np.divide(mass, sampled, out=mean, where=sampled > 0)
    if not np.isclose(np.sum(mass), np.sum(v*c), rtol=1e-10, atol=1e-10):
        raise ValueError('Display aggregation failed signed mass consistency')
    return mean, sampled


def track_segments(tracks, times, until, max_gap):
    """Never connect across a missing observation or an excessive time gap."""
    tracks, times = np.asarray(tracks, float), np.asarray(times, float)
    if tracks.ndim != 3 or tracks.shape[1:] != (len(times), 3):
        raise ValueError('Expected tracks (N,T,3) aligned with times')
    if not np.isfinite(times).all() or np.any(np.diff(times) <= 0) or max_gap <= 0:
        raise ValueError('Increasing finite times and positive max_gap required')
    selected = times <= until + 1e-8
    ok = (np.isfinite(tracks[:, :-1]).all(axis=2)
          & np.isfinite(tracks[:, 1:]).all(axis=2)
          & selected[:-1] & selected[1:]
          & (np.diff(times) <= max_gap + 1e-8))
    pair = np.stack([tracks[:, :-1], tracks[:, 1:]], axis=2)
    mid = np.broadcast_to((times[:-1]+times[1:])/2, ok.shape)
    return pair[ok], mid[ok]


def ribbon_faces(centerline, width, width_axis=(0, 1, 0)):
    """Planar-width display ribbon; no CFD geometry or fields are changed."""
    path = np.asarray(centerline, float)
    axis = np.asarray(width_axis, float)
    if path.ndim != 2 or path.shape[1] != 3 or len(path) < 2 or width <= 0:
        raise ValueError('Finite centerline (N>=2,3) and positive width required')
    if not np.isfinite(path).all() or not np.isfinite(axis).all() or axis.shape != (3,) or np.linalg.norm(axis) == 0:
        raise ValueError('Invalid centerline or width axis')
    axis = axis / np.linalg.norm(axis)
    if np.any(np.abs(np.diff(path, axis=0) @ axis) > 1e-7):
        raise ValueError('Centerline must be perpendicular to this fixed width axis')
    near, far = path-axis*width/2, path+axis*width/2
    vertices = np.vstack([near, far])
    n = len(path)
    faces = []
    for k in range(n-1):
        faces.extend([[k, k+1, n+k+1], [k, n+k+1, n+k]])
    outline = np.vstack([near, far[::-1], near[:1]])
    return vertices, np.asarray(faces, dtype=int), outline


def fill_display_gaps(values, fluid_mask, spacing, max_distance_m=0):
    """Optional bounded fill, separately within each connected fluid component."""
    field = np.asarray(values, float).copy()
    fluid = np.asarray(fluid_mask, bool)
    if field.shape != fluid.shape or max_distance_m < 0:
        raise ValueError('Field/mask shapes or fill distance invalid')
    if max_distance_m == 0:
        return field, 0
    components, n = label(fluid)
    count = 0
    for k in range(1, n+1):
        component = components == k
        observed = component & np.isfinite(field)
        if not observed.any():
            continue
        distance, nearest = distance_transform_edt(~observed, sampling=spacing, return_indices=True)
        fill = component & ~np.isfinite(field) & (distance <= max_distance_m)
        field[fill] = field[tuple(nearest[:, fill])]
        count += int(fill.sum())
    return field, count


def isosurface(values, fluid_mask, axes, level):
    """Triangular isosurface, excluding invalid interpolation stencils."""
    a = np.asarray(values, float)
    valid = np.asarray(fluid_mask, bool) & np.isfinite(a)
    if not valid.any() or not (a[valid].min() < level < a[valid].max()):
        return np.empty((0, 3, 3))
    # Invalid fill is only a numerical argument to marching cubes. Any vertex
    # whose eight-point interpolation stencil includes an invalid cell is removed.
    work = np.where(valid, a, float(level))
    try:
        vertices, faces, _, _ = marching_cubes(work, level=float(level), mask=valid, allow_degenerate=False)
    except RuntimeError as exc:
        if 'No surface found' in str(exc):
            return np.empty((0, 3, 3))
        raise
    low = np.floor(vertices).astype(int)
    low = np.clip(low, 0, np.asarray(a.shape)-2)
    supported = np.ones(len(vertices), dtype=bool)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                supported &= valid[low[:, 0]+dx, low[:, 1]+dy, low[:, 2]+dz]
    faces = faces[supported[faces].all(axis=1)]
    xyz = np.column_stack([np.interp(vertices[:, k], np.arange(len(axis)), axis) for k, axis in enumerate(axes)])
    return xyz[faces]
