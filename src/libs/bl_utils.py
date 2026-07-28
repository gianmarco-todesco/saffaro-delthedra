"""
Utilità per la scena Blender (creazione/aggiornamento di oggetti mesh, materiali,
empty, handler dei frame) a partire dai MeshData della libreria.

NB: richiede `bpy` -> eseguibile solo dentro Blender. A differenza di `geometry`
ed `extended_face` (puri, coperti dai test), questo modulo non è testabile in CI.
"""

import bpy
import bmesh

from geometry import MeshData

def get_or_create_material(name: str) -> bpy.types.Material:
    """Restituisce il materiale `name`, creandolo (con nodi abilitati) se non esiste."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        # Qui si possono personalizzare i nodi del materiale appena creato.
    return mat


def assign_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    """Assegna il materiale all'oggetto usando il primo slot (lo crea se assente)."""
    if obj.data.materials:
        obj.data.materials[0] = mat   # sostituisce il primo slot
    else:
        obj.data.materials.append(mat)

def create_mesh_object(name: str, 
                       mesh_data: MeshData, 
                       material_name: str = "material") -> bpy.types.Object:
    """Crea un oggetto mesh in Blender a partire da vertici e facce."""
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    if name in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes[name])

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(mesh_data.vertices, [], mesh_data.faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    mat = get_or_create_material(material_name)
    assign_material(obj, mat)
    return obj


def merge_by_distance(obj: bpy.types.Object, distance: float = 1e-4) -> bpy.types.Object:
    """Salda i vertici coincidenti dell'oggetto (equivalente al "Merge by
    Distance" di Blender), fondendo quelli piu' vicini di `distance`.

    Utile dopo aver assemblato una mesh da piu' pezzi (es. le 20 facce di M),
    dove gli spigoli condivisi lasciano vertici duplicati coincidenti. Opera
    direttamente sui dati della mesh via bmesh, senza cambiare il contesto/modo.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj

def update_mesh_object(name: str, 
                       mesh_data: MeshData) -> bpy.types.Object:
    """modifica i vertici di un oggetto mesh in Blender."""
    if name not in bpy.data.objects:
        print(f"[bl_utils] update_mesh_object: object {name} does not exist. Skipping update.")
        return
    obj = bpy.data.objects[name]

    vv = obj.data.vertices
    if len(vv) != len(mesh_data.vertices):
        print(f"[bl_utils] update_mesh_object: object {name} has {len(vv)} vertices, but mesh_data has {len(mesh_data.vertices)} vertices. Skipping update.")
        return

    for i, v in enumerate(mesh_data.vertices):
        vv[i].co = v
    obj.data.update()    
    

def register_frame_handler(update_fn):
    """
    Register a persistent ``frame_change_pre`` handler running *update_fn(scene)*.

    General-purpose variant of :func:`register_rotation_animation`: the caller
    supplies the full per-frame logic.  Any handler previously installed by
    either function is removed first (shared sentinel), so switching between
    scene scripts never stacks callbacks.

    Parameters
    ----------
    update_fn : Callable[[bpy.types.Scene], None]
        Called with the scene on every frame change.

    Returns
    -------
    Callable
        The registered handler.
    """
    FLAG = "my_handler"
    handlers = bpy.app.handlers.frame_change_pre
    for h in list(handlers):
        if getattr(h, FLAG, False):
            handlers.remove(h)

    @bpy.app.handlers.persistent
    def _on_frame(scene, _depsgraph=None):
        update_fn(scene)

    setattr(_on_frame, FLAG, True)
    handlers.append(_on_frame)

    _on_frame(bpy.context.scene)
    print("[bl_utils] Registered generic frame handler")
    return _on_frame




def get_or_create_empty(name, empty_type='PLAIN_AXES', size=1.0):
    obj = bpy.data.objects.get(name)
    if obj is None:
        # crea il dato Empty (in realtà l'Empty non ha data-block, basta l'object)
        obj = bpy.data.objects.new(name, None)   # None = Empty
        obj.empty_display_type = empty_type
        obj.empty_display_size = size
        # collega alla collection della scena, altrimenti non compare
        bpy.context.scene.collection.objects.link(obj)
    return obj


def set_parent(child, parent):
    # keep_transform: l'oggetto non "salta" quando gli assegni il parent
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()