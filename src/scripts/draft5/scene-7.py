import bpy
import math
import os
from mathutils import Vector, Matrix


# ==========================================
# PULIZIA COMPLETA DELLA SCENA
# ==========================================

# Elimina tutti gli oggetti
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Elimina tutte le collection non predefinite
for collection in list(bpy.data.collections):
    if collection.name != "Collection":
        bpy.data.collections.remove(collection)

print("Scena completamente pulita!")



def fcurves_of(obj):
    """Le F-Curve dell'azione di `obj`, o None se non e' animato.

    Da Blender 4.4 le azioni sono 'a slot': le curve non stanno piu' in
    action.fcurves (in 5.x l'attributo non c'e' piu') ma nel channelbag dello
    slot assegnato all'oggetto. Funziona con tutt'e due le versioni; la
    collezione restituita ha anche .remove()."""
    ad = obj.animation_data
    if ad is None or ad.action is None:
        return None
    action = ad.action
    try:
        from bpy_extras.anim_utils import action_get_channelbag_for_slot
    except ImportError:                      # Blender prima della 4.4
        return action.fcurves
    channelbag = action_get_channelbag_for_slot(action, ad.action_slot)
    return None if channelbag is None else channelbag.fcurves


def _script_path():
    """Il percorso di questo script su disco. __file__ non funziona dallo
    script editor di Blender: si prende il file del testo attivo, o del testo
    'scene-7.py' (come fanno gli altri script di draft5)."""
    txt = getattr(getattr(bpy.context, "space_data", None), "text", None)
    if txt is None:
        txt = bpy.data.texts.get("scene-7.py")
    if txt is not None and txt.filepath:
        # bpy.path.abspath risolve i percorsi relativi al .blend ('//...')
        return os.path.abspath(bpy.path.abspath(txt.filepath))
    if "__file__" in globals():                  # lanciato con --python
        return os.path.abspath(__file__)
    raise RuntimeError(
        "non riesco a ricavare il percorso dello script: il testo non e' "
        "salvato su disco (Text > Save As) oppure e' un blocco 'interno'"
    )


# gli asset stanno in saffaro/assets, accanto al repository:
# draft5 -> scripts -> src -> saffaro-delthedra -> saffaro
_SAFFARO = _script_path()
for _ in range(5):
    _SAFFARO = os.path.dirname(_SAFFARO)
asset_path = os.path.join(_SAFFARO, "assets")
if not os.path.isdir(asset_path):
    raise RuntimeError(f"cartella degli asset non trovata: {asset_path}")


# ==========================================
# CONFIGURAZIONE
# ==========================================

scene = bpy.context.scene

scene.frame_start = 1
scene.frame_end = 750

# ==========================================
# PULIZIA OGGETTI PRECEDENTI
# ==========================================

objects_to_remove = [
    "Camera",
    "empty_camera",
    "camera_tracker",
    "luce_sole",
    "luce_dipinto"
]

for name in objects_to_remove:
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
        


# ==========================================
# LUCE SPOT - LUCE_DIPINTO
# ==========================================

spot_data = bpy.data.lights.new(
    name="luce_dipinto",
    type='SPOT'
)

spot_data.energy = 1000

# Impostazioni fascio luminoso
spot_data.spot_size = math.radians(45)
spot_data.spot_blend = 0.15

spot = bpy.data.objects.new(
    "luce_dipinto",
    spot_data
)

scene.collection.objects.link(spot)

spot.location = (-4.9, -6, 1.58)

spot.rotation_euler = tuple(
    math.radians(v)
    for v in (-287, 48.7, -53.3)
)

spot.scale = (4.8, 4.8, 4.8)


# ==========================================
# LUCE SUN - LUCE_SOLE
# ==========================================

sun_data = bpy.data.lights.new(
    name="luce_sole",
    type='SUN'
)

# Strength / Energy
sun_data.energy = 1.0

