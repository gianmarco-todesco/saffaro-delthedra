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


def set_material_look(name, rgba, alpha=1.0, roughness=0.4):
    """Crea (o riprende) il materiale e gli da' colore.

    Il colore viene riscritto a ogni corsa: il materiale appartiene allo
    script che lo chiama, non all'utente. Se vuoi ritoccarlo a mano, rinominalo.

    Oltre al Base Color si imposta anche `diffuse_color`, che e' quello che la
    vista Solid mostra: cosi' gli oggetti si distinguono subito, senza dover
    passare a Material Preview.
    """
    mat = get_or_create_material(name)
    mat.diffuse_color = (rgba[0], rgba[1], rgba[2], alpha)

    node = None
    if mat.node_tree is not None:
        node = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if node is None:
        return mat                      # materiale senza nodi: basta diffuse_color

    node.inputs["Base Color"].default_value = (rgba[0], rgba[1], rgba[2], 1.0)
    if "Roughness" in node.inputs:
        node.inputs["Roughness"].default_value = roughness
    if alpha < 1.0 and "Alpha" in node.inputs:
        node.inputs["Alpha"].default_value = alpha
        set_blended(mat)
    return mat


def set_blended(mat):
    """Rende il materiale trasparente in EEVEE. Il nome della proprieta' cambia
    con la versione: fino a 4.1 blend_method, da 4.2 surface_render_method."""
    if hasattr(mat, "blend_method"):
        mat.blend_method = 'BLEND'
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = 'BLENDED'


def set_triangle_uvs(mesh, uvs, layer_name="UVMap"):
    """Stessa UV su tutti i triangoli della mesh: il k-esimo vertice di ogni
    faccia (nell'ordine in cui la faccia lo elenca) riceve uvs[k].

    E' cosi' che una texture disegnata su un triangolo compare identica, e con
    lo stesso orientamento, su tutte le facce. La UV sta sui loop, quindi
    sopravvive a un merge_by_distance fatto dopo.
    """
    layer = mesh.uv_layers.get(layer_name) or mesh.uv_layers.new(name=layer_name)
    for poly in mesh.polygons:
        if poly.loop_total != len(uvs):
            raise ValueError(f"faccia {poly.index}: {poly.loop_total} vertici, "
                             f"ma {len(uvs)} coordinate UV")
        for k, li in enumerate(poly.loop_indices):
            layer.data[li].uv = uvs[k]
    return layer
