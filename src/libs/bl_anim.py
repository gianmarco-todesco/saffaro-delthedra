"""
bl_anim.py -- keyframe e interpolazioni, il lato Blender di `pieces`.

Tutto quello che serve per animare dei pezzi rigidi scrivendo i keyframe una
volta sola, quando lo script gira: niente handler di fotogramma, quindi Render
Animation e `blender -b -a` funzionano.

NB: richiede `bpy` e `mathutils` -> eseguibile solo dentro Blender, come
`bl_utils`.
"""

import bpy
import mathutils


# =============================================================================
# FCURVE E INTERPOLAZIONE
# =============================================================================

def action_fcurves(datablock):
    """Le fcurve dell'azione di un datablock (oggetto, dati della camera,
    node tree di un materiale...).

    Da Blender 4.4 le fcurve stanno nei channelbag degli strip dei layer, e da
    5.0 `action.fcurves` non c'e' piu': si prova prima la via vecchia, per le
    versioni che ce l'hanno, e poi si scende nei layer."""
    anim = getattr(datablock, "animation_data", None)
    if anim is None or anim.action is None:
        return []
    action = anim.action
    fcurves = list(getattr(action, "fcurves", []))
    if fcurves:
        return fcurves
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                fcurves.extend(bag.fcurves)
    return fcurves


def set_interpolation(datablock, interpolation='BEZIER', data_paths=None):
    """Forza l'interpolazione dei keyframe del datablock, su tutte le fcurve o
    solo su quelle il cui data_path sta in `data_paths`.

    Non e' cosmesi: l'interpolazione dei keyframe nuovi dipende dalle
    preferenze dell'utente (Edit > Preferences > Animation > Default
    Interpolation), quindi senza questo passaggio lo stesso script darebbe
    animazioni diverse su macchine diverse. Con BEZIER le maniglie sono
    AUTO_CLAMPED, che garantisce che un tratto fermo fra due keyframe uguali
    resti davvero fermo, senza sbordare."""
    for fcurve in action_fcurves(datablock):
        if data_paths is not None and fcurve.data_path not in data_paths:
            continue
        for point in fcurve.keyframe_points:
            point.interpolation = interpolation
            if interpolation == 'BEZIER':
                point.handle_left_type = 'AUTO_CLAMPED'
                point.handle_right_type = 'AUTO_CLAMPED'
        fcurve.update()


# =============================================================================
# POSE E KEYFRAME
# =============================================================================

def pose_from_matrix(matrix):
    """(location, rotation_quaternion) di una matrice 4x4 rigida, numpy o
    mathutils. La scala che decompose() restituisce si scarta: per una matrice
    rigida e' 1 a meno della singola precisione di mathutils."""
    m4 = mathutils.Matrix([[float(x) for x in row] for row in matrix])
    loc, quat, _ = m4.decompose()
    return loc, quat


class Key:
    """Un keyframe: frame + posa (posizione, rotazione e, facoltativa, scala).

    rotation e' un mathutils.Quaternion. Per costruirne uno comodamente:
        mathutils.Quaternion()                              # identita'
        mathutils.Quaternion((0, 0, 1), math.radians(90))   # asse, angolo
        mathutils.Euler((0, 0, math.radians(90))).to_quaternion()

    scale e' un numero (scala uniforme) o None: con None la scala non viene
    keyframata affatto, ed e' quello che vuole chi non la usa.
    """

    __slots__ = ("frame", "location", "rotation", "scale")

    def __init__(self, frame, location, rotation, scale=None):
        self.frame = int(round(frame))
        self.location = mathutils.Vector(location)
        self.rotation = mathutils.Quaternion(rotation)
        self.scale = None if scale is None else float(scale)


POSE_PATHS = ("location", "rotation_quaternion", "scale")


