"""
M_video.py -- il video: dal quadro di Saffaro al poliedro M, che gira, si
mostra dentro il suo icosaedro, ed esplode nei suoi 240 triangoli allineati in
una griglia per poterli contare.

Una sola scena, una sola timeline, tutto bakerato in keyframe quando lo script
gira: nessun handler, quindi Render Animation e `blender -b -a` funzionano. Lo
script e' idempotente: rilanciandolo cancella quello che aveva creato e rifa'
tutto. Conviene tenerlo in un .blend suo: i nomi hanno il prefisso MV_ per non
scontrarsi con quelli di explode_M e M_story, ma la scena (camera, mondo,
gestione del colore) la imposta lui.

--------------------------------------------------------------------------
LA SCALETTA (BEATS)
--------------------------------------------------------------------------
  quadro        si vede solo il quadro
  dissolvenza   il quadro si dissolve e sotto c'e' M, nella stessa posa; la
                camera e' ferma, centrata su M, fino all'esplosione
  giro          M comincia a girare
  ico_entra     compare l'icosaedro-gabbia (i tubi crescono di spessore)
  ico_resta     M e la gabbia girano insieme; a fine battuta il perno e' fermo
  ico_esce      la gabbia sparisce
  pausa         M fermo
  esplosione    i 240 triangoli si staccano, sfalsati, e volano sulla griglia
                sullo sfondo, mentre la camera arretra
  conta         la griglia ferma: 20 gruppi da 12

Cambiando una durata tutto il resto si sposta da solo.

--------------------------------------------------------------------------
LA GERARCHIA
--------------------------------------------------------------------------
  MV_camera                prospettica o ortografica (CAMERA_TYPE), guarda
                           lungo +Y (come la vista Fronte), ferma fino
                           all'esplosione, poi allarga il campo
  MV_sun                   la luce
  MV_painting              il quadro: un piano davanti a tutto
  MV_pivot                 empty: e' lui che ruota (asse Z)
   +- MV_orient            empty fermo: la posa di M nel quadro
       +- MV_M             M come mesh saldata: si vede fino all'esplosione
       +- MV_ico           l'icosaedro-gabbia
       +- MV_tri_000..239  i 240 triangoli: compaiono all'esplosione,
                           esattamente dove sta MV_M

M saldata e triangoli separati occupano le stesse posizioni, quindi lo scambio
al primo fotogramma dell'esplosione non si vede; serve perche' 240 oggetti con
spigoli coincidenti solo numericamente possono lasciar filtrare lo sfondo lungo
gli spigoli. USE_MERGED_M = False mostra i triangoli dall'inizio.

La griglia e' calcolata in coordinate mondo -- rivolta alla camera, sul piano
GRID_DEPTH -- e solo dopo riportata nel riferimento di MV_orient, al fotogramma
in cui l'esplosione parte e il perno e' gia' fermo. Per questo funziona con
qualsiasi posa e qualsiasi numero di giri.

--------------------------------------------------------------------------
LA POSA DEL QUADRO (ORIENT_EULER_DEG)
--------------------------------------------------------------------------
Il piano del quadro viene scalato e posizionato in modo che il poliedro dipinto
(PAINTING_MODEL_BOX, in pixel) abbia la stessa altezza e lo stesso centro della
proiezione di M. Resta da trovare la rotazione di M, e quella si regola a
occhio:

  1. vai a meta' della battuta 'dissolvenza': il quadro e' trasparente al 50%
     e fa da carta velina su M;
  2. ruota MV_orient a mano (R, oppure i campi Rotation nel pannello N) finche'
     gli spigoli combaciano;
  3. rilancia lo script: prima di ricostruire stampa a console la rotazione
     che hai dato a MV_orient, pronta da copiare in ORIENT_EULER_DEG.

--------------------------------------------------------------------------
DOVE SI METTONO LE MANI
--------------------------------------------------------------------------
* BEATS, PIVOT_TURNS          -> la scaletta e i giri
* ORIENT_EULER_DEG            -> la posa del quadro (si veda sopra)
* LIGHT_*, AMBIENT, colori    -> la luce: il quadro e' illuminato da sinistra
                                 in alto, e piu' la luce somiglia meno la
                                 dissolvenza si nota
* GRID, GRID_*, CAMERA_ZOOM_OUT -> la formazione finale e quanto arretra la camera
* explosion_keys(), start_delay() -> la traiettoria dei triangoli
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
        txt = bpy.data.texts.get("M_video.py")
    if txt is None or not txt.filepath:
        raise RuntimeError(
            "non riesco a ricavare il path dello script: il testo non e' salvato "
            "su disco (Text > Save As) oppure e' un blocco 'interno'"
        )
    # attenzione: se il file e' stato aperto con l'opzione 'Relative Path' spuntata,
    # filepath e' del tipo '//../...' (relativo al .blend) e os.path lo interpreta
    # come percorso UNC. bpy.path.abspath lo risolve; sugli assoluti non fa nulla.
    path = os.path.abspath(bpy.path.abspath(txt.filepath))
    # script in src/scripts, librerie in src/libs
    libs = os.path.join(os.path.dirname(os.path.dirname(path)), "libs")
    if not os.path.isdir(libs):
        raise RuntimeError(f"cartella libs non trovata: {libs}  (filepath: {txt.filepath})")
    return libs


_LIBS = _find_libs_dir()
if _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender
import geometry, bl_utils, extended_face, pieces, bl_anim, m_scene
for _mod in (geometry, bl_utils, extended_face, pieces, bl_anim, m_scene):
    importlib.reload(_mod)

from bl_anim import Key


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "MV"
COLLECTION_NAME = "M_video"

# saffaro/assets, accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
ASSETS_DIR        = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_LIBS))), "assets")
PAINTING_FILE     = "m.jpg"
FACE_TEXTURE_FILE = "m2face_texture.png"

FPS         = 24
RESOLUTION  = (1920, 1080)
FRAME_START = 1

BEATS = [
    ("quadro",      3.0),
    ("dissolvenza", 2.5),
    ("giro",        4.0),
    ("ico_entra",   2.0),
    ("ico_resta",   3.0),
    ("ico_esce",    1.0),
    ("pausa",       0.5),
    ("esplosione",  6.0),
    ("conta",       4.0),
]

# I giri del perno attorno a Z: (prima battuta, ultima battuta, giri). Sono
# cumulativi, ognuno con ease in/out. L'ultimo deve finire prima
# dell'esplosione: la griglia e' calcolata col perno fermo.
PIVOT_TURNS = [
    ("giro", "ico_resta", 2.0),
]

# La posa di M nel quadro, angoli di Eulero XYZ in gradi su MV_orient.
# Trovata a occhio sulla dissolvenza (si veda "LA POSA DEL QUADRO" in testa al
# file): una sola rotazione attorno a X.
ORIENT_EULER_DEG = (20.7862, 0.0, 0.0)

# --- il quadro ---
# Dove sta il poliedro dipinto in m.jpg, in pixel (x0, y0, x1, y1), misurato
# sui pixel blu. Serve a far coincidere le proporzioni del quadro con M.
PAINTING_MODEL_BOX = (66, 107, 814, 797)
PAINTING_FILL      = 0.92       # quanta altezza dell'inquadratura occupa il quadro

# --- il mondo e la luce ---
# Il fondo e' il crema del quadro (media dei suoi angoli), cosi' quando il
# quadro si dissolve lo sfondo non cambia. Con la vista 'Standard' i colori
# escono come sono scritti: con AgX (il default) il quadro uscirebbe smorto.
BACKGROUND_SRGB   = (217, 214, 198)
AMBIENT           = 0.35        # quanto il fondo illumina la scena (1 = quanto si vede)
USE_STANDARD_VIEW = True
# Verso cui va la luce. Nel quadro arriva da sinistra; la si tiene nel piano
# dell'immagine (y = 0) perche' con FACE_SHADING = 'PAINTED' e' cosi' che le
# facce *visibili* hanno la stessa proporzione di toni chiari e scuri del
# quadro (si veda FACE_PALETTE): con una componente verso la scena (y > 0) M
# si schiarisce, con una verso la camera si scurisce.
LIGHT_DIRECTION   = (0.866, 0.0, -0.5)   # da sinistra, un po' dall'alto
LIGHT_STRENGTH    = 3.0

# --- la texture delle facce ---
# I tre vertici del triangolo azzurro in m2face_texture.png, in pixel, nello
# stesso ordine dei vertici del triangolo canonico (in alto, in basso a
# sinistra, a destra). Misurati sui pixel: nell'immagine il triangolo non e'
# equilatero perche' e' ritagliato dal quadro, dove e' dipinto di scorcio.
FACE_UV_PX    = ((109, 12), (36, 496), (452, 277))
FACE_UV_INSET = 0.04            # la UV rientra del 4% verso il baricentro, per
                                # non pescare i bordi scuri del ritaglio
FACE_ROUGHNESS = 0.75

# Come si colorano le facce.
#
# 'PAINTED'  -> i colori del quadro. Nel quadro una faccia che si scurisce non
#               diventa grigia: la tinta ruota dal ciano al blu (da 192 a 221
#               gradi) e la saturazione resta fra 0.85 e 0.95. Nessuna luce
#               fisica lo fa -- il colore illuminato e' quello della superficie
#               per la luce, e i mezzitoni del quadro sono piu' blu di qualsiasi
#               miscela dei due estremi -- quindi il materiale calcola da se'
#               quanto la faccia guarda verso LIGHT_DIRECTION e ne prende il
#               colore da FACE_PALETTE, moltiplicato per la grana della texture.
#               Emissivo: ignora sole e ambiente, e M non fa ombra su se stesso
#               (nemmeno nel quadro). Funziona in Cycles e in EEVEE.
# 'PHYSICAL' -> Principled con la texture, illuminato dal sole e dall'ambiente.
FACE_SHADING = 'PAINTED'

# La tavolozza del quadro: (posizione, sRGB). Misurata su tutti i pixel del
# poliedro dipinto in m.jpg, ordinati per luminanza: la posizione e' il
# quantile, il colore e' la mediana dei pixel attorno a quel quantile.
# La posizione di una faccia e' (n.l + 1) / 2, con n la normale e l la
# direzione da cui arriva la luce: 0 volta le spalle alla luce, 0.5 la prende di
# taglio, 1 la guarda in pieno. Non e' una scelta estetica: per normali sparse
# in tutte le direzioni n.l e' distribuito uniformemente, quindi (n.l + 1) / 2
# ha la stessa distribuzione dei quantili, e la proporzione fra toni chiari e
# scuri torna con quella del quadro.
FACE_PALETTE = [
    (0.00, (2, 13, 36)),
    (0.08, (4, 37, 74)),
    (0.20, (12, 67, 106)),
    (0.35, (19, 92, 130)),
    (0.50, (24, 121, 169)),
    (0.65, (26, 137, 186)),
    (0.80, (28, 150, 199)),
    (0.92, (26, 178, 226)),
    (1.00, (30, 188, 228)),
]
FACE_GRAIN = 1.0                # quanto della grana della texture resta (0 = tinta piatta)

USE_MERGED_M = True

# --- l'icosaedro ---
ICO_MARGIN         = 1.0        # 1.0 = tangente agli spigoli di M (si veda M_ico.py)
ICO_WIRE_THICKNESS = 0.06
ICO_COLOR          = (0.95, 0.72, 0.15, 1.0)

# --- l'esplosione ---
# 20 gruppi da 12, disposti 5 x 4 perche' stiano in un'inquadratura 16:9.
GRID = pieces.Grid(group_cols=5, group_rows=4, cols_per_group=4, rows_per_group=3,
                   spacing=1.2, group_gap=0.6)
GRID_DEPTH      = 4.0           # y del piano della griglia: dietro a M
GRID_FILL       = 0.90          # quanta larghezza (o altezza) dell'inquadratura occupa
CAMERA_ZOOM_OUT = 1.25          # di quanto arretra la camera durante l'esplosione
ZOOM_FRACTION   = 0.5           # in quanta parte dell'esplosione arretra
STAGGER_SECONDS = 1.5           # fra il primo triangolo che parte e l'ultimo
POP_DISTANCE    = 0.8           # di quanto si stacca lungo la normale, prima di volare
POP_FRACTION    = 0.25          # in quanta parte del volo

# --- la camera ---
# 'PERSP' o 'ORTHO'. Con la prospettica e' la distanza a decidere quanto e'
# forte la prospettiva; la focale non si sceglie, si calcola perche' il quadro
# occupi PAINTING_FILL dell'inquadratura. Con l'ortografica la distanza conta
# solo per il clipping.
CAMERA_TYPE     = 'PERSP'
CAMERA_DISTANCE = 15.0          # dal centro di M, lungo -Y
SENSOR_WIDTH    = 36.0          # mm, il default di Blender


# =============================================================================
# LA REGIA
# =============================================================================

def _build_marks():
    """Da BEATS ai fotogrammi: {nome: (primo frame, ultimo frame)}."""
    marks, f = {}, FRAME_START
    for name, seconds in BEATS:
        end = f + int(round(seconds * FPS))
        marks[name] = (f, end)
        f = end
    return marks


MARKS = _build_marks()
FRAME_END = MARKS[BEATS[-1][0]][1]


def beat(name):
    """(primo, ultimo) fotogramma della battuta."""
    return MARKS[name]


def pivot_keys():
    """(frame, angoli) del perno: un keyframe all'inizio e uno alla fine di
    ogni ripresa di PIVOT_TURNS, con l'angolo cumulato. Fra due riprese il
    perno resta fermo (AUTO_CLAMPED fra due chiavi uguali)."""
    keys, angle = [(FRAME_START, (0.0, 0.0, 0.0))], 0.0
    for first, last, turns in PIVOT_TURNS:
        keys.append((beat(first)[0], (0.0, 0.0, angle)))
        angle += 2.0 * math.pi * turns
        keys.append((beat(last)[1], (0.0, 0.0, angle)))
    return keys


def pivot_matrix_at_rest():
    """La matrice del perno a fine rotazione, quando l'esplosione parte."""
    last = max(beat(last)[1] for _, last, _ in PIVOT_TURNS) if PIVOT_TURNS else FRAME_START
    if last > beat("esplosione")[0]:
        raise ValueError("PIVOT_TURNS: il perno deve fermarsi prima dell'esplosione")
    return mathutils.Matrix.Rotation(pivot_keys()[-1][1][2], 4, 'Z')


