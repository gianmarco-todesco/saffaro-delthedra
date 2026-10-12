"""
v2/scene-2.py -- comincia dove finisce v2/scene-1.py (i 240 triangoli di M
nella griglia), e porta all'icosaedro, a M, al tetraedro e agli otto deltaedri
convessi. E' scene_2.py coi tempi della seconda versione del video.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0          l'ultimo fotogramma di v2/scene-1: i 240 triangoli nella
              griglia, stessa camera, stesso fondo, stessa luce, stesso
              materiale
   0.3 - 5.5  i triangoli si rimpiccioliscono fino a sparire, dal centro della
              griglia verso la periferia
   5 - 6      al centro compare l'icosaedro (scala da 0 a 1, ease in/out), gia'
              girando lentamente su se stesso
   6 - 7      gli compare accanto M
  15 - 17     M e l'icosaedro schizzano fuori dall'inquadratura, e fra i due
              cresce il tetraedro, formato a 17 s
  21          entra l'ottaedro (da sinistra), e il tetraedro sale al suo posto
  22          entra l'icosaedro (da destra): col tetraedro e l'ottaedro forma
              un triangolo stretto, nel piano dello schermo
  30          compaiono uno dopo l'altro, da sinistra a destra, gli altri
              cinque deltaedri convessi, ai vertici di un pentagono regolare
              attorno al triangolo
  34          fine

Ogni poliedro gira sempre su se stesso attorno all'asse verticale.

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* Il raccordo: camera, fondo, luce, griglia e materiale dei triangoli vengono
  da libs/story.py, gli stessi conti di scene_1. Il primo fotogramma e'
  l'ultimo di scene_1.
* La texture dei poliedri e' generata (textures.border_triangle): un
  triangolo equilatero con un bordo scuro e il centro chiaro e neutro, che
  ogni materiale moltiplica per il suo colore. Si riscrive in
  assets/face_border.png a ogni corsa. Il bordo e' largo uguale (BORDER_WORLD)
  su tutte le facce di tutti i poliedri: ognuno ingrandisce il triangolo UV
  quanto serve alla grandezza delle sue facce.
* M e l'icosaedro hanno la posa di M nel quadro, e l'icosaedro e' quello su
  cui e' costruita M: la stessa simmetria nella stessa posizione. Gli altri
  vengono da modelli-3d/convex-deltahedra.
* Ogni poliedro sta in una sfera di raggio PAIR_RADIUS (M e l'icosaedro,
  all'inizio) o del triangolo e del pentagono (dal triangolo in poi):
  l'icosaedro rientra piu' piccolo, perche' alla fine ci devono stare otto
  poliedri. Sono due oggetti, scambiati mentre e' fuori campo.
* Colori pastello, stessa luminosita' e saturazione in OKLCH (story.pastel);
  M azzurro, l'icosaedro albicocca (il complementare); il tetraedro e' un
  rosso piu' deciso, fuori dalla serie dei pastelli.
* Niente ombre portate, come nelle altre scene.
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).
"""

import bpy
import mathutils

import os, sys
import math
import importlib

import numpy as np

# rendi possibile importare i moduli da src/libs
# (nota bene: __file__ non funziona dallo script editor di Blender,
#  quindi si ricava il path del file dal datablock di testo attivo)
def _find_libs_dir():
    txt = getattr(getattr(bpy.context, "space_data", None), "text", None)
    if txt is None:  # lo script non gira dal Text Editor: cerco il datablock per nome
        txt = bpy.data.texts.get("scene-2.py")
    if txt is None or not txt.filepath:
        raise RuntimeError(
            "non riesco a ricavare il path dello script: il testo non e' salvato "
            "su disco (Text > Save As) oppure e' un blocco 'interno'"
        )
    # attenzione: se il file e' stato aperto con l'opzione 'Relative Path' spuntata,
    # filepath e' del tipo '//../...' (relativo al .blend) e os.path lo interpreta
    # come percorso UNC. bpy.path.abspath lo risolve; sugli assoluti non fa nulla.
    path = os.path.abspath(bpy.path.abspath(txt.filepath))
    # script in src/scripts/v2, librerie in src/libs
    libs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(path))), "libs")
    if not os.path.isdir(libs):
        raise RuntimeError(f"cartella libs non trovata: {libs}  (filepath: {txt.filepath})")
    return libs


