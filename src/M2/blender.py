import bpy

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
    
