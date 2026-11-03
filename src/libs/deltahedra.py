"""
deltahedra.py -- i deltaedri come dati, puro numpy (niente bpy): coperto dai
test.

* load_welded(), load_stl(): un deltaedro da un OBJ o da un STL binario,
  coi vertici duplicati saldati.
* tetrahedron_chain(): il composto di tre tetraedri regolari in catena.
* orient_outward(), vertex_degrees(): orientamento delle facce e tipi di
  vertice.
* La platea di cundy_deltahedra: arrange() mette i modelli in file,
  frame_all() trova la camera che le inquadra.
"""

import glob
import math
import os
import struct

import numpy as np

import geometry


# =============================================================================
# I POLIEDRI
# =============================================================================

def load_welded(path):
    """(vertici, facce) del poliedro del file, coi vertici duplicati saldati
    (gli OBJ ripetono i vertici per faccia) e il baricentro dei vertici
    nell'origine."""
    md = geometry.read_obj(path)
    index, remap = {}, []
    for v in md.vertices:
        remap.append(index.setdefault(tuple(np.round(v, 5)), len(index)))
    V = np.asarray(list(index), dtype=float)
    faces = [[remap[i] for i in f] for f in md.faces]
    return V - V.mean(axis=0), faces


def load_stl(path):
    """(vertici, facce) del poliedro di un STL binario, coi vertici saldati
    (l'STL ripete i vertici per faccia) e il baricentro dei vertici
    nell'origine. Le coordinate restano quelle del file."""
    with open(path, "rb") as fp:
        data = fp.read()
    n = struct.unpack("<I", data[80:84])[0]
    if len(data) < 84 + 50 * n:
        raise ValueError(f"{path}: non e' un STL binario ({len(data)} byte per {n} triangoli)")
    rec = np.frombuffer(data[84:84 + 50 * n],
                        dtype=np.dtype([("normal", "<3f4"), ("v", "<9f4"), ("attr", "<u2")]))
    P = rec["v"].reshape(-1, 3).astype(float)
    index, remap = {}, []
    for v in P:
        remap.append(index.setdefault(tuple(np.round(v, 4)), len(index)))
    V = np.asarray(list(index), dtype=float)
    faces = [remap[3 * k:3 * k + 3] for k in range(n)]
    return V - V.mean(axis=0), faces


def tetrahedron_chain():
    """Tre tetraedri regolari di spigolo 1 in catena: il secondo incollato a
    una faccia del primo, il terzo a una faccia del secondo, senza tornare
    indietro. Ogni nuovo vertice e' il riflesso, attraverso la faccia in
    comune, del vertice opposto. Restituisce (vertici numpy, facce); le facce
    interne (bcd, cde) non ci sono."""
    def reflect(p, a, b, c):
        n = np.cross(b - a, c - a)
        n = n / np.linalg.norm(n)
        return p - 2.0 * np.dot(p - a, n) * n
    a = np.array([0.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    c = np.array([0.5, math.sqrt(3) / 2, 0.0])
    d = np.array([0.5, math.sqrt(3) / 6, math.sqrt(2.0 / 3.0)])
    e = reflect(a, b, c, d)
    f = reflect(b, c, d, e)
    V = np.array([a, b, c, d, e, f])
    faces = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 4), (1, 3, 4), (2, 3, 5), (2, 4, 5), (3, 4, 5)]
    return V, orient_outward(V, faces)


def orient_outward(V, faces):
    """Le facce con l'orientamento coerente e le normali verso l'esterno.

    Si propaga l'orientamento da faccia a faccia attraverso gli spigoli (due
    facce adiacenti percorrono lo spigolo in sensi opposti), poi si sceglie il
    verso col segno del volume: su un poliedro non convesso il confronto col
    baricentro non basta."""
    faces = [list(f) for f in faces]
    done, todo = {0}, [0]
    while todo:
        i = todo.pop()
        edges_i = {(faces[i][k], faces[i][(k + 1) % 3]) for k in range(3)}
        for j, g in enumerate(faces):
            if j in done:
                continue
            edges_j = {(g[k], g[(k + 1) % 3]) for k in range(3)}
            if not any(e in edges_j or (e[1], e[0]) in edges_j for e in edges_i):
                continue
            if any(e in edges_j for e in edges_i):       # stesso verso: va girata
                faces[j] = [g[0], g[2], g[1]]
            done.add(j)
            todo.append(j)
    volume = sum(np.dot(V[f[0]], np.cross(V[f[1]], V[f[2]])) for f in faces)
    if volume < 0:
        faces = [[f[0], f[2], f[1]] for f in faces]
    return faces