sun = bpy.data.objects.new(
    "luce_sole",
    sun_data
)

scene.collection.objects.link(sun)

sun.location = (0, 0, 15)

sun.rotation_euler = tuple(
    math.radians(v)
    for v in (41.1, -1.8, -0.7)
)


# ==========================================
# EMPTY PRINCIPALE
# ==========================================

empty_camera = bpy.data.objects.new(
    "empty_camera",
    None
)

scene.collection.objects.link(empty_camera)

empty_camera.empty_display_type = 'PLAIN_AXES'

# ==========================================
# CAMERA
# ==========================================

cam_data = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", cam_data)

scene.collection.objects.link(camera)

camera.parent = empty_camera

scene.camera = camera

# ==========================================
# CAMERA TRACKER
# ==========================================

camera_tracker = bpy.data.objects.new(
    "camera_tracker",
    None
)

scene.collection.objects.link(camera_tracker)

camera_tracker.empty_display_type = 'SPHERE'
camera_tracker.parent = empty_camera


# ==========================================
# TRACK TO CONSTRAINT
# ==========================================

track_constraint = camera.constraints.new(
    type='TRACK_TO'
)

track_constraint.name = "Camera Track To"

# Oggetto da seguire
track_constraint.target = camera_tracker

# Asse della camera rivolto verso il target
track_constraint.track_axis = 'TRACK_NEGATIVE_Z'

# Asse verticale
track_constraint.up_axis = 'UP_Y'

track_constraint.use_target_z = True


# ==========================================
# FUNZIONE KEYFRAME EMPTY_CAMERA
# ==========================================

def set_empty_keyframe(frame, location=None,
                       rotation=None, scale=None):

    if location is not None:
        empty_camera.location = location

    if rotation is not None:
        empty_camera.rotation_euler = tuple(
            math.radians(v) for v in rotation
        )

    if scale is not None:
        empty_camera.scale = (scale, scale, scale)

    if location is not None:
        empty_camera.keyframe_insert(
            data_path="location", frame=frame
        )

    if rotation is not None:
        empty_camera.keyframe_insert(
            data_path="rotation_euler", frame=frame
        )

    if scale is not None:
        empty_camera.keyframe_insert(
            data_path="scale", frame=frame
        )

# ==========================================
# KEYFRAMES EMPTY_CAMERA
# ==========================================

set_empty_keyframe(
    1,
    location=(0, 0, 0),
    rotation=(0, 0, 0),
    scale=1.705
)

set_empty_keyframe(
    50,
    rotation=(0, 0, 0)
)

set_empty_keyframe(
    160,
    scale=2.475
)

set_empty_keyframe(
    421,
    rotation=(0, 0, 311.25)
)

set_empty_keyframe(
    528,
    rotation=(0, 0, 327.88),
    scale=1.604
)

set_empty_keyframe(
    628,
    rotation=(0, 0, 360),
    scale=1.172
)

set_empty_keyframe(
    717,
    scale=3.241
)

# ==========================================
# KEYFRAMES CAMERA
# ==========================================

camera.location = (0, -8.89, 10.43)
camera.keyframe_insert(
    data_path="location",
    frame=1
)

camera.location = (0, -8.89, 0)
camera.keyframe_insert(
    data_path="location",
    frame=380
)

# ==========================================
# IMPOSTAZIONI FINALI
# ==========================================

scene.frame_set(1)

bpy.context.view_layer.objects.active = empty_camera
empty_camera.select_set(True)

print("Camera rig creato correttamente!")





# ==========================================
# ICREAZIONE EMPTY
# ==========================================


