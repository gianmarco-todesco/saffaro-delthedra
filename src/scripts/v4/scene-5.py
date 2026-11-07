"""
v4/scene-5.py -- il quadro di Saffaro torna, con M che gira lentamente al
suo posto; poi, dopo un istante di buio, l'articolo (Scienza & Tecnica
87/88, "Nuovissime operazioni sui poliedri platonici"): il libro si apre a
V, si sfogliano due pagine e intanto arretra, e fra le sue due meta'
compaiono i cinque deltaedri di Saffaro di scene_5a.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0 - 1      compare (fade-in) il quadro senza il poliedro dipinto, e al suo
              posto M, coi colori del quadro: dalla camera combacia col
              dipinto. Da 1 M comincia a girare lentamente su se stesso
   6.5 - 7.3  il quadro e M svaniscono; un istante di buio
   7.5 - 8.2  compare il libro chiuso, la copertina al centro ("pubblica
              l'articolo", a 8 s)
   8.4 - 9.6  la copertina si apre, e il libro scivola a destra: le due
              meta' stanno al centro e non si stendono piatte, restano a V
              verso la camera (OPEN_ALPHA), con le pagine un po' incurvate.
              A sinistra l'interno della copertina, a destra la 323
   9.9 - 11.7 due giri in rapida successione: due fogli insieme (326 | 327)
              e uno (328 | 329); intanto il libro arretra sul pavimento, e la
              camera si alza un poco perche' resti tutto dentro
  11 - 12.5   si accende la luce calda, sopra lo spazio davanti al libro
  12          fra le due meta' compaiono, uno dopo l'altro, i cinque
              deltaedri di Saffaro di scene_5a, che girano su se stessi; la
              camera avanza piano
  18          fine

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* Camera, pavimento, sole e fondo sono quelli di v4/scene-2 e v4/scene-3:
  la camera dritta dove la lascia v4/scene-1, e il pavimento inclinato
  verso di lei, come se la guardasse dall'alto di CAMERA_ELEVATION gradi. I
  conti si fanno nel mondo 'virtuale' della camera alta (floor_frame).
* Il quadro e' quello di v4/scene-1 (story.AxisLayout) alla fine
  dell'arretramento della camera, che qui e' ferma li', ma senza il poliedro
  (PAINTING_FILE). M sta davanti al quadro (il quadro ora e' opaco dove
  c'era il poliedro): sull'asse della camera, alla scala per cui visto da
  lei combacia ancora col dipinto, e tanto avanti che girando non lo tocca
  (conta il raggio del cilindro verticale che lo contiene). Il pavimento
  sta all'altezza del bordo in basso del quadro, che cosi' ci e' appoggiato;
  il libro e i poliedri stanno sullo stesso pavimento.
* Il libro chiuso sta in piedi davanti alla camera, perpendicolare al suo asse
  (nel mondo virtuale e' inclinato all'indietro, come su un leggio), col
  bordo in basso sul pavimento; aperto e' alto BOOK_FILL dell'immagine. Il
  riferimento del libro (book): x a destra, y verso il fondo, z in alto, la
  costola sull'asse z.
* Non si mostrano tutte le pagine (TURNS): la copertina, sulla pagina col
  titolo, poi due giri rapidi fino a 328 | 329.
* Aperto, il libro non e' piatto: le due pile girano di OPEN_ALPHA verso la
  camera attorno alla costola (a destra -OPEN_ALPHA, a sinistra -(180 -
  OPEN_ALPHA)), e un foglio che gira va dall'una all'altra. Le pagine ferme
  restano incurvate di BEND_REST verso la camera.
* Le foto sono pagine vere: pari a sinistra, dispari a destra. Ogni foglio
  (SHEETS) ha un fronte e un retro: la copertina e il suo interno (carta
  bianca), 323 e 324, 325 e 326, ... e 331. Il materiale mostra il fronte o
  il retro secondo il lato della faccia che si vede (Geometry > Backfacing);
  le foto, di formati un po' diversi, si ritagliano tutte a PAGE_ASPECT.
* Un foglio gira attorno alla costola venendo verso la camera, da destra a
  sinistra, e mentre gira si piega di piu' (BEND_DEG, col seno), verso la
  camera: piegato all'indietro entrerebbe nella pila. La curvatura a riposo
  passa da quella della pagina destra a quella della sinistra. I fogli
  impilati stanno a STACK_GAP l'uno dall'altro, l'ultimo girato sopra;
  quelli che girano davanti a tutti (depth).
* I cinque deltaedri sono quelli di scene_5a (D, A, F, N, H: i nomi che
  Saffaro da' loro nella tabella dell'articolo), coi suoi colori, davanti
  al libro arretrato, fra le sue due meta', appoggiati sul pavimento
  (LAYOUT). La luce calda e' un punto luce sopra di loro, davanti alla
  costola: illumina l'interno delle pagine e i poliedri.
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).

Una sola scena, tutto in keyframe (nessun handler), script idempotente, nomi
col prefisso S5V4_.
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
        txt = bpy.data.texts.get("scene-5.py")
    if txt is None or not txt.filepath:
        raise RuntimeError(
            "non riesco a ricavare il path dello script: il testo non e' salvato "
            "su disco (Text > Save As) oppure e' un blocco 'interno'"
        )
    # attenzione: se il file e' stato aperto con l'opzione 'Relative Path' spuntata,
    # filepath e' del tipo '//../...' (relativo al .blend) e os.path lo interpreta
    # come percorso UNC. bpy.path.abspath lo risolve; sugli assoluti non fa nulla.
    path = os.path.abspath(bpy.path.abspath(txt.filepath))
    # script in src/scripts/v4, librerie in src/libs
    libs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(path))), "libs")
    if not os.path.isdir(libs):
        raise RuntimeError(f"cartella libs non trovata: {libs}  (filepath: {txt.filepath})")
    return libs


_LIBS = _find_libs_dir()
if _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender
import bl_utils, bl_anim, m_scene, story, extended_face, deltahedra
for _mod in (bl_utils, bl_anim, m_scene, story, extended_face, deltahedra):
    importlib.reload(_mod)

from mathutils import Vector, Matrix


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S5V4"
COLLECTION_NAME = "scene-5_v4"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO    = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR  = os.path.join(_SAFFARO, "assets")
PAGES_DIR   = os.path.join(ASSETS_DIR, "nuovissime")
SAFFARO_DIR = os.path.join(_SAFFARO, "modelli-3d", "saffaro-deltahedra")

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

# --- la scaletta, in secondi ---
PAINT_IN    = (0.0, 1.0)         # il quadro e M compaiono
SPIN_AT     = 1.0                # M comincia a girare...
SPIN_RAMP   = 1.5                # ... arrivando alla sua velocita' in tanto
SPIN_SECONDS_PER_TURN = 24.0
PAINT_OUT   = (6.5, 7.3)         # il quadro svanisce...
BOOK_IN     = (7.5, 8.2)         # ... un istante di buio, e compare il libro chiuso
# i giri: (fogli, inizio, fine). Il primo e' la copertina, e intanto il
# libro va al centro; i fogli girati insieme partono a BUNDLE_LAG l'uno
# dall'altro, come quando li si prende fra le dita
TURNS       = [((0,), 8.4, 9.6), ((1, 2), 9.9, 10.7), ((3,), 10.9, 11.7)]
BUNDLE_LAG  = 0.08
RETREAT     = (9.9, 12.0)         # il libro arretra...
RETREAT_H   = 1.5                # ... di tanto, in altezze della pagina
BOOK_TOP_FILL = 0.92             # e la camera si alza perche' la sua cima resti dentro tanto...
TILT_SMOOTH = 1.0                # ... lisciando su tanti secondi
WARM_ON     = (11.0, 12.5)       # la luce calda si accende
OTHERS_AT   = 12.0               # i cinque deltaedri compaiono...
OTHERS_GAP  = 0.3                # ... uno dopo l'altro...
OTHERS_GROW = 0.8                # ... ognuno in tanto
PUSH        = (12.0, 18.0)       # la camera avanza...
PUSH_FRACTION = 0.08             # ... di tanto della sua distanza dal libro
END         = 18.0
OTHER_SECONDS_PER_TURN = 10.0    # come in scene_5a

# --- il quadro ---
PAINTING_FILE = "quadro_senza_m.png"   # m.jpg senza il poliedro dipinto
M_AHEAD       = 0.05             # fra M che gira e il quadro

# --- il libro ---
# i fogli: (fronte, retro); None e' carta bianca
SHEETS = [("copertina", None), ("323", "324"), ("325", "326"), ("327", "328"), ("329", "330"),
          ("331", None)]
PAGE_ASPECT = 2.0 / 3.0          # larghezza / altezza della pagina
BOOK_FILL   = 0.85               # il libro aperto e' alto tanto dell'immagine
STACK_GAP   = 0.004              # fra due fogli impilati, in altezze della pagina
BEND_DEG    = 40.0               # quanto si piega in piu' una pagina a meta' giro
BEND_REST   = 15.0               # la curvatura delle pagine ferme
OPEN_ALPHA  = 25.0               # gradi: le due meta' del libro aperto, verso la camera
PAPER_SRGB  = (236, 232, 220)    # la carta senza foto
PAPER_ROUGHNESS = 0.85
PAPER_GLOW  = 0.7                # la carta e' soprattutto emissione...
PAPER_DIFFUSE = 0.4              # ... e un po' di luce: girando verso il sole, piena, saturerebbe
SEGMENTS    = 48                 # le suddivisioni della pagina in larghezza (per piegarla)

# --- i cinque deltaedri di scene_5a: (file, facce, tinta OKLCH) ---
OTHERS = [
    ("D.stl", 16,  20.0),        # salmone
    ("A.stl", 24, 150.0),        # verde menta
    ("F.stl", 48, 300.0),        # lilla
    ("N.stl", 72,  75.0),        # albicocca
    ("H.stl", 96, 345.0),        # rosa
]
PASTEL_L   = 0.82
PASTEL_C   = 0.085
ROUGHNESS  = 0.5
POLY_RADIUS  = 0.2               # circonraggio, in altezze della pagina
# dove stanno, nell'ordine di OTHERS: (a destra, davanti alla costola del
# libro arretrato), in altezze della pagina
LAYOUT = [(-0.72, 0.35), (-0.37, 0.7), (0.0, 0.85), (0.37, 0.7), (0.72, 0.35)]
CLEARANCE    = 0.05              # fra il pavimento e la sfera del pezzo, in altezze della pagina

# --- la luce calda ---
WARM_COLOR   = (1.0, 0.72, 0.42)
WARM_POWER   = 2500.0            # watt, accesa
WARM_AHEAD   = 0.4               # davanti alla costola, in altezze della pagina
WARM_HEIGHT  = 1.1
WARM_RADIUS  = 0.3

# --- il pavimento e la camera: come v4/scene-2 ---
FLOOR_SRGB       = (30, 38, 56)
FLOOR_ROUGHNESS  = 0.85
FLOOR_SPECULAR   = 0.05
FLOOR_SIZE       = 400.0
FLOOR_BELOW      = 2.2
SUN_SIZE_DEG     = 8.0
BACKGROUND_DEPTH = 300.0
CAMERA_ELEVATION = 24.0


# =============================================================================
# LA REGIA
# =============================================================================

FRAME_END = FRAME_START + int(round(END * FPS))


def frame_of(t):
    return FRAME_START + int(round(t * FPS))


def time_of(frame):
    return (frame - FRAME_START) / FPS


def ramp(t, t0, t1):
    return min(1.0, max(0.0, (t - t0) / (t1 - t0)))


def smoother(u):
    return u * u * u * (u * (6.0 * u - 15.0) + 10.0)


COVER_OPEN = TURNS[0][1:]


def turn_windows():
    """(inizio, fine) del giro di ogni foglio che si gira, in ordine."""
    out = []
    for sheets, t0, t1 in TURNS:
        for k, i in enumerate(sheets):
            if i != len(out):
                raise ValueError("TURNS deve girare i fogli in ordine")
            out.append((t0 + k * BUNDLE_LAG, t1 + k * BUNDLE_LAG))
    return out


class Basis:
    """Gli assi di una camera in `eye` che guarda `target` con l'orizzonte
    dritto: forward, right, up."""

    def __init__(self, eye, target):
        self.eye = np.asarray(eye, dtype=float)
        f = np.asarray(target, dtype=float) - self.eye
        self.f = f / np.linalg.norm(f)
        r = np.cross(self.f, [0.0, 0.0, 1.0])
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.r, self.f)


def orbit(target, back_h, elevation, distance):
    return target + (back_h * math.cos(elevation) + np.array([0.0, 0.0, math.sin(elevation)])) * distance


# =============================================================================
# LE PAGINE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


def crop_box(image):
    """(u0, v0, u1, v1): la parte centrale della foto col formato PAGE_ASPECT."""
    w, h = image.size
    a = w / h
    if a > PAGE_ASPECT:
        m = (1.0 - PAGE_ASPECT / a) / 2.0
        return m, 0.0, 1.0 - m, 1.0
    m = (1.0 - a / PAGE_ASPECT) / 2.0
    return 0.0, m, 1.0, 1.0 - m


def page_mesh(name, width, height, front_box, back_box):
    """Il foglio: un rettangolo suddiviso in larghezza, dalla costola (x = 0)
    al bordo (x = width), nel piano y = 0, la faccia davanti verso -y. Due UV:
    'front' (la foto del fronte, ritagliata) e 'back' (quella del retro,
    specchiata: si vede da dietro)."""
    verts, faces = [], []
    for i in range(SEGMENTS + 1):
        x = width * i / SEGMENTS
        verts += [(x, 0.0, 0.0), (x, 0.0, height)]
    for i in range(SEGMENTS):
        a, b, c, d = 2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1
        faces.append((a, b, c, d))          # normale verso -y
    mesh = bpy.data.meshes.new(KIT.name(name))
    mesh.from_pydata(verts, [], faces)
    for layer_name, box, mirror in (("front", front_box, False), ("back", back_box, True)):
        layer = mesh.uv_layers.new(name=layer_name)
        u0, v0, u1, v1 = box
        for poly in mesh.polygons:
            for li in poly.loop_indices:
                co = mesh.vertices[mesh.loops[li].vertex_index].co
                s = co.x / width
                if mirror:
                    s = 1.0 - s
                layer.data[li].uv = (u0 + (u1 - u0) * s, v0 + (v1 - v0) * co.z / height)
    mesh.update()
    return mesh


def side_color(nodes, links, image, uv_name):
    """Il colore di un lato: la foto sulla sua UV, o la carta bianca."""
    if image is None:
        rgb = nodes.new("ShaderNodeRGB")
        rgb.outputs[0].default_value = m_scene.linear_rgba(PAPER_SRGB)
        return rgb.outputs[0]
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = uv_name
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = 'EXTEND'
    links.new(uv.outputs["UV"], tex.inputs["Vector"])
    return tex.outputs["Color"]


def page_material(name, front, back):
    """Il fronte o il retro secondo il lato che si vede: emissione
    (PAPER_GLOW) piu' un po' di luce (il colore scurito a PAPER_DIFFUSE), cosi'
    la pagina che gira e' modellata dalla luce senza saturare; il nodo 'Fade'
    per la comparsa (parte da 1)."""
    mat, nodes, links = KIT.new_material(name)
    out = nodes.new("ShaderNodeOutputMaterial")
    geo = nodes.new("ShaderNodeNewGeometry")
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    links.new(geo.outputs["Backfacing"], mix.inputs[0])
    links.new(side_color(nodes, links, front, "front"), mix.inputs[6])
    links.new(side_color(nodes, links, back, "back"), mix.inputs[7])
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = PAPER_ROUGHNESS
    dim = nodes.new("ShaderNodeMix")
    dim.data_type = 'RGBA'
    dim.inputs[0].default_value = 1.0 - PAPER_DIFFUSE
    links.new(mix.outputs[2], dim.inputs[6])
    dim.inputs[7].default_value = (0.0, 0.0, 0.0, 1.0)
    links.new(dim.outputs[2], bsdf.inputs["Base Color"])
    links.new(mix.outputs[2], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = PAPER_GLOW
    clear = nodes.new("ShaderNodeBsdfTransparent")
    fade = nodes.new("ShaderNodeMixShader")
    fade.name = "Fade"
    fade.inputs["Fac"].default_value = 1.0
    links.new(clear.outputs["BSDF"], fade.inputs[1])
    links.new(bsdf.outputs["BSDF"], fade.inputs[2])
    links.new(fade.outputs["Shader"], out.inputs["Surface"])
    return mat


def load_page(key):
    return None if key is None else bpy.data.images.load(
        os.path.join(PAGES_DIR, f"nuovissime_{key}.png"), check_existing=True)


# =============================================================================
# COSTRUZIONE
# =============================================================================

def build():
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    m_scene.use_cycles(scene)
    scene.cycles.transparent_max_bounces = 32
    KIT.new_collection(scene)
    frames = list(range(FRAME_START, FRAME_END + 1))

    md = extended_face.make_M()
    painting_img = KIT.load_image(story.PAINTING_FILE)
    ev = story.ExitView(md, painting_img.size)
    rig = ev.layout.rig

    # --- la camera, il mondo del pavimento e il sole: come v4/scene-2 ---
    eye1, m_end, lens = np.asarray(ev.eye1), np.asarray(ev.m_end), ev.lens_m
    b1 = Basis(eye1, m_end)
    d0 = float(np.linalg.norm(m_end - eye1))
    cam = rig.build(KIT, Vector(eye1), clip_end=BACKGROUND_DEPTH + 20.0)
    cam.data.lens = lens
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = story.look_quat(m_end - eye1)
    back1 = (eye1 - m_end) / d0
    back_h = np.array([back1[0], back1[1], 0.0]) / math.hypot(back1[0], back1[1])
    floor_z = m_end[2] - FLOOR_BELOW
    target2 = np.array([m_end[0], m_end[1], floor_z + 1.0])
    eye2 = orbit(target2, back_h, math.radians(CAMERA_ELEVATION), d0)
    b2 = Basis(eye2, target2)
    R = np.column_stack([b1.r, b1.f, b1.u]) @ np.column_stack([b2.r, b2.f, b2.u]).T
    frame = KIT.new_object("floor_frame")
    frame.matrix_world = Matrix.Translation(Vector(eye1 - R @ eye2)) @ Matrix(R.tolist()).to_4x4()
    e = math.radians(story.SKY_SUN_ELEVATION)
    h = np.array([-story.LIGHT_DIRECTION[0], -story.LIGHT_DIRECTION[1], 0.0])
    sun = R @ (h / np.linalg.norm(h) * math.cos(e) + np.array([0.0, 0.0, math.sin(e)]))
    m_scene.build_background(KIT, rig, cam, lens, BACKGROUND_DEPTH,
                             story.BACKGROUND_CORNERS_SRGB, story.BACKGROUND_BLEED)
    m_scene.setup_sky_world(KIT, math.asin(sun[2]), m_scene.sky_rotation(sun), story.SKY_STRENGTH,
                            sun_size=math.radians(SUN_SIZE_DEG))

    # --- il quadro, senza il poliedro, dove sta alla fine di v4/scene-1 ---
    layout = ev.layout
    painting, p_mat = story.build_painting(KIT, KIT.load_image(PAINTING_FILE), layout)
    fade_in_out = [(frame_of(PAINT_IN[0]), 0.0), (frame_of(PAINT_IN[1]), 1.0),
                   (frame_of(PAINT_OUT[0]), 1.0), (frame_of(PAINT_OUT[1]), 0.0)]
    bl_anim.key_value(p_mat.node_tree, m_scene.FADE_PATH, fade_in_out)
    bl_anim.key_visibility(painting, [(FRAME_START, True), (frame_of(PAINT_OUT[1]) + 1, False)])
    # il pavimento all'altezza del bordo in basso del quadro (nel mondo
    # virtuale il bordo e' orizzontale: la x della camera vera e' orizzontale)
    px, pz = layout.painting_center
    bottom = frame.matrix_world.inverted() @ Vector((px, layout.painting_depth, pz - layout.painting_height / 2.0))
    floor_z = bottom.z
    floor = m_scene.build_floor(KIT, FLOOR_SRGB, FLOOR_ROUGHNESS, FLOOR_SPECULAR, FLOOR_SIZE)
    floor.parent = frame
    floor.location = (target2[0], target2[1], floor_z)

    # --- M, davanti al quadro, che combacia col dipinto e gira ---
    # la scala che combacia, col centro in y sull'asse: s(y) = (y - eye.y) / (0 - eye.y)
    # (AxisLayout e' fatto per M nell'origine a scala 1); il punto piu' avanti
    # di M girando (raggio del cilindro verticale rc) sta M_AHEAD davanti al quadro
    P = story.model_points(md)
    rc = float(np.linalg.norm(P[:, :2], axis=1).max())
    kk = -float(layout.eye.y)
    y_m = (layout.painting_depth - M_AHEAD - rc) / (1.0 + rc / kk)
    s_m = (y_m + kk) / kk
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    m_mat = story.face_material(KIT, face_img, uvs)          # Look 0: i colori del quadro
    bl_anim.key_value(m_mat.node_tree, m_scene.FADE_PATH, fade_in_out)
    mover = KIT.new_object("mover")
    mover.location = (0.0, y_m, 0.0)
    mover.scale = (s_m,) * 3
    orient = KIT.new_object("orient", parent=mover)
    orient.rotation_euler = [math.radians(a) for a in story.ORIENT_EULER_DEG]
    m_obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, m_mat, uvs), parent=orient)
    bl_utils.merge_by_distance(m_obj)
    m_obj.visible_shadow = False
    bl_anim.key_visibility(m_obj, [(FRAME_START, True), (frame_of(PAINT_OUT[1]) + 1, False)])
    omega = 2.0 * math.pi / SPIN_SECONDS_PER_TURN / FPS
    angle, keys = 0.0, []
    for f in range(FRAME_START, frame_of(PAINT_OUT[1]) + 1):
        keys.append((f, (0.0, 0.0, angle)))
        angle += omega * smoother(ramp(time_of(f) + 0.5 / FPS, SPIN_AT, SPIN_AT + SPIN_RAMP))
    mover.rotation_mode = 'XYZ'
    bl_anim.key_value(mover, "rotation_euler", keys, interpolation='LINEAR')

    # --- il libro: perpendicolare all'asse della camera, centrato
    # nell'immagine, alto BOOK_FILL, col bordo in basso sul pavimento ---
    tan_v = rig.frame_width(lens, 1.0) / rig.aspect / 2.0
    # il centro e' a distanza D lungo l'asse; l'altezza e' BOOK_FILL * 2 D tan_v;
    # il bordo in basso (centro - u H/2) sta alla quota del pavimento
    k = BOOK_FILL * tan_v
    D = (floor_z - eye2[2]) / (b2.f[2] - b2.u[2] * k)
    H = 2.0 * D * k
    W = H * PAGE_ASPECT
    origin = eye2 + b2.f * D - b2.u * (H / 2.0)              # la costola, in basso
    ahead_h = np.array([b2.f[0], b2.f[1], 0.0]) / math.hypot(b2.f[0], b2.f[1])
    final = origin + ahead_h * (RETREAT_H * H)               # la costola, arretrata
    book = KIT.new_object("book", parent=frame)
    book.matrix_parent_inverse = Matrix.Identity(4)
    basis = Matrix([list(b2.r), list(b2.f), list(b2.u)]).transposed()
    book.rotation_mode = 'QUATERNION'
    book.rotation_quaternion = basis.to_quaternion()
    # chiuso, la copertina (a destra della costola) al centro; aperto, la
    # costola; poi arretra sul pavimento
    bl_anim.key_value(book, "location",
                      [(f, tuple(origin - b2.r * (W / 2.0) * (1.0 - smoother(ramp(time_of(f), *COVER_OPEN)))
                                 + ahead_h * (RETREAT_H * H) * smoother(ramp(time_of(f), *RETREAT))))
                       for f in frames], interpolation='LINEAR')

    # --- i fogli ---
    windows = turn_windows()
    gap = STACK_GAP * H

    def state(j, t):
        if j >= len(windows) or t < windows[j][0]:
            return "right"
        return "turning" if t < windows[j][1] else "left"

    def depth(i, t):
        """Quanto il foglio i sta dietro il piano del libro. Quelli che girano
        stanno davanti a tutti (il primo del mazzo davanti), e la pila di
        destra resta dov'e' finche' il giro non e' finito: se avanzasse subito,
        vicino alla costola sarebbe nel piano del foglio che gira, e si
        vedrebbe a bande. Nelle pile, il primo foglio sta sul piano e gli
        altri dietro: a destra quelli con l'indice piu' basso sopra, a
        sinistra quelli girati per ultimi."""
        st = state(i, t)
        if st == "turning":
            return -gap * (1 + sum(1 for j in range(i + 1, len(SHEETS)) if state(j, t) == "turning"))
        if st == "right":
            return gap * sum(1 for j in range(i) if state(j, t) != "left")
        return gap * sum(1 for j in range(i + 1, len(SHEETS)) if state(j, t) == "left")

    def opening(t):
        """Di quanto le due meta' girano verso la camera: da 0 (chiuso) a
        OPEN_ALPHA, mentre si apre la copertina."""
        return math.radians(OPEN_ALPHA) * smoother(ramp(t, *COVER_OPEN))

    def pose(i, t):
        """(angolo attorno alla costola, piega) del foglio i: a destra
        -alpha, a sinistra -(180 - alpha); a riposo piegato di BEND_REST verso
        la camera (che per la pagina sinistra, girata, e' l'altro verso)."""
        a = opening(t)
        rest = math.radians(BEND_REST) * smoother(ramp(t, *COVER_OPEN))
        st = state(i, t)
        if st == "right":
            return -a, -rest
        if st == "left":
            return -(math.pi - a), rest
        t0, t1 = windows[i]
        u = ramp(t, t0, t1)
        w = smoother(u)
        return -(a + (math.pi - 2.0 * a) * w), -rest + 2.0 * rest * w - math.radians(BEND_DEG) * math.sin(math.pi * w)

    for i, (front_key, back_key) in enumerate(SHEETS):
        front, back = load_page(front_key), load_page(back_key)
        box_f = crop_box(front) if front else (0.0, 0.0, 1.0, 1.0)
        box_b = crop_box(back) if back else (0.0, 0.0, 1.0, 1.0)
        name = f"sheet_{i}"
        mesh = page_mesh(name, W, H, box_f, box_b)
        mat = page_material(name, front, back)
        mesh.materials.append(mat)
        obj = KIT.new_object(name, mesh, parent=book)
        obj.rotation_mode = 'XYZ'
        bend = obj.modifiers.new("Bend", 'SIMPLE_DEFORM')
        bend.deform_method = 'BEND'
        bend.deform_axis = 'Z'
        poses = [(f, pose(i, time_of(f))) for f in frames]
        bl_anim.key_value(obj, "location", [(f, (0.0, depth(i, time_of(f)), 0.0)) for f in frames],
                          interpolation='CONSTANT')
        bl_anim.key_value(obj, "rotation_euler", [(f, (0.0, 0.0, a)) for f, (a, _) in poses],
                          interpolation='LINEAR')
        bl_anim.key_value(obj, 'modifiers["Bend"].angle', [(f, b) for f, (_, b) in poses],
                          interpolation='LINEAR')
        # la comparsa: solo la copertina, gli altri fogli ci sono quando e' piena
        if i == 0:
            bl_anim.key_value(mat.node_tree, m_scene.FADE_PATH, [(frame_of(BOOK_IN[0]), 0.0),
                                                                 (frame_of(BOOK_IN[1]), 1.0)])
            bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(BOOK_IN[0]), True)])
        else:
            bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(BOOK_IN[1]), True)])

    # --- i cinque deltaedri, davanti al libro arretrato, sul pavimento ---
    r = POLY_RADIUS * H
    spin = 2.0 * math.pi / (OTHER_SECONDS_PER_TURN * FPS)
    for kk, (fname, n_faces, hue) in enumerate(OTHERS):
        V, faces = deltahedra.load_stl(os.path.join(SAFFARO_DIR, fname))
        if len(faces) != n_faces:
            raise ValueError(f"{fname}: {len(faces)} facce, non {n_faces}")
        V = V * (r / float(np.linalg.norm(V, axis=1).max()))
        color, _ = m_scene.oklch_to_linear(PASTEL_L, PASTEL_C, hue)
        name = os.path.splitext(fname)[0]
        mesh = bpy.data.meshes.new(KIT.name(name))
        mesh.from_pydata([tuple(v) for v in V], [], faces)
        mesh.materials.append(m_scene.wire_material(KIT, f"mat_{name}", color, roughness=ROUGHNESS))
        mesh.update()
        obj = KIT.new_object(name, mesh, parent=frame)
        side, front_of = LAYOUT[kk]
        q = final + b2.r * (side * H) - ahead_h * (front_of * H)
        q[2] = floor_z + r + CLEARANCE * H
        obj.location = tuple(q)
        t0 = OTHERS_AT + kk * OTHERS_GAP
        bl_anim.key_value(obj, "scale", [(frame_of(t0), (0.0,) * 3), (frame_of(t0 + OTHERS_GROW), (1.0,) * 3)])
        bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(t0) + 1, True)])
        obj.rotation_mode = 'XYZ'
        phase = 2.0 * math.pi * ((kk * 0.618034) % 1.0)
        bl_anim.key_value(obj, "rotation_euler", [(FRAME_START, (0.0, 0.0, phase)),
                                                  (FRAME_END, (0.0, 0.0, phase + spin * (FRAME_END - FRAME_START)))],
                          interpolation='LINEAR')

    # --- la luce calda, sopra lo spazio davanti alla costola ---
    light = bpy.data.lights.new(KIT.name("warm"), 'POINT')
    light.color = WARM_COLOR
    light.shadow_soft_size = WARM_RADIUS * H
    lamp = KIT.new_object("warm", light, parent=frame)
    q = final - ahead_h * (WARM_AHEAD * H)
    q[2] = floor_z + WARM_HEIGHT * H
    lamp.location = tuple(q)
    bl_anim.key_value(light, "energy", [(frame_of(WARM_ON[0]), 0.0), (frame_of(WARM_ON[1]), WARM_POWER)])

    # --- la camera: avanza alla fine, e si alza un poco quanto basta perche'
    # la cima del libro resti dentro BOOK_TOP_FILL della meta' altezza: aperto
    # a V le pagine vengono verso la camera, e sul pavimento inclinato,
    # allontanandosi, il libro sale nell'immagine. Il bisogno si calcola
    # fotogramma per fotogramma sugli spigoli in alto dei fogli fermi, poi si
    # allarga (il massimo nei dintorni) e si liscia (la media), cosi' resta
    # sempre sopra il bisogno e non segue gli scatti ---
    target = math.atan(BOOK_TOP_FILL * tan_v)

    def tilt_needed(t):
        a = opening(t)
        loc = (origin - b2.r * (W / 2.0) * (1.0 - smoother(ramp(t, *COVER_OPEN)))
               + ahead_h * (RETREAT_H * H) * smoother(ramp(t, *RETREAT)))
        eye = eye2 + b2.f * D * PUSH_FRACTION * smoother(ramp(t, *PUSH))
        worst = -math.pi
        for x, y in ((W * math.cos(a), -W * math.sin(a)), (-W * math.cos(a), -W * math.sin(a)), (0.0, 0.0)):
            v = loc + b2.r * x + b2.f * y + b2.u * H - eye
            worst = max(worst, math.atan2(v @ b2.u, v @ b2.f))
        return max(0.0, worst - target)

    need = [tilt_needed(time_of(f)) for f in frames]
    half = int(round(TILT_SMOOTH * FPS / 2.0))
    padded = [need[0]] * half + need + [need[-1]] * half
    wide = [max(padded[k:k + 2 * half + 1]) for k in range(len(need))]
    padded = [wide[0]] * half + wide + [wide[-1]] * half
    tilts = [sum(padded[k:k + 2 * half + 1]) / (2 * half + 1) for k in range(len(need))]
    q0 = cam.rotation_quaternion.copy()
    axis = Vector(b1.r)
    bl_anim.key_value(cam, "location",
                      [(f, tuple(eye1 + b1.f * D * PUSH_FRACTION * smoother(ramp(time_of(f), *PUSH))))
                       for f in range(frame_of(PUSH[0]), frame_of(PUSH[1]) + 1)],
                      interpolation='LINEAR')
    bl_anim.key_value(cam, "rotation_quaternion",
                      [(f, tuple(mathutils.Quaternion(axis, tl) @ q0)) for f, tl in zip(frames, tilts)],
                      interpolation='LINEAR')
    tilt = max(tilts)

    scene.frame_set(FRAME_START)
    print(f"[scene-5 v4] M davanti al quadro a y {y_m:.2f} (quadro a {layout.painting_depth:.2f}), "
          f"scala {s_m:.3f}; pavimento a z {floor_z:.2f} (virtuale); la camera si alza al massimo di "
          f"{math.degrees(tilt):.1f} gradi")
    print(f"[scene-5 v4] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END:.0f} s); pagina "
          f"{W:.2f} x {H:.2f}, il libro a {D:.2f} dalla camera; giri: "
          + ", ".join(f"{a:.1f}-{b:.1f}" for a, b in windows))


build()