_LIBS = _find_libs_dir()
if _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender
import geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story, textures
for _mod in (geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story, textures):
    importlib.reload(_mod)

from mathutils import Vector


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S2V2"
COLLECTION_NAME = "scene-2_v2"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO   = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR = os.path.join(_SAFFARO, "assets")
MODELS_DIR = os.path.join(_SAFFARO, "modelli-3d", "convex-deltahedra")

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

# --- la scaletta, in secondi ---
VANISH          = (0.3, 5.5)     # i triangoli spariscono, dal centro alla periferia
VANISH_SECONDS  = 0.8            # quanto ci mette un triangolo a rimpicciolirsi
ICO_IN          = (5.0, 6.0)     # l'icosaedro compare
M_IN            = (6.0, 7.0)     # M compare
SPLIT_END       = 17.0           # M e l'icosaedro sono fuori, il tetraedro e' formato...
SPLIT_SECONDS   = 2.0            # ... in tanti secondi
# quando entrano i tre del triangolo (il tetraedro sale con l'ottaedro)
TRIO_IN         = {"octa": 21.0, "tetra": 21.0, "ico_ring": 22.0}
TRIO_SECONDS    = 1.8            # quanto ci mettono ad arrivare
PENTAGON_IN     = 30.0           # compare il primo dei cinque
PENTAGON_GAP    = 0.4            # fra uno e il successivo
GROW_SECONDS    = 0.8            # quanto ci mette uno dei cinque a comparire
END_AT          = 34.0

SPIN_SECONDS_PER_TURN = 20.0     # ognuno su se stesso

# --- la texture ---
TEXTURE_FILE   = "face_border.png"   # generata in assets a ogni corsa
TEXTURE_SIZE   = 1024
TEXTURE_MARGIN = 0.10            # fra il triangolo disegnato e il bordo dell'immagine
BORDER_DARK    = 0.10            # il grigio del bordo (sRGB, 0..1)
ROUGHNESS      = 0.5
# Lo spessore del bordo scuro, uguale su tutte le facce di tutti i poliedri:
# BORDER_WORLD in unita' del mondo, sul poliedro alla sua grandezza (circa 3
# pixel a 1080 righe). La texture lo disegna sottilissimo (BORDER_DRAWN, in
# frazione dell'inraggio del triangolo), e ogni poliedro lo allarga quanto
# serve alle sue facce ingrandendo il triangolo UV (si veda textures.py).
BORDER_WORLD   = 0.022
BORDER_DRAWN   = 0.04

# --- i poliedri: chiave -> (file, tinta OKLCH, (luminosita', saturazione) o None) ---
# None = il pastello del racconto (story.pastel). M e l'icosaedro hanno la posa
# di M nel quadro; gli altri quella del file. L'icosaedro e' due oggetti: quello
# della coppia con M e quello che rientra piu' piccolo col triangolo (ico_ring),
# perche' con la grandezza cambia anche il triangolo UV che da' lo spessore del
# bordo.
POLYHEDRA = {
    "M":        (None,                                     230.0, None),          # azzurro
    "ico":      (None,                                      70.0, None),          # albicocca
    "tetra":    ("01_Regular_Tetrahedron.obj",              25.0, (0.65, 0.18)),  # rosso deciso
    "ico_ring": (None,                                      70.0, None),
    "octa":     ("03_Regular_Octahedron.obj",              150.0, None),          # verde menta
    "tribi":    ("02_Triangular_Bipyramid.obj",            300.0, None),          # lilla
    "pentbi":   ("04_Pentagonal_Bipyramid.obj",            190.0, None),          # verde acqua
    "snub":     ("05_Snub_Disphenoid.obj",                 110.0, None),          # giallo
    "triaug":   ("06_Triaugmented_Triangular_Prism.obj",   350.0, None),          # rosa
    "gyro":     ("07_Gyroelongated_Square_Bipyramid.obj",  275.0, None),          # lavanda
}

