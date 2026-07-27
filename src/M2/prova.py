import bpy
import os, sys
import importlib
import math

from bpy.app.handlers import persistent

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



PROP_A = "param_a"
PROP_B = "param_b"
PANEL_IDNAME = "MyPanel"

MYFAN = "M2fan"

md = fan.make_M2_fan(2*math.pi/4.3)
blender.create_mesh_object(MYFAN, md)


def rebuild_model(scene):
    a = getattr(scene, PROP_A)
    b = getattr(scene, PROP_B)
    t = a   
    md = fan.make_M2_fan((1-t)*1.4 + t*1.5)
    # >>> qui dentro rigeneri/aggiorni la geometria <<<
    blender.update_mesh_object(MYFAN, md)

# crea la mesh M2 e l'oggetto Blender corrispondente
def on_prop_changed(self, context):
    # 'self' è la Scene (la proprietà è registrata su Scene)
    rebuild_model(self)

@persistent
def on_frame_change(scene, depsgraph=None):
    rebuild_model(scene)

def cleanup():
    # handler
    for h in list(bpy.app.handlers.frame_change_post):
        if getattr(h, "__name__", "") == "on_frame_change":
            bpy.app.handlers.frame_change_post.remove(h)
    # pannello
    cls = getattr(bpy.types, PANEL_IDNAME, None)
    if cls is not None:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    # proprietà
    for name in (PROP_A, PROP_B):
        if hasattr(bpy.types.Scene, name):
            try:
                delattr(bpy.types.Scene, name)
            except (AttributeError, RuntimeError):
                pass    
#m2 = geometry.make_M2_mesh_data()
#blender.create_mesh_object("M2", m2)

class MyPanel(bpy.types.Panel):
    bl_label = "Generatore"
    bl_idname = PANEL_IDNAME
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, PROP_A)
        layout.prop(context.scene, PROP_B)
        layout.operator("scene.gen_rebuild_now", icon='FILE_REFRESH')



# --- Registrazione ---
def register():
    cleanup()

    setattr(bpy.types.Scene, PROP_A, bpy.props.FloatProperty(
        name="Parametro A", default=1.0, min=0.0, max=10.0,
        update=on_prop_changed,   # editing manuale
    ))
    setattr(bpy.types.Scene, PROP_B, bpy.props.FloatProperty(
        name="Parametro B", default=0.0, min=-5.0, max=5.0,
        update=on_prop_changed,
    ))

    # bpy.utils.register_class(SCENE_OT_gen_rebuild_now)
    bpy.utils.register_class(MyPanel)

    bpy.app.handlers.frame_change_post.append(on_frame_change)  # animazione


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




blender.register_myprop()

def on_myprop(value):
    obj = bpy.data.objects.get("M2fan")
    if obj is not None:
        if value < 50:
            md = fan.make_M2_fan(1.4)
            t = value/50
            pts = [geometry.Vector(p) for p in md.vertices]
            for i in range(3):
                pa = pts[i*4]
                pb = pts[((i+1)%3)*4]
                for j in range(4):
                    s= j/4
                    p0 = pa*(1-s)+pb*s
                    p1 = pts[i*4+j]
                    p = p0*(1-t) + p1*t
                    md.vertices[i*4+j] = p.tup()
            pts[12].z *= t
            md.vertices[12] = pts[12].tup()
            
        else:
            t = (value-50)/50
            if t<0: t=0
            elif t>1: t=1
            
            md = fan.make_M2_fan((1-t)*1.4 + t*1.5)
            
        blender.update_mesh_object("M2fan", md)
        
        # obj.rotation_euler.z = value
        

blender.PROP_CB = on_myprop


# register()