def recupera_o_crea_controllo_generale():

    nome = "CONTROLLO_GENERALE"

    empty = bpy.data.objects.get(nome)

    if empty is None:
        empty = bpy.data.objects.new(nome, None)
        empty.empty_display_type = 'SPHERE'
        empty.empty_display_size = 2.0

        collection_empty = bpy.data.collections.get("CONTROLLI_EMPTY")

        if collection_empty is None:
            collection_empty = bpy.data.collections.new("CONTROLLI_EMPTY")
            bpy.context.scene.collection.children.link(collection_empty)

        collection_empty.objects.link(empty)

    return empty



def recupera_o_crea_empty(nome_oggetto):

    nome_empty = f"{nome_oggetto}_Empty"

    empty = bpy.data.objects.get(nome_empty)

    if empty is None:
        empty = bpy.data.objects.new(nome_empty, None)
        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 1.0

        collection_empty = bpy.data.collections.get("CONTROLLI_EMPTY")

        if collection_empty is None:
            collection_empty = bpy.data.collections.new("CONTROLLI_EMPTY")
            bpy.context.scene.collection.children.link(collection_empty)

        collection_empty.objects.link(empty)

    # Recupera il controllo generale
    controllo = recupera_o_crea_controllo_generale()

    # Imposta il parent mantenendo la trasformazione globale
    if empty.parent != controllo:
        matrice_world = empty.matrix_world.copy()
        empty.parent = controllo
        empty.matrix_world = matrice_world

    return empty












# ==========================================
# IMPORTAZIONE POLIGONI SGHEMBI
# ==========================================

collection_name = "poligoni sghembi"

# Percorso relativo al file Blender

folder_path = os.path.join(
    asset_path,
    "data-leo",
    "poligoni_sghembi"
)

# Verifica esistenza collection
collection = bpy.data.collections.get(collection_name)

if collection is None:

    print("Collection non trovata. Creazione...")

    collection = bpy.data.collections.new(
        collection_name
    )

    scene.collection.children.link(collection)

    # Verifica cartella sorgente
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(
            f"Cartella non trovata: {folder_path}"
        )

    # Importazione file OBJ, FBX, PLY, STL, GLB, GLTF
    supported_extensions = (
        ".obj",
        ".fbx",
        ".ply",
        ".stl",
        ".glb",
        ".gltf"
    )

    imported_count = 0

    for filename in sorted(os.listdir(folder_path)):

        filepath = os.path.join(folder_path, filename)

        if not os.path.isfile(filepath):
            continue

        extension = os.path.splitext(filename)[1].lower()

        if extension not in supported_extensions:
            continue

        # Oggetti presenti prima dell'importazione
        previous_objects = set(bpy.data.objects)

        # Importazione in base al formato
        if extension == ".obj":
            bpy.ops.wm.obj_import(filepath=filepath)

        elif extension == ".fbx":
            bpy.ops.import_scene.fbx(filepath=filepath)

        elif extension == ".ply":
            bpy.ops.wm.ply_import(filepath=filepath)

        elif extension == ".stl":
            bpy.ops.wm.stl_import(filepath=filepath)

        elif extension == ".glb" or extension == ".gltf":
            bpy.ops.import_scene.gltf(filepath=filepath)

        # Recupera nuovi oggetti importati
        new_objects = set(bpy.data.objects) - previous_objects

        for obj in new_objects:

            if obj.type == 'MESH':
                
                #Rimuove shade smooth
                for polygon in obj.data.polygons:
                    polygon.use_smooth = False

                # Rimuove il collegamento alle collection
                # precedenti e inserisce nella collection target
                for old_collection in list(obj.users_collection):
                    old_collection.objects.unlink(obj)

                collection.objects.link(obj)

                imported_count += 1

    print(
        f"Importazione completata: "
        f"{imported_count} mesh."
    )
    # Nasconde la collection nel viewport
    collection.hide_viewport = True

    # Esclude la collection dal rendering
    collection.hide_render = True

else:

    print(
        f"Collection '{collection_name}' già presente. "
        "Importazione saltata."
    )

# ==========================================
# FINE IMPORTAZIONE
# ==========================================




