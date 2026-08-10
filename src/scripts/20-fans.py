import bpy
import os, sys
import importlib
import math

from bpy.app.handlers import persistent

# rendi possibile importare i moduli da src/libs
# (nota bene: __file__ non funziona dallo script editor di Blender,
#  quindi si ricava il path del file dal datablock di testo attivo)
def _find_libs_dir():
    txt = getattr(getattr(bpy.context, "space_data", None), "text", None)
    if txt is None:  # lo script non gira dal Text Editor: cerco il datablock per nome
        txt = bpy.data.texts.get("20-fans.py")
    if txt is None or not txt.filepath:
        raise RuntimeError(
            "non riesco a ricavare il path dello script: il testo non e' salvato "
            "su disco (Text > Save As) oppure e' un blocco 'interno'"
        )
    # attenzione: se il file e' stato aperto con l'opzione 'Relative Path' spuntata,
    # filepath e' del tipo '//../...' (relativo al .blend) e os.path lo interpreta
    # come percorso UNC. bpy.path.abspath lo risolve; sugli assoluti non fa nulla.
    path = os.path.abspath(bpy.path.abspath(txt.filepath))
    # script in src/scripts, librerie in src/libs
    libs = os.path.join(os.path.dirname(os.path.dirname(path)), "libs")
    if not os.path.isdir(libs):
        raise RuntimeError(f"cartella libs non trovata: {libs}  (filepath: {txt.filepath})")
    return libs


_LIBS = _find_libs_dir()
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


def rebuild_model(scene):
    # in frame_change_pre param_a NON è ancora aggiornato dal depsgraph:
    # lo valuto io dalla fcurve
    # a = eval_scene_prop(scene, PROP_A, getattr(scene, PROP_A))
    a = 0.277*(0.5 + 0.5 * math.sin(scene.frame_current * 0.1))
    
    update_model(a)


@persistent
def on_frame_change(scene, depsgraph=None):
    try:
        rebuild_model(scene)
    except Exception as e:
        print("[on_frame_change] errore ignorato:", e)
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
    for lst in (bpy.app.handlers.frame_change_pre,
                bpy.app.handlers.frame_change_post):
        for h in list(lst):
            if getattr(h, "__name__", "") == "on_frame_change":
                lst.remove(h)
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

    bpy.app.handlers.frame_change_pre.append(on_frame_change)  # animazione


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