def vertex_degrees(n, faces):
    """Quanti triangoli concorrono in ognuno degli n vertici."""
    deg = [0] * n
    for f in faces:
        for i in f:
            deg[i] += 1
    return deg


def plane_section(V, faces, axis, value, weld=1e-6):
    """La sezione della superficie (triangoli) col piano coordinata[axis] =
    value: le curve chiuse, ognuna un array di punti in ordine (il primo non
    e' ripetuto in fondo), in ordine di primo triangolo incontrato.

    I vertici a meno di `weld` l'uno dall'altro si considerano lo stesso
    (le mesh di M ripetono i vertici per faccia): due triangoli vicini tagliano
    lo stesso spigolo nello stesso punto, ed e' cosi' che i pezzi si
    concatenano. Un vertice che stesse esattamente sul piano si conta dalla
    parte positiva, cosi' ogni spigolo e' tagliato al piu' una volta."""
    V = np.asarray(V, dtype=float)
    keys = {}
    ids = np.array([keys.setdefault(tuple(np.round(v / weld).astype(np.int64)), len(keys)) for v in V])
    d = V[:, axis] - value
    side = d >= 0.0

    def cut(a, b):
        """Il punto in cui lo spigolo a-b attraversa il piano, e la sua chiave."""
        key = (min(ids[a], ids[b]), max(ids[a], ids[b]))
        return key, V[a] + (V[b] - V[a]) * (d[a] / (d[a] - d[b]))

    links, points = {}, {}
    for f in faces:
        ends = []
        for k in range(len(f)):
            a, b = f[k], f[(k + 1) % len(f)]
            if side[a] != side[b]:
                key, p = cut(a, b)
                points[key] = p
                ends.append(key)
        if len(ends) == 2:
            links.setdefault(ends[0], []).append(ends[1])
            links.setdefault(ends[1], []).append(ends[0])
    loops, seen = [], set()
    for start in links:
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            nxt = [n for n in links[cur] if n != prev]
            if not nxt or nxt[0] == start:
                break
            prev, cur = cur, nxt[0]
            if cur in seen:
                break
            seen.add(cur)
            loop.append(cur)
        loops.append(np.array([points[k] for k in loop]))
    return loops


# =============================================================================
# LA PLATEA (cundy_deltahedra)
# =============================================================================

class Model:
    """Un deltaedro della platea: il file, la mesh (vertici saldati,
    centrata), il circonraggio, e dove sta (`location`, numpy)."""

    def __init__(self, path):
        self.path = path
        self.name = os.path.splitext(os.path.basename(path))[0]
        self.vertices, self.faces = load_welded(path)
        self.radius = float(np.linalg.norm(self.vertices, axis=1).max())
        self.location = np.zeros(3)


def load_models(models_dir, expected):
    """I modelli della cartella, in ordine di nome; errore se non sono
    `expected`."""
    paths = sorted(glob.glob(os.path.join(models_dir, "*.obj")))
    if len(paths) != expected:
        raise ValueError(f"{len(paths)} modelli in {models_dir}, ma ne servono {expected}")
    return [Model(p) for p in paths]


