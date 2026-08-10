import bpy
import os, sys
import importlib

# rendi possibile importare i moduli da src/libs
# (nota bene: __file__ non funziona dallo script editor di Blender,
#  quindi si ricava il path del file dal datablock di testo attivo)
def _find_libs_dir():
    txt = getattr(getattr(bpy.context, "space_data", None), "text", None)
    if txt is None:  # lo script non gira dal Text Editor: cerco il datablock per nome
        txt = bpy.data.texts.get("playground.py")
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


md2 = extended_face.make_extended_face(extended_face.PHI_CLOSING)
md1 = extended_face.flatten1_extended_face(md2)
md0 = extended_face.flatten2_extended_face(md1)
fan = bl_utils.create_mesh_object("FAN1", md0)

num_frames = 250

def smoothstep(t,t0,t1):
    s = (t-t0)/(t1-t0)
    if s<0.0:s=0.0
    elif s>1.0: s=1.0
    else:
        s = 3*s**2 - 2*s**3
    return s


for frame in range(1,num_frames+1):
    bpy.context.scene.frame_set(frame)
    t = (frame-1)/(num_frames-1)
    if t < 0.5:        
        md = extended_face.morph(md0,md1,smoothstep(t, 0.1, 0.4))
    else:
        md = extended_face.morph(md1,md2,smoothstep(t, 0.6, 0.9))
        
    bl_utils.update_mesh_object("FAN1", md)
    
    fan.rotation_euler.z = frame * 0.02
    bpy.context.view_layer.update()  # aggiorna la scena per vedere il risultato
    bpy.context.scene.render.filepath = f"/tmp/{frame:03d}.png"
    bpy.ops.render.render(write_still=True)  # renderizza e salva l'immagine    

    print(f"Frame {frame} renderizzato e salvato in /tmp/uff{frame:03d}.png")
