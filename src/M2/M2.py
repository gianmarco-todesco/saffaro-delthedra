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
    
# crea la mesh M2 e l'oggetto Blender corrispondente

#m2 = geometry.make_M2_mesh_data()
#blender.create_mesh_object("M2", m2)


# param = geometry.get_M2_parameter()
# #d = geometry.make_M2_fan_mesh_data(0, param)
# #blender.create_mesh_object("M2_fan", d, material_name="M2_material")

# d = geometry.make_M2_fan_mesh_data(0, param + 0.2)
# blender.update_mesh_object("M2_fan", d)


# # registra un frame handler che ruota l'oggetto M2 di 1° per frame

# def on_frame_change(scene):
#     #obj = bpy.data.objects.get("M2")
#     #if obj is not None:
#     #    obj.rotation_euler.z = scene.frame_current * 0.01 
#     param = scene.frame_current * 0.01 
#     d = geometry.make_M2_fan_mesh_data(0, param + 0.2)
#     blender.update_mesh_object("M2_fan", d)

# blender.register_frame_handler(on_frame_change)



md = fan.make_M2_fan(2*math.pi/4.3)
blender.create_mesh_object("M2fan", md)


def myparam_callback(self, context):
    value = self.myparam
    obj = bpy.data.objects.get("M2fan")
    if obj is not None:
        obj.rotation_euler.z = value

def draw_myparam(self, context):
    layout = self.layout
    # Aggiunge una riga separatrice e poi la proprietà
    layout.separator()
    layout.prop(context.scene, "myparam")

def register():
    # Registra la proprietà
    bpy.types.Scene.myparam = bpy.props.FloatProperty(
        name="My Param",
        default=0,
        update=myparam_callback
    )
    
    # Inietta la proprietà nel pannello standard "SCENE_PT_scene"
    # (Pannello 'Scene' dentro le proprietà della Scena)
    bpy.types.SCENE_PT_scene.append(draw_myparam)

def unregister():
    # Rimuove l'iniezione dal pannello standard
    bpy.types.SCENE_PT_scene.remove(draw_myparam)
    
    # Rimuove la proprietà
    del bpy.types.Scene.myparam
    

register()