def arrange(models, rows, gap, row_gap, clearance):
    """Le file: i modelli ordinati per grandezza (a pari grandezza, per nome),
    i primi davanti; `rows` dice quanti pezzi per fila. Assegna le `location`
    e restituisce l'ordine di comparsa e le file.

    Dentro una fila il piu' grande sta al centro e gli altri si alternano a
    destra e a sinistra, a scalare; due vicini stanno alla distanza che serve
    a loro due (somma dei raggi piu' `gap`), non a quella del pezzo piu' grande
    della fila, che allargherebbe tutto per un pezzo solo. La distanza fra due
    file e' la somma dei loro raggi massimi piu' `row_gap`: non si toccano
    mai, nemmeno girando. Ogni pezzo sta `clearance` sopra il pavimento (z = 0).

    L'ordine di comparsa va fila per fila, da sinistra a destra."""
    by_size = sorted(models, key=lambda m: (round(m.radius, 3), m.name))
    out_rows, k = [], 0
    for n in rows:
        out_rows.append(by_size[k:k + n])
        k += n
    y, prev = 0.0, None
    for k, row in enumerate(out_rows):
        r = max(m.radius for m in row)
        if prev is not None:
            y += prev + r + row_gap
        prev = r
        # il piu' grande al centro, poi alternati: ..., 4, 2, 0, 1, 3, ...
        big_first = sorted(row, key=lambda m: (-m.radius, m.name))
        line = []
        for j, m in enumerate(big_first):
            if j % 2:
                line.append(m)
            else:
                line.insert(0, m)
        x, xs = 0.0, []
        for j, m in enumerate(line):
            if j:
                x += line[j - 1].radius + m.radius + gap
            xs.append(x)
        mid = (xs[0] - line[0].radius + xs[-1] + line[-1].radius) / 2.0
        for m, x in zip(line, xs):
            m.location = np.array([x - mid, y, m.radius + clearance])
        out_rows[k] = line
    order = [m for row in out_rows for m in row]
    return order, out_rows


class View:
    """Una camera prospettica che guarda dall'alto di `elevation_deg` gradi,
    nel piano yz (verso +y): la geometria della camera di Blender con
    sensor_fit AUTO e l'immagine piu' larga che alta."""

    def __init__(self, elevation_deg, lens, sensor_w, aspect):
        e = math.radians(elevation_deg)
        self.back = np.array([0.0, -math.cos(e), math.sin(e)])   # dal soggetto verso la camera
        self.right = np.array([1.0, 0.0, 0.0])
        self.up = np.cross(self.right, -self.back)
        self.lens, self.sensor_w, self.aspect = lens, sensor_w, aspect

    def project(self, points, target, distance):
        """Coordinate nell'immagine (0..1, y verso l'alto) dei punti, con la
        camera che guarda `target` da `distance`."""
        q = np.asarray(points) - (np.asarray(target) + self.back * distance)
        z = q @ -self.back
        sensor_h = self.sensor_w / self.aspect
        return (0.5 + (q @ self.right) / z * self.lens / self.sensor_w,
                0.5 + (q @ self.up) / z * self.lens / sensor_h)

    def frame_width(self, distance):
        """Larghezza dell'inquadratura a quella distanza."""
        return distance * self.sensor_w / self.lens


def sphere_cloud(centres, radii, n=300):
    """Punti sulle sfere (spirale di Fibonacci): quello che occupano i pezzi
    qualunque sia la loro rotazione."""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = math.pi * (1 + 5 ** 0.5) * i
    S = np.c_[np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)]
    return np.concatenate([S * r + np.asarray(c) for c, r in zip(centres, radii)])


def frame_all(view, centres, radii, fill):
    """(punto inquadrato, distanza): le sfere occupano `fill` (larghezza,
    altezza) dell'immagine nella dimensione che arriva prima al limite, e sono
    centrate. Bisezione sulla distanza e correzione del punto, alternate."""
    P = sphere_cloud(centres, radii)
    target = np.mean(np.asarray(centres), axis=0)
    for _ in range(10):
        lo, hi = 1.0, 500.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            x, y = view.project(P, target, mid)
            if (x.max() - x.min()) > fill[0] or (y.max() - y.min()) > fill[1]:
                lo = mid
            else:
                hi = mid
        d = hi
        x, y = view.project(P, target, d)
        w = view.frame_width(d)
        dx = ((x.min() + x.max()) / 2 - 0.5) * w
        dy = ((y.min() + y.max()) / 2 - 0.5) * w / view.aspect
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            break
        target = target + view.right * dx + view.up * dy
    return target, d
