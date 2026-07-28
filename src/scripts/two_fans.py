import bpy
import os, sys
import importlib
import math

from bpy.app.handlers import persistent

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
PROP_A = "param_a"
PROP_B = "param_b"
PANEL_IDNAME = "MyPanel"

FAN1 = "fan1"
FAN2 = "fan2"

# creo i due ventagli
md = extended_face.make_extended_face(2*math.pi/4.3)
bl_utils.create_mesh_object(FAN1, md)
bl_utils.create_mesh_object(FAN2, md)

#
# Questa funzione aggiorna il modello in funzione di un parametro 'param'
# che va da 0.0 a 1.0
#
def update_model(param):
    # mi assicuro che param sia compreso fra 0 e 1
    param = max(0,min(1,param)) 
    # calcolo l'angolo theta che controlla indirettamente la grandezza del lato del ventaglio
    # rispetto al lato del triangolo dell'icosaedro.
    theta = (1-param)*1.2 + param*1.5
    # costruisco i punti che definiscono il ventaglio
    md = extended_face.make_extended_face(theta)
    # aggiorno la mesh del primo ventaglio
    bl_utils.update_mesh_object(FAN1, md)
    # prendo i punti della mesh
    V = [geometry.Vector(p) for p in md.vertices]
    # calcolo la trasformazione geometrica che "attacca" il secondo ventaglio al primo
    mat = geometry.matrix_from_triples([V[0],V[2],V[4]],[V[4],V[2],V[0]])
    # modifico i punti applicando la trasformazione (in blocco)
    md.vertices = geometry.transform_points(mat, md.vertices).tolist()
    # aggiorno la mesh del secondo ventaglio
    bl_utils.update_mesh_object(FAN2, md)

# inizializzo il tutto
update_model(0)
    
# questa funione viene richiamata in vari casi e aggiorna quello che va aggiornato
# nota bene: i nomi update_model e rebuild_model fanno orrore. Dovremmo trovare qualcosa di meglio
def rebuild_model(scene):
    a = getattr(scene, PROP_A)
    b = getattr(scene, PROP_B)
    update_model(a)

# se la proprietà cambia chiamo rebuild_model
def on_prop_changed(self, context):
    # 'self' è la Scene (la proprietà è registrata su Scene)
    rebuild_model(self)

# se il fotogramma cambia chiamo rebuild_model
@persistent
def on_frame_change(scene, depsgraph=None):
    rebuild_model(scene)

# questa funzione viene chiamata all'inizio ed elimina le chiamate registrate
# della stessa sessione, dalla precedente esecuzione dello script
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
#bl_utils.create_mesh_object("M2", m2)

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
        # layout.operator("scene.gen_rebuild_now", icon='FILE_REFRESH')



# --- Registrazione ---
def register():
    cleanup()

    setattr(bpy.types.Scene, PROP_A, bpy.props.FloatProperty(
        name="Parametro A", default=1.0, min=0.0, max=1.0,
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
# #bl_utils.create_mesh_object("M2_fan", d, material_name="M2_material")

# d = geometry.make_M2_fan_mesh_data(0, param + 0.2)
# bl_utils.update_mesh_object("M2_fan", d)


# # registra un frame handler che ruota l'oggetto M2 di 1° per frame

# def on_frame_change(scene):
#     #obj = bpy.data.objects.get("M2")
#     #if obj is not None:
#     #    obj.rotation_euler.z = scene.frame_current * 0.01 
#     param = scene.frame_current * 0.01 
#     d = geometry.make_M2_fan_mesh_data(0, param + 0.2)
#     bl_utils.update_mesh_object("M2_fan", d)

# bl_utils.register_frame_handler(on_frame_change)


register()