# ==========================================
# IMPORTAZIONE basi
# ==========================================

collection_name = "basi"


folder_path = os.path.join(
    asset_path,
    "data-leo",
    "basi"
)

# Verifica esistenza collection
collection = bpy.data.collections.get(collection_name)

if collection is None:

    print("Collection non trovata. Creazione...")

    collection = bpy.data.collections.new(
        collection_name
    )

    scene.collection.children.link(collection)

    # Verifica cartella sorgente
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(
            f"Cartella non trovata: {folder_path}"
        )

    # Importazione file OBJ, FBX, PLY, STL, GLB, GLTF
    supported_extensions = (
        ".obj",
        ".fbx",
        ".ply",
        ".stl",
        ".glb",
        ".gltf"
    )

    imported_count = 0

    for filename in sorted(os.listdir(folder_path)):

        filepath = os.path.join(folder_path, filename)

        if not os.path.isfile(filepath):
            continue

        extension = os.path.splitext(filename)[1].lower()

        if extension not in supported_extensions:
            continue

        # Oggetti presenti prima dell'importazione
        previous_objects = set(bpy.data.objects)

        # Importazione in base al formato
        if extension == ".obj":
            bpy.ops.wm.obj_import(filepath=filepath)

        elif extension == ".fbx":
            bpy.ops.import_scene.fbx(filepath=filepath)

        elif extension == ".ply":
            bpy.ops.wm.ply_import(filepath=filepath)

        elif extension == ".stl":
            bpy.ops.wm.stl_import(filepath=filepath)

        elif extension == ".glb" or extension == ".gltf":
            bpy.ops.import_scene.gltf(filepath=filepath)

        # Recupera nuovi oggetti importati
        new_objects = set(bpy.data.objects) - previous_objects

        for obj in new_objects:

            if obj.type == 'MESH':
                
                nome = os.path.basename(obj.name)
                nome = nome.split("base")[0]+"base"
                obj.name = nome
                
                # Imposta la base come figlia del relativo Empty
                empty = recupera_o_crea_empty(nome)

                matrice_world = obj.matrix_world.copy()
                obj.parent = empty
                obj.matrix_world = matrice_world
                
                for polygon in obj.data.polygons:
                    polygon.use_smooth = False

                # Rimuove il collegamento alle collection
                # precedenti e inserisce nella collection target
                for old_collection in list(obj.users_collection):
                    old_collection.objects.unlink(obj)

                collection.objects.link(obj)

                imported_count += 1

    print(
        f"Importazione completata: "
        f"{imported_count} mesh."
    )
    # Nasconde la collection nel viewport
    #collection.hide_viewport = True

    # Esclude la collection dal rendering
    #collection.hide_render = True

else:

    print(
        f"Collection '{collection_name}' già presente. "
        "Importazione saltata."
    )

# ==========================================
# FINE IMPORTAZIONE
# ==========================================





# ==========================================
# IMPORTAZIONE MESH AMBIENTE
# ==========================================

files_ambiente = [
    "Muro_nero.obj",
    "stanza.obj"
]

for filename in files_ambiente:

    filepath = os.path.join(
        asset_path,
        "data-leo",
        "ambiente",
        filename
        )

    if not os.path.exists(filepath):
        print(f"File non trovato: {filepath}")
        continue

    bpy.ops.wm.obj_import(filepath=filepath)

    print(f"Importato: {filename}")

print("Importazione completata!")










# ============================================================
# PARAMETRI ANIMAZIONE FACCE
# ============================================================

FRAME_INIZIO = 1
FRAME_FINE = 61
FRAME_MEDIO = (FRAME_FINE-FRAME_INIZIO)//3

NOME_COLLECTION = "FACCE_ANIMATE_GENERATE"


# ============================================================
# LISTA SOLIDI
# ============================================================

