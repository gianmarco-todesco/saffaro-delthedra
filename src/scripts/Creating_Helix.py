import bpy
import math
from mathutils import Vector


bpy.context.scene.frame_current = 0

camera = bpy.data.objects.get("Camera")
ref = bpy.data.objects.get("Empty")
camera.location = (10, 0, 0.5)
camera.parent = ref
camera.matrix_parent_inverse = ref.matrix_world.inverted()
posizione_camera_iniziale = camera.location.copy()

# --- CONFIGURAZIONE TIMELINE ELICOIDE ---
FPS = bpy.context.scene.render.fps

F_C1_INIZIO = 1
D_C1 = 10                      # frame per far crescere c_1 da scala 0 a 1

F_PRIME_PARTI_INIZIO = F_C1_INIZIO + D_C1   # subito dopo che c_1 è apparso
N_PRIME_PARTI = 3               # quante parti dell'elicoide appaiono "in rapida successione"
FRAME_TRA_PRIME_PARTI = 4       # pochi frame tra una e l'altra
D_APPARIZIONE = 8               # durata della crescita di ciascun tetraedro

PAUSA_SECONDI = 7
PAUSA_FRAME = int(PAUSA_SECONDI * FPS)

FRAME_TRA_TETRAEDRI_DOPO_PAUSA = 10   # ritmo "normale" dopo la pausa

NUM_TETRAEDRI_TOTALI = 30


elica_costruita = False
tetraedri_elica_obj = []

NOME_COLLEZIONE_ELICA = "BC_Helix"
if NOME_COLLEZIONE_ELICA in bpy.data.collections:
    coll_helix = bpy.data.collections[NOME_COLLEZIONE_ELICA]
    for o in list(coll_helix.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    coll_helix = bpy.data.collections.new(NOME_COLLEZIONE_ELICA)
    bpy.context.scene.collection.children.link(coll_helix)


def aggiungi_tetraedro_elica(vertici, old_apex_index, edge_length):
    A, B, C = vertici[-3], vertici[-2], vertici[-1]
    old_apex = vertici[old_apex_index]
    centroide = (A + B + C) / 3
    normale = (B - A).cross(C - A).normalized()
    if normale.dot(old_apex - centroide) > 0:
        normale = -normale
    altezza = edge_length * math.sqrt(2/3)
    vertici.append(centroide + normale * altezza)


def costruisci_elica_da_c1(n_max):
    global elica_costruita

    if elica_costruita:
        return

    obj_c1 = bpy.data.objects.get('c_1')
    if obj_c1 is None:
        return

    matrice_mondo = obj_c1.matrix_world.copy()
    vertici_elica = [matrice_mondo @ v.co for v in obj_c1.data.vertices]

    if len(vertici_elica) != 4:
        print(f"Attenzione: c_1 ha {len(vertici_elica)} vertici, non 4.")
        return

    edge_length = (vertici_elica[0] - vertici_elica[1]).length

    for i in range(n_max - 1):
        aggiungi_tetraedro_elica(vertici_elica, len(vertici_elica) - 4, edge_length)

    materiale_c1 = obj_c1.data.materials[0] if len(obj_c1.data.materials) > 0 else None

    for i in range(1, n_max):
        v_locali = [vertici_elica[i], vertici_elica[i+1], vertici_elica[i+2], vertici_elica[i+3]]
        centro = sum(v_locali, Vector((0, 0, 0))) / 4
        v_relativi = [v - centro for v in v_locali]
        facce = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]

        mesh = bpy.data.meshes.new(f"Tetra_Elica_{i:03d}")
        mesh.from_pydata(v_relativi, [], facce)
        mesh.update()

        obj_t = bpy.data.objects.new(f"Tetra_Elica_{i:03d}", mesh)
        obj_t.location = centro
        obj_t.scale = (0.0, 0.0, 0.0)
        coll_helix.objects.link(obj_t)

        if materiale_c1:
            obj_t.data.materials.append(materiale_c1)

        tetraedri_elica_obj.append(obj_t)

    elica_costruita = True
    print(f"Elica costruita al frame {bpy.context.scene.frame_current}.")


def anima_crescita_c1(frame):
    obj_c1 = bpy.data.objects.get("c_1")
    if obj_c1 is None:
        return

    if frame < F_C1_INIZIO:
        s = 0.0
    elif frame >= F_C1_INIZIO + D_C1:
        s = 1.0
    else:
        s = (frame - F_C1_INIZIO) / D_C1

    obj_c1.scale = (s, s, s)


def frame_apparizione_tetraedro(i):
    """Calcola a che frame appare il tetraedro i-esimo dell'elicoide
    (indice 0 = primo tetraedro dopo c_1), gestendo la pausa di 7 secondi."""
    if i < N_PRIME_PARTI:
        # Prime parti: rapida successione, subito dopo c_1
        return F_PRIME_PARTI_INIZIO + i * FRAME_TRA_PRIME_PARTI
    else:
        # Dopo le prime N_PRIME_PARTI, c'è la pausa, poi si riprende
        frame_fine_prime_parti = F_PRIME_PARTI_INIZIO + (N_PRIME_PARTI - 1) * FRAME_TRA_PRIME_PARTI + D_APPARIZIONE
        frame_ripresa = frame_fine_prime_parti + PAUSA_FRAME
        indice_dopo_pausa = i - N_PRIME_PARTI
        return frame_ripresa + indice_dopo_pausa * FRAME_TRA_TETRAEDRI_DOPO_PAUSA


def anima_costruzione_elicoide(frame):
    if frame >= F_PRIME_PARTI_INIZIO:
        costruisci_elica_da_c1(NUM_TETRAEDRI_TOTALI)

    if frame >= F_PRIME_PARTI_INIZIO and elica_costruita:
        for i, obj_t in enumerate(tetraedri_elica_obj):
            f_app = frame_apparizione_tetraedro(i)

            if frame < f_app:
                s = 0.0
            elif frame < f_app + D_APPARIZIONE:
                s = (frame - f_app) / D_APPARIZIONE
            else:
                s = 1.0
            obj_t.scale = (s, s, s)


def rotateObj(a, ax, delt):
    delt.rotation_euler[ax] += math.radians(a)


def frame_change_handler(scene):
    frame = scene.frame_current
    camera = bpy.data.objects.get("Camera")

    if frame >= 130:
        camera.location = (
            posizione_camera_iniziale.x + 0.1 * (frame - 130),
            posizione_camera_iniziale.y + 0,
            posizione_camera_iniziale.z + 0.02 * (frame - 130)
        )

    rotateObj(-1, 2, ref)

    anima_crescita_c1(frame)
    anima_costruzione_elicoide(frame)


bpy.app.handlers.frame_change_pre.clear()
bpy.app.handlers.frame_change_pre.append(frame_change_handler)