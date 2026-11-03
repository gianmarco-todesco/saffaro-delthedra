"""
v3/scene1b.py -- M esce dal quadro col contorno della sezione che brilla,
visto di lato; poi gira su se stesso, la camera lo porta al centro e il
quadro svanisce.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0 - 2.5    il quadro, fermo, dalla camera di scene1a (asse lungo y, per il
              centro di M). M c'e' gia', coi colori del quadro, subito dietro
              il quadro, che lo nasconde
   2.5        la camera comincia a girare di lato (SIDE_ANGLE) e un po' in
              alto (ELEVATION): la direzione di vista non e' piu' lungo y.
              Si ferma quando il centro di M passa per il piano del quadro
   3 - 7      M esce dal quadro con un solo movimento (ease in/out): viene
              avanti e un po' a sinistra, e si ferma davanti, distinto dal
              quadro. Intanto il contorno della sezione -- dove la superficie
              di M incontra il piano del quadro -- brilla d'oro
   7 -        M comincia a girare lentamente su se stesso; la camera, ferma
              dov'e', si gira piano verso di lui e lo porta al centro (fino a
              12), e intanto il quadro svanisce (7 - 9)
  13          fine

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* La partenza e' quella di scene1a: la camera di story.AxisLayout, M alla
  scala per cui, subito dietro il quadro, visto dalla camera e' identico al
  poliedro dipinto. Quella scala poi resta: venendo avanti M si ingrandisce.
* Il quadro non si muove. Dalla camera laterale (SIDE_ANGLE, ELEVATION, a
  DISTANCE dal punto fra la posizione finale di M e il quadro, con la
  focale che fa entrare tutti e due in FRAME_FILL) M e il quadro, alla fine,
  sono distinti: oltre a venire avanti (fra il retro di M e il quadro resta
  FINAL_GAP) M va di lato quanto basta perche' fra i due resti SCREEN_GAP
  della larghezza dell'immagine. Alla fine la camera, sempre dov'e', si gira
  verso M e la focale lo porta a occupare M_FILL dell'immagine.
* M esiste solo davanti al quadro: nel materiale, la parte che sta dietro il
  piano del quadro e' trasparente. Da davanti non cambia niente (il quadro la
  coprirebbe), e visto di lato M non spunta dai bordi del quadro, ed esce
  davvero dalla sua superficie. L'apertura della sezione guarda il retro del
  quadro, e la camera sta sempre davanti: non si vede mai.
* Il contorno della sezione e' una linea vera: a ogni fotogramma lo script
  calcola le curve chiuse in cui il piano del quadro taglia la superficie di
  M (deltahedra.plane_section, sulla mesh nella posa di quel fotogramma) e ne
  fa un tubicino sottile (LINE_RADIUS) di luce dorata (GLOW_COLOR,
  LINE_STRENGTH), visibile solo in quel fotogramma. Non illumina la scena e
  non fa ombra. Il bagliore attorno lo fa il compositor (m_scene.setup_glare),
  che fa brillare solo cio' che supera GLARE_THRESHOLD: la linea, non il
  quadro ne' M.
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).

Una sola scena, tutto in keyframe (nessun handler), script idempotente, nomi
col prefisso S1BV3_.
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
        txt = bpy.data.texts.get("scene1b.py")
    if txt is None or not txt.filepath:
        raise RuntimeError(
            "non riesco a ricavare il path dello script: il testo non e' salvato "
            "su disco (Text > Save As) oppure e' un blocco 'interno'"
        )
    # attenzione: se il file e' stato aperto con l'opzione 'Relative Path' spuntata,
    # filepath e' del tipo '//../...' (relativo al .blend) e os.path lo interpreta
    # come percorso UNC. bpy.path.abspath lo risolve; sugli assoluti non fa nulla.
    path = os.path.abspath(bpy.path.abspath(txt.filepath))
    # script in src/scripts/v3, librerie in src/libs
    libs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(path))), "libs")
    if not os.path.isdir(libs):
        raise RuntimeError(f"cartella libs non trovata: {libs}  (filepath: {txt.filepath})")
    return libs


_LIBS = _find_libs_dir()
if _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender
import geometry, bl_utils, extended_face, bl_anim, m_scene, story, deltahedra
for _mod in (geometry, bl_utils, extended_face, bl_anim, m_scene, story, deltahedra):
    importlib.reload(_mod)

from mathutils import Vector


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S1BV3"
COLLECTION_NAME = "scene1b_v3"

# saffaro/assets, accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_LIBS))), "assets")

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

# --- la scaletta, in secondi ---
MOVE        = (3.0, 7.0)         # M esce dal quadro, con un solo ease in/out
CAMERA_LEAD = 0.5                # la camera va di lato da tanto prima di MOVE fino a quando
                                 # il centro di M passa per il piano del quadro
SPIN_RAMP   = 1.5                # quando M si ferma comincia a girare, arrivando alla
                                 # sua velocita' in tanto
SPIN_SECONDS_PER_TURN = 20.0
PAINT_FADE  = (7.0, 9.0)         # il quadro svanisce
FOCUS       = (7.0, 12.0)        # la camera si gira verso M e lo porta al centro
END         = 13.0

# --- le posizioni ---
CROSS_MARGIN = 0.05              # all'inizio M e' subito dietro il quadro
FINAL_GAP    = 1.0               # alla fine, fra il retro di M e il quadro
SCREEN_GAP   = 0.05              # alla fine, fra M e il quadro nell'immagine (frazione della larghezza)

# --- la camera di lato ---
SIDE_ANGLE  = 35.0               # gradi attorno alla verticale (verso destra)
ELEVATION   = 8.0                # gradi in alto
DISTANCE    = 14.0               # dal punto che guarda
FRAME_FILL  = 0.85               # quanta immagine occupano M e il quadro
M_FILL      = 0.7                # alla fine, quanta ne occupa M

# --- il contorno della sezione ---
GLOW_COLOR      = (1.0, 0.78, 0.35)
LINE_RADIUS     = 0.007          # il tubicino della linea (circa 3 pixel di diametro)
LINE_STRENGTH   = 30.0           # quanto brilla
GLARE_THRESHOLD = 1.0
GLARE_STRENGTH  = 1.2
GLARE_SIZE      = 0.7


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


def smootherstep(x, x0, x1):
    return smoother(ramp(x, x0, x1))


def spin_angles(frames):
    """{frame: angolo}: dalla fine di MOVE la velocita' sale da zero con un
    raccordo dolce in SPIN_RAMP secondi, poi resta costante; integrata
    fotogramma per fotogramma."""
    omega = 2.0 * math.pi / SPIN_SECONDS_PER_TURN
    out, a = {}, 0.0
    for f in frames:
        out[f] = a
        a += omega * smootherstep(time_of(f) + 0.5 / FPS, MOVE[1], MOVE[1] + SPIN_RAMP) / FPS
    return out


# =============================================================================
# LA CAMERA
# =============================================================================

def look_quat(direction):
    return Vector(direction).normalized().to_track_quat('-Z', 'Y')


def camera_back(side_deg, elevation_deg):
    """Dal punto guardato verso la camera: (0, -1, 0) con angoli nulli."""
    a, e = math.radians(side_deg), math.radians(elevation_deg)
    return np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])


def lens_to_fit(rig, eye, target, points, fill):
    """La focale per cui i punti, visti da `eye` che guarda `target`,
    occupano `fill` dell'immagine nella dimensione che arriva prima al
    bordo."""
    f = (target - eye) / np.linalg.norm(target - eye)
    r = np.cross(f, [0.0, 0.0, 1.0])
    r = r / np.linalg.norm(r)
    u = np.cross(r, f)
    v = np.asarray(points) - eye
    depth = v @ f
    x, y = (v @ r) / depth, (v @ u) / depth
    tan_half = max(np.abs(x).max(), np.abs(y).max() * rig.aspect) / fill
    return rig.sensor_width / 2.0 / tan_half


def screen_box(eye, target, points):
    """Il rettangolo che i punti occupano nell'immagine, in tangenti
    dell'angolo dall'asse: (xmin, xmax, ymin, ymax)."""
    f = (target - eye) / np.linalg.norm(target - eye)
    r = np.cross(f, [0.0, 0.0, 1.0])
    r = r / np.linalg.norm(r)
    u = np.cross(r, f)
    v = np.asarray(points) - eye
    depth = v @ f
    x, y = (v @ r) / depth, (v @ u) / depth
    return x.min(), x.max(), y.min(), y.max()


def side_view(layout, m_points, m_y):
    """La camera laterale: di quanto M va di lato (verso -x), il punto
    guardato, la camera e la focale. Lo spostamento cresce a passi di 5 cm
    finche' fra M e il quadro (fermo) resta SCREEN_GAP della larghezza
    dell'immagine. `m_points` sono i punti di M attorno al suo centro."""
    px, pz = layout.painting_center
    hw, hh = layout.painting_width / 2.0, layout.painting_height / 2.0
    p_centre = np.array([px, layout.painting_depth, pz])
    corners = [p_centre + np.array([sx * hw, 0.0, sz * hh]) for sx in (-1, 1) for sz in (-1, 1)]
    side = 0.0
    while True:
        m_end = np.array([-side, m_y, 0.0])
        target = (m_end + p_centre) / 2.0
        eye = target + camera_back(SIDE_ANGLE, ELEVATION) * DISTANCE
        pts = [m_end + q for q in m_points]
        lens = lens_to_fit(layout.rig, eye, target, corners + pts, FRAME_FILL)
        tan_half = layout.rig.sensor_width / 2.0 / lens
        gap = (screen_box(eye, target, corners)[0] - screen_box(eye, target, pts)[1]) / (2.0 * tan_half)
        if gap >= SCREEN_GAP:
            return side, target, eye, lens
        side += 0.05
        if side > 20.0:
            raise ValueError("non riesco a separare M dal quadro")