lista_solidi = [
    ("A_tetra", 3),
    ("B_tetra", 3),
    ("O_dode", 5),
    ("E_esa", 4),
    ("F_esa", 4),
    ("G_otta", 3),
    #("D_tetra", 3),
    ("H_otta", 3),
    ("I_dode", 5),
    ("K_dode", 5),
    ("L_ico", 3),
    ("N_esa", 4),
    ("V_cuboct_3", 3),
    ("V_cuboct_4", 4),
    ("W_icosid_3", 3),
    ("W_icosid_5", 5),
    ("C_tetra", 3),
    ("M_ico", 3),
]






def assegna_colori_poligoni():
    print('assegno colori')

    palette = [
        "#E85D5D", #colore A
        "#A7C957", #colore B
        "#E9C46A", #colore C
        "#F28E2B", #colore E
        "#2A9D8F", #colore F
        "#48BFE3", #colore G
        "#4EA8DE", #colore H
        "#C445A4", #colore I 
        "#3A0CA3", #colore K
        "#7209B7", #colore L
        "#4361EE", #colore M
        "#F284B6", #colore N
        "#C76D45", #colore O
        "#84A98C", #colore V
        "#84A98C", #V
        "#9D8DF1", #colore W
        "#9D8DF1", #W
    ]

    # Conversione HEX -> RGB lineare
    def hex_to_rgb(hex_color):

        rgb = [
            int(hex_color[i:i+2], 16) / 255
            for i in (1, 3, 5)
        ]

        return tuple(
            ((c + 0.055) / 1.055) ** 2.4
            if c > 0.04045
            else c / 12.92
            for c in rgb
        )

    # Recupera collection
    collection = bpy.data.collections.get("poligoni sghembi")

    if collection is None:
        print("Collection 'poligoni sghembi' non trovata.")
        return

    # Considera solo oggetti mesh
    oggetti = [
        obj for obj in collection.objects
        if obj.type == 'MESH'
    ]

    for i_test, obj in enumerate(oggetti):
        if obj.name in ['V_cuboct_4', 'W_icosid_5']:
            i = i_test -1
        else:
            i = i_test

        colore_hex = palette[i % len(palette)]
        rgb = hex_to_rgb(colore_hex)

        # Crea o recupera materiale
        nome_materiale = f"Colore_{i+1:02d}"

        mat = bpy.data.materials.get(nome_materiale)

        if mat is None:
            mat = bpy.data.materials.new(nome_materiale)

        # Impostazioni materiale
        mat.diffuse_color = (*rgb, 1.0)
        mat.use_nodes = True

        bsdf = mat.node_tree.nodes.get("Principled BSDF")

        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.45

        # Assegna il materiale alla mesh
        obj.data.materials.clear()
        obj.data.materials.append(mat)

        # Tutte le facce usano lo stesso materiale
        for poly in obj.data.polygons:
            poly.material_index = 0

        print(f"{obj.name}: {colore_hex}")

    print(f"Assegnati colori a {len(oggetti)} mesh.")


##ESECUZIONE
assegna_colori_poligoni()







## ============================================================
## ELIMINA EVENTUALI VECCHI HANDLER
## ============================================================

#for h in list(bpy.app.handlers.frame_change_post):
#    if h.__name__ == "aggiorna_solido":
#        bpy.app.handlers.frame_change_post.remove(h)


## ============================================================
## ELIMINA LA PRECEDENTE GENERAZIONE
## ============================================================

#vecchia_collection = bpy.data.collections.get(NOME_COLLECTION)

#if vecchia_collection is not None:

#    for obj in list(vecchia_collection.objects):
#        bpy.data.objects.remove(obj, do_unlink=True)

#    bpy.data.collections.remove(vecchia_collection)







# Crea la collection per le nuove facce

collection = bpy.data.collections.new(NOME_COLLECTION)

bpy.context.scene.collection.children.link(collection)