def orient_matrix():
    return mathutils.Euler([math.radians(a) for a in ORIENT_EULER_DEG], 'XYZ') \
        .to_matrix().to_4x4()


# =============================================================================
# L'ESPLOSIONE  --  e' qui che si mettono le mani
# =============================================================================

def start_delay(tri, ranks):
    """Ritardo (frame) con cui parte il triangolo. Default: un ventaglio alla
    volta, prima quelli verso la camera; `ranks[fan]` va da 0 (il piu' vicino)
    a 19."""
    return STAGGER_SECONDS * FPS * ranks[tri.piece.fan] / 19.0


def explosion_keys(tri, target, ranks):
    """Keyframe del triangolo: fermo in M, poi si stacca lungo la normale e
    vola alla sua cella. `target` = (location, quaternione, scala) nel
    riferimento di MV_orient."""
    e0, e1 = beat("esplosione")
    fly = (e1 - e0) - STAGGER_SECONDS * FPS
    t1 = e0 + start_delay(tri, ranks)
    t2 = t1 + fly
    normal = mathutils.Vector(tri.piece.normal)
    return [
        Key(FRAME_START, tri.loc, tri.quat, 1.0),
        Key(t1, tri.loc, tri.quat, 1.0),
        Key(t1 + POP_FRACTION * fly, tri.loc + normal * POP_DISTANCE, tri.quat, 1.0),
        Key(t2, *target),
    ]