def apply_keys(obj, keys):
    """Mette i keyframe di `keys` su location e rotation_quaternion di obj (e
    sulla scala, per le chiavi che ne hanno una).

    I quaternioni vengono resi "compatibili" a catena: se il prodotto scalare
    col precedente e' negativo si cambia segno. q e -q sono la stessa
    rotazione, ma Blender interpola le quattro componenti una per una, e senza
    questa correzione il pezzo prenderebbe la strada lunga, girando su se'
    stesso di quasi 360 gradi.

    L'interpolazione viene forzata a BEZIER solo sui canali della posa, cosi'
    gli altri keyframe dell'oggetto (la visibilita', per esempio) restano come
    sono.
    """
    obj.rotation_mode = 'QUATERNION'

    previous = None
    for key in keys:
        quat = key.rotation.copy()
        if previous is not None and quat.dot(previous) < 0.0:
            quat.negate()
        previous = quat

        obj.location = key.location
        obj.rotation_quaternion = quat
        obj.keyframe_insert("location", frame=key.frame)
        obj.keyframe_insert("rotation_quaternion", frame=key.frame)
        if key.scale is not None:
            obj.scale = (key.scale,) * 3
            obj.keyframe_insert("scale", frame=key.frame)

    set_interpolation(obj, 'BEZIER', POSE_PATHS)


def apply_euler_keys(obj, keys):
    """Anima rotation_euler di obj con una lista di (frame, (x, y, z)).

    Eulero e non quaternioni perche' un quaternione non sa rappresentare piu'
    di mezzo giro per segmento: gli angoli di Eulero sono numeri che crescono,
    e 2 pi greco e' un giro. Interpolazione BEZIER: ogni tratto parte da
    fermo e si ferma, che e' l'ease in/out.

    L'animazione dell'oggetto viene azzerata a ogni chiamata: tenere i
    keyframe della corsa precedente vorrebbe dire che, cambiando i tempi, i
    vecchi restano appesi ai frame che il nuovo disegno non tocca piu'. E'
    pensata per un empty che fa solo da perno."""
    obj.animation_data_clear()
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = (0.0, 0.0, 0.0)
    for frame, angles in keys:
        obj.rotation_euler = angles
        obj.keyframe_insert("rotation_euler", frame=int(round(frame)))
    set_interpolation(obj, 'BEZIER', ("rotation_euler",))


def key_visibility(obj, changes):
    """Visibilita' a gradini: `changes` e' una lista di (frame, visibile).

    Si keyframano hide_render e hide_viewport insieme, cosi' quello che si vede
    nella vista e' quello che esce dal render. Interpolazione CONSTANT, che per
    un booleano e' l'unica sensata.

    Attenzione: a differenza della scala, la visibilita' non si eredita dai
    figli. Va messa su ogni oggetto."""
    for frame, visible in changes:
        obj.hide_render = not visible
        obj.hide_viewport = not visible
        obj.keyframe_insert("hide_render", frame=int(round(frame)))
        obj.keyframe_insert("hide_viewport", frame=int(round(frame)))
    set_interpolation(obj, 'CONSTANT', ("hide_render", "hide_viewport"))


def key_value(datablock, data_path, keys, interpolation='BEZIER'):
    """Keyframe di una proprieta' scalare qualsiasi del datablock: `keys` e'
    una lista di (frame, valore), `data_path` e' relativo al datablock, per
    esempio 'ortho_scale' sui dati di una camera, 'modifiers["Wireframe"].thickness'
    su un oggetto, 'nodes["Mix"].inputs[0].default_value' su un node tree."""
    for frame, value in keys:
        datablock.path_resolve(data_path)            # errore chiaro se il path e' sbagliato
        _assign(datablock, data_path, value)
        datablock.keyframe_insert(data_path, frame=int(round(frame)))
    set_interpolation(datablock, interpolation, (data_path,))


def _assign(datablock, data_path, value):
    """datablock.<data_path> = value, per un data_path con indici e chiavi."""
    head, _, attr = data_path.rpartition(".")
    owner = datablock.path_resolve(head) if head else datablock
    setattr(owner, attr, value)