# =============================================================================
# IL CONTORNO DELLA SEZIONE
# =============================================================================

def add_section_cut(mat, plane_y):
    """Rende trasparente, nel materiale, tutto quello che sta dietro il piano
    y = plane_y."""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    out = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
    surface = out.inputs["Surface"].links[0].from_socket
    geo = nodes.new("ShaderNodeNewGeometry")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geo.outputs["Position"], sep.inputs[0])
    behind = nodes.new("ShaderNodeMath")
    behind.operation = 'GREATER_THAN'
    links.new(sep.outputs["Y"], behind.inputs[0])
    behind.inputs[1].default_value = plane_y
    clear = nodes.new("ShaderNodeBsdfTransparent")
    cut = nodes.new("ShaderNodeMixShader")
    links.new(behind.outputs[0], cut.inputs["Fac"])
    links.new(surface, cut.inputs[1])
    links.new(clear.outputs["BSDF"], cut.inputs[2])
    links.new(cut.outputs["Shader"], out.inputs["Surface"])


def line_material():
    mat, nodes, links = KIT.new_material("section")
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = tuple(GLOW_COLOR) + (1.0,)
    emit.inputs["Strength"].default_value = LINE_STRENGTH
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    mat.diffuse_color = tuple(GLOW_COLOR) + (1.0,)
    return mat