def anima_base(nome_base, t0, intervallo_1):

    import bpy

    # ==========================================
    # PARAMETRI TEMPORALI
    # ==========================================
    
    intervallo_0 = 1
    fade_in = 15
    #intervallo_1 = 65
    fade_out = 15

    # ==========================================
    # RICERCA MESH
    # ==========================================

    obj = bpy.data.objects.get(nome_base)

    if obj is None:
        print(f"Mesh non trovata: {nome_base}")
        return

    # ==========================================
    # CALCOLO FRAME
    # ==========================================

    f0 = t0
    f1 = f0 + intervallo_0
    f2 = f1 + fade_in
    f3 = f2 + intervallo_1
    f4 = f3 + fade_out

    # ==========================================
    # VISIBILITÀ INIZIALE
    # ==========================================

    obj.hide_viewport = False
    obj.hide_render = False

    obj.keyframe_insert(
        data_path="hide_viewport",
        frame=f0
    )

    obj.keyframe_insert(
        data_path="hide_render",
        frame=f0
    )

    # ==========================================
    # ANIMAZIONE SCALE
    # ==========================================

    keyframes = [
        (f0, 0),
        (f1, 0),
        (f2, 1),
        (f3, 1),
        (f4, 0),
    ]

    for frame, value in keyframes:

        obj.scale = (value, value, value)

        obj.keyframe_insert(
            data_path="scale",
            frame=frame
        )

    # ==========================================
    # NASCONDE LA MESH ALLA FINE
    # ==========================================

    obj.hide_viewport = True
    obj.hide_render = True

    obj.keyframe_insert(
        data_path="hide_viewport",
        frame=f4
    )

    obj.keyframe_insert(
        data_path="hide_render",
        frame=f4
    )

    # ==========================================
    # INTERPOLAZIONE
    # ==========================================

    for fc in fcurves_of(obj) or []:

        if fc.data_path == "scale":

            for key in fc.keyframe_points:
                key.interpolation = 'BEZIER'

        elif fc.data_path in (
            "hide_viewport",
            "hide_render"
        ):

            for key in fc.keyframe_points:
                key.interpolation = 'CONSTANT'

    print(
        f"Animazione {nome_base}: "
        f"{f0} -> {f1} -> {f2} -> {f3} -> {f4}"
    )




# ============================================================
# FUNZIONE PRINCIPALE
# ============================================================

