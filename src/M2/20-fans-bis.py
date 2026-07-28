import bpy
import os, sys
import importlib
import math

# rendi possibile importare i moduli dallo stesso folder dello script
# (nota bene: __file__ non funziona dallo script editor di Blender,
#  quindi si ricava il path del file dal datablock di testo attivo)
filepath = bpy.context.space_data.text.filepath
_DIR = os.path.dirname(filepath)
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender    
import geometry, blender, fan
for _mod in (geometry, blender, fan):
    importlib.reload(_mod)


# definisco un po' di nomi

# creo l'empty
pivot = blender.get_or_create_empty("pivot")

# creo i ventagli
md = fan.make_M2_fan(2*math.pi/4.3)
for i in range(20):
    obj = blender.create_mesh_object(f"fan{i}", md)
    obj.parent = pivot
    
ico = geometry.Polyhedron.ico
ico_side = (ico.vertices[ico.faces[0][0]]-ico.vertices[ico.faces[0][1]]).length()

def update_model(param):
    # mi assicuro che param sia compreso fra 0 e 1
    param = max(0,min(1,param)) 
    theta = (1-param)*1.2 + param*1.5
    md = fan.make_M2_fan(theta)
    p0,p1,p2 = [geometry.Vector(md.vertices[4*i]) for i in range(3)]
    factor = (p0-p1).length()/ico_side
    
    for i in range(20):
        qs = [ico.vertices[ico.faces[i][j]]*factor for j in range(3)]
        
        mat = geometry.matrix_from_triples([p0,p1,p2],qs)
        md = fan.make_M2_fan(theta)
        for j in range(len(md.vertices)):
            md.vertices[j] = geometry.apply_matrix(mat, geometry.Vector(md.vertices[j])).tup()
        blender.update_mesh_object(f"fan{i}", md)

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