def build_section_lines(md, P, frames, m_loc, m_spin, scale, plane_y):
    """Le linee della sezione: per ogni fotogramma in cui il piano del quadro
    taglia M, un oggetto curva coi tubicini delle curve chiuse, visibile solo
    in quel fotogramma. Restituisce i fotogrammi che ne hanno una."""
    mat = line_material()
    out = []
    for f, loc, a in zip(frames, m_loc, m_spin):
        c, sn = math.cos(a), math.sin(a)
        Rz = np.array([[c, -sn, 0.0], [sn, c, 0.0], [0.0, 0.0, 1.0]])
        W = np.asarray(loc) + scale * (P @ Rz.T)
        loops = deltahedra.plane_section(W, md.faces, axis=1, value=plane_y)
        if not loops:
            continue
        name = f"section_{f:04d}"
        curve = bpy.data.curves.new(KIT.name(name), 'CURVE')
        curve.dimensions = '3D'
        curve.bevel_depth = LINE_RADIUS
        curve.bevel_resolution = 2
        curve.fill_mode = 'FULL'
        for loop in loops:
            spline = curve.splines.new('POLY')
            spline.points.add(len(loop) - 1)
            for point, q in zip(spline.points, loop):
                point.co = (q[0], q[1], q[2], 1.0)
            spline.use_cyclic_u = True
        curve.materials.append(mat)
        obj = KIT.new_object(name, curve)
        m_scene.hide_from_light(obj)
        bl_anim.key_visibility(obj, [(FRAME_START, False), (f, True), (f + 1, False)])
        out.append(f)
    return out


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


