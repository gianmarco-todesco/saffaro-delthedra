import bpy
import os, sys
import importlib

# rendi possibile importare i moduli dallo stesso folder dello script
# (nota bene: __file__ non funziona dallo script editor di Blender,
#  quindi si ricava il path del file dal datablock di testo attivo)
filepath = bpy.context.space_data.text.filepath
_DIR = os.path.dirname(filepath)
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender    
import geometry, blender
for _mod in (geometry, blender):
    importlib.reload(_mod)
    
# crea la mesh M2 e l'oggetto Blender corrispondente
m2 = geometry.make_M2_mesh_data()
blender.create_mesh_object("M2", m2)

# registra un frame handler che ruota l'oggetto M2 di 1° per frame

def on_frame_change(scene):
    obj = bpy.data.objects.get("M2")
    if obj is not None:
        obj.rotation_euler.z = scene.frame_current * 0.01 
        

blender.register_frame_handler(on_frame_change)
