"""
textures.py -- texture generate, puro numpy (niente bpy): coperto dai test.

border_triangle(): un triangolo equilatero con un bordo spesso e scuro e la
parte centrale chiara e neutra. Chiara e neutra perche' a colorarla e' il
materiale (texture per colore): il bordo, scuro, resta scuro per tutti.
"""

import math

import numpy as np


def border_triangle_uvs(margin=0.02):
    """Le UV dei tre vertici del triangolo, nell'ordine del triangolo canonico
    (pieces.CANONICAL_TRIANGLE): in alto, in basso a sinistra, in basso a
    destra. Il triangolo e' equilatero e centrato nel quadrato, a `margin` dai
    lati."""
    side = 1.0 - 2.0 * margin
    height = side * math.sqrt(3.0) / 2.0
    bottom = (1.0 - height) / 2.0
    return [(0.5, bottom + height), (margin, bottom), (1.0 - margin, bottom)]


def border_triangle(size=1024, border=0.22, dark=0.10, light=1.0, margin=0.02):
    """L'immagine: array (size, size, 4) di float RGBA, la riga 0 in basso
    (com'e' image.pixels in Blender), e le UV dei vertici.

    `border` e' lo spessore del bordo come frazione dell'inraggio del
    triangolo (la distanza dal centro ai lati): 0 = niente bordo, 1 = tutto
    bordo. Fuori dal triangolo e' scuro come il bordo, cosi' il filtraggio
    della texture vicino ai lati non porta dentro altro colore. Il passaggio
    fra bordo e centro e' sfumato su un pixel e mezzo, per non scalettare."""
    uvs = border_triangle_uvs(margin)
    corners = [np.asarray(p) for p in uvs]
    centre = sum(corners) / 3.0
    u, v = np.meshgrid((np.arange(size) + 0.5) / size, (np.arange(size) + 0.5) / size)
    P = np.stack([u, v], axis=-1)

    # distanza dal lato piu' vicino, positiva dentro il triangolo
    dist = None
    for k in range(3):
        p, q = corners[k], corners[(k + 1) % 3]
        d = q - p
        n = np.array([-d[1], d[0]]) / np.linalg.norm(d)
        if np.dot(centre - p, n) < 0:
            n = -n
        dk = (P - p) @ n
        dist = dk if dist is None else np.minimum(dist, dk)

    side = 1.0 - 2.0 * margin
    inradius = side * math.sqrt(3.0) / 6.0
    soft = 1.5 / size
    t = np.clip((dist - border * inradius) / soft + 0.5, 0.0, 1.0)
    value = dark + (light - dark) * t
    img = np.empty((size, size, 4))
    img[..., 0] = img[..., 1] = img[..., 2] = value
    img[..., 3] = 1.0
    return img, uvs


# =============================================================================
# LO SPESSORE DEL BORDO SULLA FACCIA
# =============================================================================
#
# Se una faccia corrisponde nella texture a un triangolo k volte piu' grande
# di quello disegnato (con lo stesso centro), il suo lato cade nello scuro che
# sta attorno al triangolo, e la fascia scura che si vede sulla faccia si
# allarga: la parte chiara resta quella disegnata, (1 - b0) volte l'inraggio
# del triangolo disegnato, mentre l'inraggio della faccia nella texture e' k
# volte quello. La fascia vale quindi 1 - (1 - b0) / k dell'inraggio della
# faccia. Una sola texture col bordo sottile da' cosi' qualunque spessore piu'
# grosso, scegliendo k.

def border_scale(target, drawn):
    """Il k per cui la fascia scura e' `target` dell'inraggio della faccia,
    con una texture il cui bordo disegnato e' `drawn` (frazioni in [0, 1))."""
    if not (drawn <= target < 1.0):
        raise ValueError(f"spessore {target:.3f} non ottenibile: dev'essere fra quello "
                         f"disegnato ({drawn}) e 1")
    return (1.0 - drawn) / (1.0 - target)


def scaled_uvs(uvs, k):
    """Le UV del triangolo ingrandito di k attorno al suo baricentro; errore se
    escono dall'immagine (la texture li' non c'e')."""
    cu = sum(p[0] for p in uvs) / 3.0
    cv = sum(p[1] for p in uvs) / 3.0
    out = [(cu + (u - cu) * k, cv + (v - cv) * k) for u, v in uvs]
    if any(not (0.0 <= c <= 1.0) for p in out for c in p):
        raise ValueError(f"ingrandito di {k:.3f} il triangolo esce dalla texture: "
                         f"serve un margine piu' grande")
    return out