# =============================================================================
# COSTRUZIONE
# =============================================================================
#
# I pezzi comuni ai video di M (materiale dipinto, mesh, icosaedro, camera,
# griglia) stanno in m_scene; qui ci sono solo le scelte di questo video.

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)
CAMERA = m_scene.CameraRig(CAMERA_TYPE, CAMERA_DISTANCE, SENSOR_WIDTH, RESOLUTION)


def report_hand_orientation():
    """Se MV_orient e' stato ruotato a mano, stampa la rotazione da copiare in
    ORIENT_EULER_DEG prima che la ricostruzione la cancelli."""
    orient = bpy.data.objects.get(KIT.name("orient"))
    if orient is None:
        return
    got = tuple(round(math.degrees(a), 3) for a in orient.rotation_euler)
    if any(abs(g - c) > 1e-3 for g, c in zip(got, ORIENT_EULER_DEG)):
        print(f"[M_video] MV_orient era stato ruotato a mano: "
              f"ORIENT_EULER_DEG = {got}")


def face_material(image, uvs):
    """Il materiale delle facce, secondo FACE_SHADING."""
    if FACE_SHADING == 'PHYSICAL':
        return m_scene.physical_face_material(KIT, image, FACE_ROUGHNESS)
    if FACE_SHADING == 'PAINTED':
        return m_scene.painted_face_material(KIT, image, uvs, FACE_PALETTE,
                                             LIGHT_DIRECTION, FACE_GRAIN)
    raise ValueError(f"FACE_SHADING dev'essere 'PAINTED' o 'PHYSICAL', non {FACE_SHADING!r}")