# --- la disposizione, nel piano dello schermo (y = 0) ---
PAIR_RADIUS   = 1.0              # M e l'icosaedro, all'inizio
PAIR_GAP      = 0.5              # fra le loro sfere
RING_FILL     = 0.84             # il pentagono, con i pezzi, occupa tanta altezza dell'immagine
INNER_RATIO   = 1.45             # raggio del triangolo, in raggi dei pezzi
OUTER_RATIO   = 3.75             # raggio del pentagono: la corona e' larga 2.3 raggi > un diametro
# gli angoli (gradi; 0 = a destra, 90 = in alto): il tetraedro in alto,
# l'icosaedro in basso a destra (arriva da destra), l'ottaedro in basso a sinistra
TRIO_ANGLES = {"tetra": 90.0, "ico_ring": -30.0, "octa": 210.0}
# il pentagono ha un vertice in basso, fra l'icosaedro e l'ottaedro; i cinque
# vanno da sinistra a destra in ordine di numero di facce
PENTAGON = ("tribi", "pentbi", "snub", "triaug", "gyro")
PENTAGON_ANGLES = (198.0, 126.0, 270.0, 54.0, -18.0)
OUT_MARGIN = 1.0                 # di quanto si esce dall'inquadratura, oltre la sfera


# =============================================================================
# LA REGIA
# =============================================================================

T_SPLIT0  = SPLIT_END - SPLIT_SECONDS
T_TRIO0   = min(TRIO_IN.values())
T_TRIO1   = max(TRIO_IN.values()) + TRIO_SECONDS
FRAME_END = FRAME_START + int(round(END_AT * FPS))


def frame_of(t):
    return FRAME_START + int(round(t * FPS))


def time_of(frame):
    return (frame - FRAME_START) / FPS


def ramp(t, t0, t1):
    return min(1.0, max(0.0, (t - t0) / (t1 - t0)))


def ease_in(u):
    return u ** 3


def ease_out(u):
    return 1.0 - (1.0 - u) ** 3


def ease_inout(u):
    return u * u * (3.0 - 2.0 * u)


def _check_schedule():
    marks = [0.0, VANISH[0], ICO_IN[0], M_IN[0], M_IN[1], T_SPLIT0, SPLIT_END, T_TRIO0, T_TRIO1,
             PENTAGON_IN, PENTAGON_IN + 4 * PENTAGON_GAP + GROW_SECONDS, END_AT]
    if marks != sorted(marks):
        raise ValueError(f"scaletta fuori ordine: {marks}")


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


def normalized(V):
    """Vertici centrati nel baricentro e scalati nella sfera unitaria: la
    grandezza la da' la scala dell'oggetto."""
    V = np.asarray(V, dtype=float)
    V = V - V.mean(axis=0)
    return V / np.linalg.norm(V, axis=1).max()


def color(key):
    """Il colore del poliedro, RGBA lineare."""
    _, hue, lc = POLYHEDRA[key]
    if lc is None:
        return story.pastel(hue)
    rgba, clipped = m_scene.oklch_to_linear(lc[0], lc[1], hue)
    if clipped:
        raise ValueError(f"il colore di {key} esce dal gamut sRGB")
    return rgba


def polyhedron_mesh(key, md_m, material, base_uvs, radius):
    """La mesh del poliedro `key`, nella sfera unitaria, con la stessa UV su
    tutte le facce (sono tutte triangoli equilateri uguali).

    `radius` e' la grandezza a cui lo si vede (la scala dell'oggetto): da li'
    l'inraggio delle facce nel mondo, e l'ingrandimento del triangolo UV per
    cui il bordo scuro e' largo BORDER_WORLD. Restituisce (mesh, frazione
    dell'inraggio occupata dal bordo, ingrandimento)."""
    source = POLYHEDRA[key][0]
    R = np.asarray(story.orient_matrix().to_3x3())
    if key == "M":
        V, faces = np.asarray(md_m.vertices) @ R.T, md_m.faces
    elif key in ("ico", "ico_ring"):
        ico = geometry.Polyhedron.ico
        V, faces = np.asarray([v.tup() for v in ico.vertices]) @ R.T, ico.faces
    else:
        md = geometry.read_obj(os.path.join(MODELS_DIR, source))
        V, faces = md.vertices, md.faces
    V = normalized(V)
    edge = float(np.linalg.norm(V[faces[0][0]] - V[faces[0][1]]))
    inradius = edge * radius * math.sqrt(3.0) / 6.0
    fraction = BORDER_WORLD / inradius
    k = textures.border_scale(fraction, BORDER_DRAWN)
    mesh = bpy.data.meshes.new(KIT.name(key))
    mesh.from_pydata([tuple(v) for v in V], [], [list(f) for f in faces])
    bl_utils.set_triangle_uvs(mesh, textures.scaled_uvs(base_uvs, k))
    mesh.materials.append(material)
    mesh.update()
    return mesh, fraction, k


