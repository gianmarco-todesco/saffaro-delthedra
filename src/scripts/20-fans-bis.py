import bpy
import os, sys
import importlib
import math

# rendi possibile importare i moduli da src/libs
# (nota bene: __file__ non funziona dallo script editor di Blender,
#  quindi si ricava il path del file dal datablock di testo attivo)
_DIR = os.path.dirname(bpy.context.space_data.text.filepath)
_LIBS = os.path.join(os.path.dirname(_DIR), "libs")  # script in src/scripts, librerie in src/libs
if _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender    
import geometry, bl_utils, extended_face
for _mod in (geometry, bl_utils, extended_face):
    importlib.reload(_mod)


# definisco un po' di nomi

# creo l'empty
pivot = bl_utils.get_or_create_empty("pivot")

# creo i ventagli
md = extended_face.make_extended_face(2*math.pi/4.3)
for i in range(20):
    obj = bl_utils.create_mesh_object(f"fan{i}", md)
    obj.parent = pivot
    
ico = geometry.Polyhedron.ico
ico_side = (ico.vertices[ico.faces[0][0]]-ico.vertices[ico.faces[0][1]]).length()

def update_model(param):
    # mi assicuro che param sia compreso fra 0 e 1
    param = max(0,min(1,param)) 
    theta = (1-param)*1.2 + param*1.5
    md = extended_face.make_extended_face(theta)
    p0,p1,p2 = [geometry.Vector(md.vertices[4*i]) for i in range(3)]
    factor = (p0-p1).length()/ico_side
    
    for i in range(20):
        qs = [ico.vertices[ico.faces[i][j]]*factor for j in range(3)]
        
        mat = geometry.matrix_from_triples([p0,p1,p2],qs)
        md = extended_face.make_extended_face(theta)
        # trasformazione in blocco di tutti i vertici (una sola moltiplicazione)
        md.vertices = geometry.transform_points(mat, md.vertices).tolist()
        bl_utils.update_mesh_object(f"fan{i}", md)

# inizializzo il tutto
update_model(0)

for frame in range(1,250+1):
    bpy.context.scene.frame_set(frame)
    a = 0.277*(0.5 + 0.5 * math.sin(frame * 0.1))
    update_model(a)
    pivot.rotation_euler.z = frame * 0.01
    bpy.context.view_layer.update()  # aggiorna la scena per vedere il risultato
    bpy.context.scene.render.filepath = f"/tmp/{frame:03d}.png"
    bpy.ops.render.render(write_still=True)  # renderizza e salva l'immagine    

    print(f"Frame {frame} renderizzato e salvato in /tmp/{frame:03d}.png")