def to_platonic_face(NOME_FACCIA, NOME_SOLIDO, numero_lati, delay):

    # --------------------------------------------------------
    # RECUPERO OGGETTI
    # --------------------------------------------------------

    faccia_obj = bpy.data.objects.get(NOME_FACCIA)
    solido_obj = bpy.data.objects.get(NOME_SOLIDO)

    if faccia_obj is None:
        raise RuntimeError(
            f"Oggetto '{NOME_FACCIA}' non trovato"
        )

    if solido_obj is None:
        raise RuntimeError(
            f"Oggetto '{NOME_SOLIDO}' non trovato"
        )

    mesh = solido_obj.data

    mesh.update()

    # Matrice originale della faccia
    matrice_iniziale = faccia_obj.matrix_world.copy()

    # Centro geometrico locale della faccia modello
    if len(faccia_obj.data.vertices) == 0:
        raise RuntimeError(
            f"La mesh '{NOME_FACCIA}' non contiene vertici"
        )

    centro_locale = sum(
        (v.co for v in faccia_obj.data.vertices),
        Vector()
    ) / len(faccia_obj.data.vertices)

    # --------------------------------------------------------
    # CENTRO DEL SOLIDO IN COORDINATE MONDO
    # --------------------------------------------------------

    verts_solido = [
        solido_obj.matrix_world @ v.co
        for v in mesh.vertices
    ]

    centro_solido = sum(
        verts_solido,
        Vector()
    ) / len(verts_solido)

    # --------------------------------------------------------
    # GENERAZIONE DELLE FACCE
    # --------------------------------------------------------

    numero_create = 0

    for i, poly in enumerate(mesh.polygons):

        # Filtro numero lati

        if numero_lati is not None:
            if len(poly.vertices) != numero_lati:
                continue

        # Vertici del poligono in coordinate mondo

        verts = [
            solido_obj.matrix_world @ mesh.vertices[v].co
            for v in poly.vertices
        ]

        # Centro del poligono

        centro = sum(verts, Vector()) / len(verts)

        # ----------------------------------------------------
        # CALCOLO NORMALE E ASSI LOCALI
        # ----------------------------------------------------

        v0, v1, v2 = verts[0], verts[1], verts[2]

        z = (v1 - v0).cross(v2 - v0).normalized()

        y = (v0 - centro).normalized()

        y = (y - z * y.dot(z)).normalized()

        x = y.cross(z).normalized()

        y = z.cross(x).normalized()

        # Matrice di rotazione

        rot = Matrix((
            (x.x, y.x, z.x),
            (x.y, y.y, z.y),
            (x.z, y.z, z.z)
        ))

        trasformazione = rot.to_4x4()

        trasformazione.translation = centro

        # ----------------------------------------------------
        # CREA LA NUOVA FACCIA
        # ----------------------------------------------------

        nuova = faccia_obj.copy()

        nuova.data = faccia_obj.data.copy()

        #nuova.data.materials.clear()
        nuova = faccia_obj.copy()
        nuova.data = faccia_obj.data.copy()

        # Elimina eventuali animazioni ereditate
        nuova.animation_data_clear()

        collection.objects.link(nuova)

        # Mantiene la trasformazione originale
        # del tuo script

        nuova.matrix_world = trasformazione @ matrice_iniziale

        nuova.name = f"{NOME_FACCIA}_Faccia_{i:02d}"
        
        nuova.hide_render = False

        # ----------------------------------------------------
        # CALCOLO MOVIMENTO RADIALE
        # ----------------------------------------------------

        # Centro geometrico effettivo della nuova faccia
        # in coordinate mondo

        centro_faccia = nuova.matrix_world @ centro_locale

        # Vettore diretto verso il centro del solido

        spostamento = (centro_solido - centro_faccia)*0.6

        # Posizione iniziale

        posizione_iniziale = nuova.location.copy()

        # ----------------------------------------------------
        # KEYFRAME INIZIALE e FINALE
        # ----------------------------------------------------

        nuova.keyframe_insert(
            data_path="location",
            frame=FRAME_FINE + delay,
            group="Animazione radiale"
        )
        
        nuova.keyframe_insert(
            data_path="scale",
            frame=FRAME_MEDIO + delay,
            group="Animazione radiale"
        )
        
        

        # ----------------------------------------------------
        # KEYFRAME MEDIO
        # ----------------------------------------------------

        matrice_finale = nuova.matrix_world.copy()

        matrice_finale.translation -= spostamento

        nuova.matrix_world = matrice_finale

        nuova.keyframe_insert(
            data_path="location",
            frame=FRAME_INIZIO + delay,
            group="Animazione radiale"
        )
        
        nuova.scale = [0,0,0]
        
        nuova.keyframe_insert(
            data_path="scale",
            frame=FRAME_INIZIO + delay,
            group="Animazione radiale"
        )
        