def build():
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    m_scene.use_cycles(scene)
    KIT.new_collection(scene)
    frames = list(range(FRAME_START, FRAME_END + 1))

    md = extended_face.make_M()
    painting_img = KIT.load_image(story.PAINTING_FILE)
    layout = story.AxisLayout(md, painting_img.size)
    cam = story.build_camera_and_world(KIT, layout, clip_end=story.CAMERA_DISTANCE + story.GRID_DEPTH + 40.0)
    painting, p_mat = story.build_painting(KIT, painting_img, layout)
    bl_anim.key_value(p_mat.node_tree, m_scene.FADE_PATH,
                      [(frame_of(PAINT_FADE[0]), 1.0), (frame_of(PAINT_FADE[1]), 0.0)])
    bl_anim.key_visibility(painting, [(FRAME_START, True), (frame_of(PAINT_FADE[1]) + 1, False)])
    m_scene.setup_glare(KIT, scene, GLARE_THRESHOLD, GLARE_STRENGTH, GLARE_SIZE)
    plane = layout.painting_depth

    # --- M: mover (posizione, scala, giro) -> orient (la posa del quadro) -> M ---
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    m_mat = story.face_material(KIT, face_img, uvs)          # Look 0: i colori del quadro
    add_section_cut(m_mat, plane)
    mover = KIT.new_object("mover")
    mover.empty_display_size = 0.5
    orient = KIT.new_object("orient", parent=mover)
    orient.rotation_euler = [math.radians(a) for a in story.ORIENT_EULER_DEG]
    m_obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, m_mat, uvs), parent=orient)
    bl_utils.merge_by_distance(m_obj)
    m_obj.visible_shadow = False

    # --- il movimento: da subito dietro il quadro, alla scala del dipinto, a
    # davanti e di lato, con un solo ease in/out ---
    P = story.model_points(md)
    eye0 = np.asarray(layout.eye)
    ymin, ymax = P[:, 1].min(), P[:, 1].max()
    # il punto piu' vicino di M a CROSS_MARGIN dietro il piano: y + s(y) ymin, con
    # s(y) = (y - eye.y) / (0 - eye.y), e' lineare in y
    k = -eye0[1]
    y0 = (plane + CROSS_MARGIN - ymin) / (1.0 + ymin / k)
    s0 = (y0 + k) / k
    y1 = plane - FINAL_GAP - s0 * ymax
    # i punti di M per inquadrarlo qualunque sia la sua rotazione: la sfera
    radius = s0 * float(np.linalg.norm(P, axis=1).max())
    sphere = [radius * np.array(v) for v in
              ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    side, target1, eye1, lens1 = side_view(layout, sphere, y1)
    w_move = [smootherstep(time_of(f), *MOVE) for f in frames]
    m_loc = [(-side * w, y0 + (y1 - y0) * w, 0.0) for w in w_move]
    spin = spin_angles(frames)
    bl_anim.key_value(mover, "location", [(f, loc) for f, loc in zip(frames, m_loc)],
                      interpolation='LINEAR')
    mover.scale = (s0,) * 3
    bl_anim.key_value(mover, "rotation_euler", [(f, (0.0, 0.0, spin[f])) for f in frames],
                      interpolation='LINEAR')
    lit = build_section_lines(md, P, frames, m_loc, [spin[f] for f in frames], s0, plane)

    # --- la camera: di lato, finche' il centro di M passa per il quadro;
    # ferma; poi si gira verso M e lo porta al centro ---
    t_center = next(time_of(f) for f, loc in zip(frames, m_loc) if loc[1] <= plane)
    camera_move = (MOVE[0] - CAMERA_LEAD, t_center)
    m_end = np.array([-side, y1, 0.0])
    lens_m = lens_to_fit(layout.rig, eye1, m_end, [m_end + q for q in sphere], M_FILL)
    target0 = eye0 + np.array([0.0, DISTANCE, 0.0])
    cam.rotation_mode = 'QUATERNION'
    keys_loc, keys_rot, keys_lens = [], [], []
    for f in frames:
        t = time_of(f)
        w = smootherstep(t, *camera_move)
        target = target0 + (target1 - target0) * w
        eye = target + camera_back(SIDE_ANGLE * w, ELEVATION * w) * DISTANCE
        lens = layout.lens + (lens1 - layout.lens) * w
        # alla fine: la camera resta dov'e', guarda via via M e stringe su di lui
        z = smootherstep(t, *FOCUS)
        target = target + (m_end - target1) * z
        lens = lens + (lens_m - lens1) * z
        keys_loc.append((f, tuple(eye)))
        keys_rot.append((f, tuple(look_quat(target - eye))))
        keys_lens.append((f, lens))
    bl_anim.key_value(cam, "location", keys_loc, interpolation='LINEAR')
    bl_anim.key_value(cam, "rotation_quaternion", keys_rot, interpolation='LINEAR')
    bl_anim.key_value(cam.data, "lens", keys_lens, interpolation='LINEAR')

    scene.frame_set(FRAME_START)
    print(f"[scene1b v3] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END:.0f} s)")
    print(f"[scene1b v3] M alla scala {s0:.3f}: da y = {y0:.3f} a y = {y1:.3f}, e {side:.2f} di lato, "
          f"fra {MOVE[0]} e {MOVE[1]} s; il quadro fermo a y = {plane:.3f}")
    print(f"[scene1b v3] la linea della sezione c'e' da {time_of(lit[0]):.2f} a {time_of(lit[-1]):.2f} s "
          f"({len(lit)} fotogrammi)")
    print(f"[scene1b v3] camera: di lato fra {camera_move[0]:.2f} e {camera_move[1]:.2f} s (il centro "
          f"di M passa per il quadro), focale da {layout.lens:.1f} a {lens1:.1f} mm; fra {FOCUS[0]} e "
          f"{FOCUS[1]} s si gira verso M, focale {lens_m:.1f} mm")


build()