def painting_material(image):
    """Il quadro com'e', senza luce: emissione dell'immagine, mescolata con un
    Transparent dal nodo 'Fade' (1 = quadro, 0 = trasparente)."""
    mat, nodes, links = KIT.new_material("painting")
    out = nodes.new("ShaderNodeOutputMaterial")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    emit = nodes.new("ShaderNodeEmission")
    clear = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    mix.name = "Fade"
    links.new(tex.outputs["Color"], emit.inputs["Color"])
    links.new(clear.outputs["BSDF"], mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    mix.inputs["Fac"].default_value = 1.0
    bl_utils.set_blended(mat)
    return mat


def model_points(md):
    """I vertici di M in coordinate mondo quando il quadro e' in scena (perno a
    zero), numpy (N, 3)."""
    R = np.asarray(orient_matrix().to_3x3())
    return np.asarray(md.vertices, dtype=float) @ R.T


def model_frame(md):
    """Centro (x, z) dell'ingombro di M visto lungo Y: e' dove punta la camera."""
    P = model_points(md)
    lo, hi = P.min(axis=0), P.max(axis=0)
    return (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2


def build_painting(image, md, depth, eye):
    """Il piano del quadro, a y = depth, scalato e spostato perche' il poliedro
    dipinto abbia l'altezza e il centro di M *come li vede la camera*: si
    confronta il riquadro dipinto con la proiezione di M sul piano del quadro.
    Restituisce (oggetto, centro, altezza) del piano."""
    w_px, h_px = image.size
    x0, y0, x1, y1 = PAINTING_MODEL_BOX
    Q = CAMERA.project_on_plane(model_points(md), eye, depth)
    lo, hi = Q.min(axis=0), Q.max(axis=0)
    cx, cz, height = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2, hi[2] - lo[2]
    k = height / (y1 - y0)                       # unita' mondo per pixel
    W, H = w_px * k, h_px * k
    # centro del piano: il centro del poliedro dipinto va sul centro di M
    px, pz = cx - ((x0 + x1) / 2 - w_px / 2) * k, cz + ((y0 + y1) / 2 - h_px / 2) * k

    mesh = bpy.data.meshes.new(KIT.name("painting"))
    mesh.from_pydata([(-W / 2, 0, -H / 2), (W / 2, 0, -H / 2),
                      (W / 2, 0, H / 2), (-W / 2, 0, H / 2)], [], [(0, 1, 2, 3)])
    layer = mesh.uv_layers.new(name="UVMap")
    for li, uv in zip(mesh.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
        layer.data[li].uv = uv
    mat = painting_material(image)
    mesh.materials.append(mat)
    obj = KIT.new_object("painting", mesh)
    obj.location = (px, depth, pz)
    m_scene.hide_from_light(obj)     # non deve fare ombra su M, ne' illuminarlo

    d0, d1 = beat("dissolvenza")
    bl_anim.key_value(mat.node_tree, 'nodes["Fade"].inputs[0].default_value',
                      [(d0, 1.0), (d1, 0.0)])
    bl_anim.key_visibility(obj, [(FRAME_START, True), (d1 + 1, False)])
    return obj, (px, pz), H


def build_camera(eye, painting_center, painting_depth, painting_height):
    """La camera, ferma in `eye` per tutto il video. Restituisce (camera,
    zoom iniziale); lo zoom e' ortho_scale o focale, si veda m_scene.CameraRig."""
    cam = CAMERA.build(KIT, eye, clip_end=CAMERA_DISTANCE + GRID_DEPTH + 10.0)

    # La camera sta ferma, centrata su M, dal quadro fino all'esplosione: il
    # confronto fra quadro e modello si fa a inquadratura immobile. Il quadro
    # non e' centrato su M (sotto c'e' la fascia scura), quindi l'altezza
    # dell'inquadratura si prende dal suo bordo piu' lontano dal centro di M.
    half = abs(painting_center[1] - eye.z) + painting_height / 2.0
    zoom = CAMERA.zoom_for_width(2.0 * half / PAINTING_FILL * CAMERA.aspect,
                                 painting_depth - eye.y)

    e0, e1 = beat("esplosione")
    bl_anim.key_value(cam.data, CAMERA.zoom_path, [
        (FRAME_START, zoom), (e0, zoom),
        (e0 + ZOOM_FRACTION * (e1 - e0), CAMERA.zoom_out(zoom, CAMERA_ZOOM_OUT)),
    ])
    return cam, zoom


def build_ico(orient, md):
    obj, scale = m_scene.build_ico(KIT, orient, md, ICO_MARGIN, ICO_COLOR)
    a0, a1 = beat("ico_entra")
    x0, x1 = beat("ico_esce")
    bl_anim.key_value(obj, m_scene.WIRE_THICKNESS_PATH, [
        (a0, 0.0), (a1, ICO_WIRE_THICKNESS), (x0, ICO_WIRE_THICKNESS), (x1, 0.0)])
    bl_anim.key_visibility(obj, [(FRAME_START, False), (a0, True), (x1 + 1, False)])
    return obj, scale


def build():
    report_hand_orientation()
    KIT.clear_previous_run()

    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    if USE_STANDARD_VIEW:
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'

    KIT.new_collection(scene)
    m_scene.setup_world(KIT, BACKGROUND_SRGB, AMBIENT)
    m_scene.build_light(KIT, LIGHT_DIRECTION, LIGHT_STRENGTH)

    md = extended_face.make_M()
    painting_img = KIT.load_image(PAINTING_FILE)
    face_img = KIT.load_image(FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, FACE_UV_PX, FACE_UV_INSET)
    face_mat = face_material(face_img, uvs)

    # --- perno e posa ---
    pivot = KIT.new_object("pivot")
    pivot.empty_display_size = 0.5
    bl_anim.apply_euler_keys(pivot, pivot_keys())
    orient = KIT.new_object("orient", parent=pivot)
    orient.empty_display_type = 'ARROWS'
    orient.rotation_euler = [math.radians(a) for a in ORIENT_EULER_DEG]
    orient_world = pivot_matrix_at_rest() @ orient_matrix()

    # --- l'icosaedro, e il quadro davanti a tutto ---
    ico, ico_scale = build_ico(orient, md)
    eye = CAMERA.location(model_frame(md))
    p_depth = -(ico_scale + 1.0)
    if eye.y >= p_depth - 1.0:
        raise ValueError(f"CAMERA_DISTANCE = {CAMERA_DISTANCE}: la camera dev'essere "
                         f"davanti al quadro, che sta a y = {p_depth:.2f}")
    painting, p_center, p_height = build_painting(painting_img, md, p_depth, eye)
    cam, zoom = build_camera(eye, p_center, p_depth, p_height)
    final_zoom = CAMERA.zoom_out(zoom, CAMERA_ZOOM_OUT)

    # --- M intera, e i 240 triangoli ---
    e0, e1 = beat("esplosione")
    if USE_MERGED_M:
        m_obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, face_mat, uvs), parent=orient)
        bl_utils.merge_by_distance(m_obj)
        bl_anim.key_visibility(m_obj, [(FRAME_START, True), (e0, False)])

    mesh = m_scene.triangle_mesh(KIT, face_mat, uvs)
    tris = [m_scene.Tri(p) for p in pieces.m_pieces(md)]
    frame_w = CAMERA.frame_width(final_zoom, GRID_DEPTH - eye.y)
    targets, world_targets, grid_scale = m_scene.grid_targets(
        tris, orient_world, (eye.x, eye.z), GRID, GRID_DEPTH,
        frame_w, frame_w / CAMERA.aspect, GRID_FILL)
    ranks = m_scene.fan_ranks(tris, orient_world)
    for tri, target in zip(tris, targets):
        obj = KIT.new_object(f"tri_{tri.piece.index:03d}", mesh, parent=orient)
        tri.obj = obj
        bl_anim.apply_keys(obj, explosion_keys(tri, target, ranks))
        if USE_MERGED_M:
            bl_anim.key_visibility(obj, [(FRAME_START, False), (e0, True)])

    # --- verifica: a fine esplosione i triangoli sono dove dovevano andare ---
    miss, tilt = m_scene.check_targets(tris, world_targets, scene, FRAME_END)
    scene.frame_set(FRAME_START)

    print(f"[M_video] frame {FRAME_START}-{FRAME_END} a {FPS} fps "
          f"({(FRAME_END - FRAME_START + 1) / FPS:.1f} s), {RESOLUTION[0]}x{RESOLUTION[1]}")
    print("[M_video] " + ", ".join(f"{n} {a}-{b}" for n, (a, b) in MARKS.items()))
    unit = "ortho_scale" if CAMERA_TYPE == 'ORTHO' else "focale (mm)"
    print(f"[M_video] posa ORIENT_EULER_DEG = {ORIENT_EULER_DEG}; quadro alto "
          f"{p_height:.3f}; camera {CAMERA_TYPE} a distanza {CAMERA_DISTANCE}, "
          f"{unit} {zoom:.3f} -> {final_zoom:.3f}")
    print(f"[M_video] gabbia a scala {ico_scale:.6f}; griglia "
          f"{GRID.group_cols}x{GRID.group_rows} gruppi da "
          f"{GRID.cols_per_group}x{GRID.rows_per_group}, triangoli scalati a {grid_scale:.3f}")
    print(f"[M_video] a fine esplosione: scarto di posizione {miss:.2e}, "
          f"di rotazione {tilt:.2e} gradi")
    return tris


TRIS = build()
