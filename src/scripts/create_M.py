import bpy
import os, sys
import importlib

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

# Costruisce il poliedro M (chiuso, parametro PHI_CLOSING) come unico MeshData
# e crea l'oggetto "M" nella scena, rimpiazzando l'eventuale oggetto omonimo.
# Nessuna callback, nessun render: solo la creazione dell'oggetto.
md = extended_face.make_M()
obj = bl_utils.create_mesh_object("M", md)

# salda i vertici duplicati sugli spigoli condivisi (Merge by Distance)
bl_utils.merge_by_distance(obj)