#        
#        nuova.keyframe_insert(
#            data_path="location",
#            frame=FRAME_MEDIO + FRAME_FINE,
#            group="Animazione radiale"
#        )

        # Ripristina la posizione iniziale
        # per continuare la generazione
        
        for fc in fcurves_of(nuova):
            for key in fc.keyframe_points:
                key.interpolation = 'SINE'
                key.easing = 'EASE_IN_OUT'

        nuova.location = posizione_iniziale
        
        
        # Recupera o crea l'Empty relativo al solido
        empty = recupera_o_crea_empty(NOME_SOLIDO)

        # Imposta il parent
        nuova.parent = empty

        # Mantiene invariata la trasformazione globale della faccia
        nuova.matrix_parent_inverse = empty.matrix_world.inverted()

        numero_create += 1

    # --------------------------------------------------------
    # RISULTATO
    # --------------------------------------------------------

    if numero_create == 0:

        print(
            f"Nessuna faccia con {numero_lati} lati "
            f"trovata su {NOME_SOLIDO}"
        )

    else:

        print(
            f"{NOME_FACCIA}: create {numero_create} facce "
            f"animate fino al frame {FRAME_FINE}"
        )


# ============================================================
# GENERAZIONE DI TUTTI I SOLIDI
# ============================================================

for s, solido in enumerate(lista_solidi):
    nome, lati = solido
    t0 = [s*10 , -300][nome=="M_ico"] # M pate già montato
    to_platonic_face(
        nome,
        nome + "_base",
        lati,
        t0 + 60 #inizio animazione
    )
    anima_base(
        nome + "_base",
        10 + s, #frame spawn
        t0 + 50 #intervallo visibile
    )
    


# ============================================================
# IMPOSTAZIONI FINALI
# ============================================================

scene = bpy.context.scene

scene.frame_start = FRAME_INIZIO

if scene.frame_end < FRAME_FINE:
    scene.frame_end = FRAME_FINE

# Torna al frame iniziale

scene.frame_set(FRAME_INIZIO)

print("----------------------------------------")
print("GENERAZIONE COMPLETATA")
print(f"Frame iniziale: {FRAME_INIZIO}")
print(f"Frame finale: {FRAME_FINE}")
print("Facce separate e animate radialmente.")
print("Nessun frame_change_post registrato.")
print("----------------------------------------")












import json

# ==========================================
# CONFIGURAZIONE
# ==========================================

json_path = os.path.join(
    asset_path,
    "data-leo",
    "animazioni_mesh.json"
)

# ==========================================
# LETTURA
# ==========================================

with open(json_path, "r", encoding="utf-8") as f:
    animation_data = json.load(f)

# ==========================================
# IMPORTAZIONE
# ==========================================

for obj_name, frames in animation_data.items():

    obj = bpy.data.objects.get(obj_name)

    if obj is None:
        print(f"Oggetto non trovato: {obj_name}")
        continue

    # Rimuove vecchie animazioni
    if obj.animation_data and obj.animation_data.action:

        action = obj.animation_data.action

        if action.users > 1:
            action = action.copy()
            obj.animation_data.action = action

        fcurves = fcurves_of(obj)
        for fc in list(fcurves or []):
            if fc.data_path in (
                "location",
                "rotation_euler",
                "scale"
            ):
                fcurves.remove(fc)

    # ======================================
    # RICOSTRUZIONE KEYFRAME
    # ======================================

    for frame, properties in frames.items():

        frame = int(frame)

        if "loc" in properties:
            obj.location = properties["loc"]
            obj.keyframe_insert(
                data_path="location",
                frame=frame
            )

        if "rot" in properties:
            obj.rotation_euler = properties["rot"]
            obj.keyframe_insert(
                data_path="rotation_euler",
                frame=frame
            )

        if "scale" in properties:
            obj.scale = properties["scale"]
            obj.keyframe_insert(
                data_path="scale",
                frame=frame
            )
        
        # VISIBILITÀ
        if "visible" in properties:

            visible = properties["visible"]

            # Viewport
            obj.hide_viewport = not visible

            # Rendering
            obj.hide_render = not visible

            # Keyframe viewport
            obj.keyframe_insert(
                data_path="hide_viewport",
                frame=frame
            )

            # Keyframe rendering
            obj.keyframe_insert(
                data_path="hide_render",
                frame=frame
            )

    print(f"Animazione applicata: {obj_name}")

print("Importazione completata!")