def build_vanishing_triangles(layout, md):
    """I 240 triangoli dove li lascia scene_1, nel mondo: stessa griglia,
    stessa scala, rotazione identita', stesso materiale a fine esplosione
    (Look 1, Fade 1). Ognuno si rimpicciolisce fino a sparire, prima quelli
    vicini al centro della griglia."""
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    mat = story.face_material(KIT, face_img, uvs)
    mat.node_tree.nodes["Look"].inputs["Fac"].default_value = 1.0
    mesh = m_scene.triangle_mesh(KIT, mat, uvs)
    tris = [m_scene.Tri(p) for p in pieces.m_pieces(md)]
    targets, world, scale = layout.grid(tris)
    centre = sum(world, Vector()) / len(world)
    far = max((w - centre).length for w in world)
    for tri, (loc, quat, s), w in zip(tris, targets, world):
        obj = KIT.new_object(f"tri_{tri.piece.index:03d}", mesh)
        obj.location = loc
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = quat
        obj.visible_shadow = False
        t0 = VANISH[0] + (VANISH[1] - VANISH_SECONDS - VANISH[0]) * (w - centre).length / far
        f0, f1 = frame_of(t0), frame_of(t0 + VANISH_SECONDS)
        bl_anim.key_value(obj, "scale", [(f, (s * (1.0 - ease_in(ramp(time_of(f), t0, t0 + VANISH_SECONDS))),) * 3)
                                         for f in range(f0, f1 + 1)], interpolation='LINEAR')
        bl_anim.key_visibility(obj, [(FRAME_START, True), (f1 + 1, False)])
        tri.obj = obj
    return tris, world, scale


def build_texture():
    img, uvs = textures.border_triangle(size=TEXTURE_SIZE, border=BORDER_DRAWN, dark=BORDER_DARK,
                                        margin=TEXTURE_MARGIN)
    image = m_scene.write_image(os.path.join(ASSETS_DIR, TEXTURE_FILE), img)
    return image, uvs


def plan(layout):
    """Dove sta ogni pezzo, in ogni fase: centri e raggi, nel mondo."""
    _, fh = layout.frame_size(0.0)
    fw, _ = layout.frame_size(0.0)
    centre = layout.screen_to_world(0.5, 0.5)
    right, up = Vector((1.0, 0.0, 0.0)), Vector((0.0, 0.0, 1.0))
    ring_r = RING_FILL * fh / 2.0 / (OUTER_RATIO + 1.0)
    x_pair = PAIR_RADIUS + PAIR_GAP / 2.0
    x_out = fw / 2.0 + PAIR_RADIUS + OUT_MARGIN

    def on_circle(radius, angle_deg):
        a = math.radians(angle_deg)
        return centre + right * (radius * math.cos(a)) + up * (radius * math.sin(a))

    return {
        "centre": centre, "ring_r": ring_r, "x_out": x_out,
        "ico_pair": centre - right * x_pair, "m_pair": centre + right * x_pair,
        "trio": {k: on_circle(INNER_RATIO * ring_r, a) for k, a in TRIO_ANGLES.items()},
        "pentagon": {k: on_circle(OUTER_RATIO * ring_r, a) for k, a in zip(PENTAGON, PENTAGON_ANGLES)},
    }


def position(key, t, P):
    """Dove sta il pezzo `key` all'istante t."""
    right = Vector((1.0, 0.0, 0.0))
    out = ease_in(ramp(t, T_SPLIT0, SPLIT_END))
    if key == "M":
        return P["m_pair"] + right * (out * (P["x_out"] - (P["m_pair"] - P["centre"]).x))
    if key == "ico":
        return P["ico_pair"] - right * (out * (P["x_out"] + (P["ico_pair"] - P["centre"]).x))
    if key in TRIO_ANGLES:
        start = {"ico_ring": P["centre"] + right * P["x_out"], "octa": P["centre"] - right * P["x_out"],
                 "tetra": P["centre"]}[key]
        u = ramp(t, TRIO_IN[key], TRIO_IN[key] + TRIO_SECONDS)
        u = ease_inout(u) if key == "tetra" else ease_out(u)
        return start.lerp(P["trio"][key], u)
    return P["pentagon"][key]


