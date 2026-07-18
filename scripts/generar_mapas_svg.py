# -*- coding: utf-8 -*-
"""
Genera paths SVG pre-proyectados (Mercator) para el simulador fiscal, a partir
de los GeoJSON oficiales, con UNA sola proyección compartida para que el mapa
municipal y el departamental queden perfectamente alineados.

Salidas (viewBox 1000 x 1132, igual que el escenario_it original):
  data/mapa_muni.json  -> {w,h,paths:{ sigep -> "d" }}     (335 municipios + GAIOC)
  data/mapa_dep.json   -> {w,h,paths:{ DPTO_UPPER -> "d" }} (9 departamentos)

Fuentes GeoJSON (repo madre "Observatorio de Presupuesto Fiscal Departamental"):
  municipal:      data/municipios_sim.geojson (ya en este repo, props.s = sigep)
  departamental:  gobernaciones/_datos/_bolivia_deptos_simple.geojson (props.nombre, cod_dep)
"""
import json, os, math
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROY = os.path.dirname(ROOT)
MUNI_GJ = os.path.join(ROOT, 'data', 'municipios_sim.geojson')
DEP_GJ = os.path.join(PROY, 'Observatorio de Presupuesto Fiscal Departamental',
                      'gobernaciones', '_datos', '_bolivia_deptos_simple.geojson')

W, H = 1000, 1132
PAD = 12  # margen en px

# Simplificación en grados antes de proyectar (Douglas-Peucker de shapely)
TOL_MUNI = 0.005
TOL_DEP = 0.02


def norm_dep(nom):
    """Clave canónica de departamento: mayúsculas sin tildes (POTOSI, no POTOSÍ),
    igual que en los datos del escenario (_scenario_gob.json / ent 'd')."""
    s = nom.upper().strip()
    for a, b in (('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'), ('Ú', 'U')):
        s = s.replace(a, b)
    return s


def mercator(lon, lat):
    x = math.radians(lon)
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def bounds_all(features):
    minx = miny = 1e9
    maxx = maxy = -1e9
    for ft in features:
        g = shape(ft['geometry'])
        x0, y0, x1, y1 = g.bounds
        # bounds are in lon/lat; project the 4 corners is wrong for extent,
        # instead track lon/lat extent and project extremes
        minx = min(minx, x0); maxx = max(maxx, x1)
        miny = min(miny, y0); maxy = max(maxy, y1)
    return minx, miny, maxx, maxy


def make_projector(lon0, lat0, lon1, lat1):
    # proyecta las esquinas del bbox a Mercator para hallar la escala/offset
    mx0, my0 = mercator(lon0, lat0)
    mx1, my1 = mercator(lon1, lat1)
    mw, mh = (mx1 - mx0), (my1 - my0)
    avail_w, avail_h = W - 2 * PAD, H - 2 * PAD
    scale = min(avail_w / mw, avail_h / mh)
    # centrado
    off_x = PAD + (avail_w - mw * scale) / 2
    off_y = PAD + (avail_h - mh * scale) / 2

    def proj(lon, lat):
        mx, my = mercator(lon, lat)
        px = off_x + (mx - mx0) * scale
        py = off_y + (my1 - my) * scale  # invertir Y (norte arriba)
        return round(px, 1), round(py, 1)

    return proj


def ring_to_path(coords, proj):
    pts = []
    last = None
    for lon, lat in coords:
        p = proj(lon, lat)
        if p != last:  # dedup consecutivos tras redondeo
            pts.append(p)
            last = p
    if len(pts) < 3:
        return ''
    d = 'M' + ' '.join(f'{x} {y}' for x, y in pts) + 'Z'
    return d


def geom_to_path(geom, proj):
    parts = []
    gt = geom['type']
    if gt == 'Polygon':
        polys = [geom['coordinates']]
    elif gt == 'MultiPolygon':
        polys = geom['coordinates']
    else:
        return ''
    for poly in polys:
        for ring in poly:  # ring[0] exterior + huecos; dibujamos todos (evenodd)
            d = ring_to_path(ring, proj)
            if d:
                parts.append(d)
    return ' '.join(parts)


def main():
    muni = load(MUNI_GJ)
    dep = load(DEP_GJ)

    # proyección global desde el bbox municipal (cubre todo el país)
    lon0, lat0, lon1, lat1 = bounds_all(muni['features'])
    proj = make_projector(lon0, lat0, lon1, lat1)

    # --- municipal ---
    mpaths = {}
    for ft in muni['features']:
        sig = str(ft['properties'].get('s') or ft['properties'].get('sigep') or '')
        g = shape(ft['geometry']).simplify(TOL_MUNI, preserve_topology=True)
        d = geom_to_path(json.loads(json.dumps(g.__geo_interface__)), proj)
        if sig and d:
            mpaths[sig] = d
    with open(os.path.join(ROOT, 'data', 'mapa_muni.json'), 'w', encoding='utf-8') as f:
        json.dump({'w': W, 'h': H, 'paths': mpaths}, f, ensure_ascii=False, separators=(',', ':'))

    # --- departamental: DISUELTO desde el municipal (coherente y alineado al mapa municipal).
    #     Se toman anillos exteriores (rellena lagos internos). El Salar de Uyuni no lo cubre
    #     ningún municipio y toca el borde Potosí-Oruro, así que a nivel departamental queda un
    #     hueco; se cubre con una SILUETA NACIONAL de base (a nivel país el Salar es un hueco
    #     cerrado -> exterior-only lo rellena). ---
    by_dep = {}
    for ft in muni['features']:
        d = norm_dep(ft['properties'].get('d') or ft['properties'].get('dpto') or '')
        if d:
            by_dep.setdefault(d, []).append(shape(ft['geometry']))
    dpaths = {}
    dep_geoms = []
    for nom, geoms in by_dep.items():
        merged = unary_union([g.buffer(0.008) for g in geoms]).buffer(-0.006)
        merged = merged.simplify(TOL_DEP, preserve_topology=True)
        dep_geoms.append(merged)
        polys = [merged] if merged.geom_type == 'Polygon' else list(merged.geoms)
        polys = [p for p in polys if p.area > 0.005]
        parts = [ring_to_path(list(p.exterior.coords), proj) for p in polys]
        pth = ' '.join(p for p in parts if p)
        if pth:
            dpaths[nom] = pth
    # silueta nacional: rellena el Salar y cualquier grieta inter-departamental
    nac = unary_union([g.buffer(0.03) for g in dep_geoms]).buffer(-0.03).simplify(TOL_DEP, preserve_topology=True)
    npolys = [nac] if nac.geom_type == 'Polygon' else list(nac.geoms)
    npolys = [p for p in npolys if p.area > 0.01]
    dpaths['_NACIONAL'] = ' '.join(ring_to_path(list(p.exterior.coords), proj) for p in npolys)
    _ = dep
    with open(os.path.join(ROOT, 'data', 'mapa_dep.json'), 'w', encoding='utf-8') as f:
        json.dump({'w': W, 'h': H, 'paths': dpaths}, f, ensure_ascii=False, separators=(',', ':'))

    print(f'municipal: {len(mpaths)} paths -> data/mapa_muni.json '
          f'({os.path.getsize(os.path.join(ROOT, "data", "mapa_muni.json"))//1024} KB)')
    print(f'departamental: {len(dpaths)} paths -> data/mapa_dep.json '
          f'({os.path.getsize(os.path.join(ROOT, "data", "mapa_dep.json"))//1024} KB)')
    print('deptos:', list(dpaths.keys()))


if __name__ == '__main__':
    main()