def scale_keys(key, P):
    """(secondi, scala) del pezzo: comparire e' crescere da 0."""
    r = P["ring_r"]
    if key == "ico":
        return [(ICO_IN[0], 0.0), (ICO_IN[1], PAIR_RADIUS)]
    if key == "M":
        return [(M_IN[0], 0.0), (M_IN[1], PAIR_RADIUS)]
    if key == "tetra":
        return [(T_SPLIT0, 0.0), (SPLIT_END, r)]
    if key in ("octa", "ico_ring"):
        return [(TRIO_IN[key], r)]
    k = PENTAGON.index(key)
    t0 = PENTAGON_IN + k * PENTAGON_GAP
    return [(t0, 0.0), (t0 + GROW_SECONDS, r)]


def appear_time(key):
    return {"ico": ICO_IN[0], "M": M_IN[0], "tetra": T_SPLIT0, "octa": TRIO_IN["octa"],
            "ico_ring": TRIO_IN["ico_ring"]}.get(
        key, PENTAGON_IN + PENTAGON.index(key) * PENTAGON_GAP if key in PENTAGON else 0.0)


def build():
    _check_schedule()
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    m_scene.use_cycles(scene)
    KIT.new_collection(scene)

    md = extended_face.make_M()
    painting_img = KIT.load_image(story.PAINTING_FILE)       # serve solo per le sue proporzioni
    layout = story.Layout(md, painting_img.size)
    story.build_camera_and_world(KIT, layout, clip_end=story.CAMERA_DISTANCE + story.GRID_DEPTH + 30.0)

    tris, world, grid_scale = build_vanishing_triangles(layout, md)

    texture, uvs = build_texture()
    P = plan(layout)
    frames = list(range(FRAME_START, FRAME_END + 1))
    spin = 2.0 * math.pi / (SPIN_SECONDS_PER_TURN * FPS)      # radianti a fotogramma
    borders = []
    for n, key in enumerate(POLYHEDRA):
        mat = m_scene.tinted_texture_material(KIT, f"mat_{key}", texture, color(key), ROUGHNESS)
        radius = PAIR_RADIUS if key in ("M", "ico") else P["ring_r"]
        mesh, fraction, k = polyhedron_mesh(key, md, mat, uvs, radius)
        borders.append(f"{key} {fraction:.2f} (x{k:.3f})")
        obj = KIT.new_object(key, mesh)
        obj.visible_shadow = False
        bl_anim.key_value(obj, "location", [(f, tuple(position(key, time_of(f), P))) for f in frames],
                          interpolation='LINEAR')
        bl_anim.key_value(obj, "scale", [(frame_of(t), (s,) * 3) for t, s in scale_keys(key, P)])
        # gira sempre, ognuno con la sua fase: due chiavi e una retta
        f0 = frame_of(appear_time(key))
        phase = 2.0 * math.pi * ((n * 0.618034) % 1.0)
        obj.rotation_mode = 'XYZ'
        bl_anim.key_value(obj, "rotation_euler",
                          [(f0, (0.0, 0.0, phase)),
                           (FRAME_END, (0.0, 0.0, phase + spin * (FRAME_END - f0)))],
                          interpolation='LINEAR')
        bl_anim.key_visibility(obj, [(FRAME_START, False), (f0, True)]
                               + ([(frame_of(SPLIT_END) + 1, False)] if key in ("M", "ico") else []))

    scene.frame_set(FRAME_START)
    print(f"[scene-2 v2] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END_AT:.1f} s)")
    print(f"[scene-2 v2] raccordo: camera in ({layout.eye.x:.3f}, {layout.eye.y:.1f}, {layout.eye.z:.3f}), "
          f"focale {layout.lens:.2f} mm, triangoli scalati a {grid_scale:.3f}")
    print(f"[scene-2 v2] M e icosaedro di raggio {PAIR_RADIUS}, poi i pezzi di raggio {P['ring_r']:.3f}; "
          f"triangolo di raggio {INNER_RATIO * P['ring_r']:.3f}, pentagono di raggio {OUTER_RATIO * P['ring_r']:.3f}")
    print(f"[scene-2 v2] split {T_SPLIT0:.3f}-{SPLIT_END:.3f} s, trio {T_TRIO0:.3f}-{T_TRIO1:.3f} s")
    print(f"[scene-2 v2] bordo largo {BORDER_WORLD} ovunque; in frazione dell'inraggio delle facce "
          f"(e ingrandimento del triangolo UV): " + ", ".join(borders))
    return tris


TRIS = build()
