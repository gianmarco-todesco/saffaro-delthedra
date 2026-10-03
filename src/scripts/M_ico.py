"""
M_ico.py -- il poliedro M dentro l'icosaedro che gli fa da anima, ingrandito
fino a contenerlo: due oggetti nella stessa scena, per vedere che hanno la
stessa simmetria.

L'icosaedro non e' un icosaedro qualsiasi disegnato lì attorno: e' *lo stesso*
`geometry.Polyhedron.ico` su cui `make_M` posa le 20 facce estese, con la stessa
orientazione, moltiplicato per un fattore di scala. A grandezza naturale (scala
`core_scale()`) i suoi 12 vertici sono 12 vertici di M -- i tre angoli del
triangolo di base di ogni ventaglio. Qui lo si ingrandisce fino a inglobare M.

Che cosa si dovrebbe vedere
---------------------------
Con ICO_MARGIN = 1.0 la gabbia e' la piu' piccola che contiene M, e il contatto
non e' casuale:

* i **20 apici** dei ventagli puntano esattamente ai **centri delle 20 facce**;
* i **30 vertici piu' esterni** di M (i punti di mezzo dei bordi ripiegati)
  cadono esattamente sui **punti medi dei 30 spigoli** della gabbia.

Sono le due famiglie di assi di simmetria dell'icosaedro -- quelli ternari per
le facce, quelli binari per gli spigoli -- e M li ha tutti. E' il vincolo degli
spigoli a decidere la scala: la gabbia si ferma quando i 30 picchi di M toccano
i 30 spigoli, e i 20 apici restano parecchio sotto i piani delle facce.

Siccome il contatto e' esatto, con lo stile 'WIRE' i tubi della gabbia entrano
un po' dentro M in quei 30 punti: non e' un difetto di z-fighting, e' la
tangenza. Per staccarli basta ICO_MARGIN = 1.05.

Lo script stampa a console i numeri che ha effettivamente calcolato, invece di
affermarli qui e basta.
"""

import bpy

import os, sys
import math
import importlib

import numpy as np

# rendi possibile importare i moduli da src/libs
# (nota bene: __file__ non funziona dallo script editor di Blender,
#  quindi si ricava il path del file dal datablock di testo attivo)
def _find_libs_dir():
    txt = getattr(getattr(bpy.context, "space_data", None), "text", None)
    if txt is None:  # lo script non gira dal Text Editor: cerco il datablock per nome
        txt = bpy.data.texts.get("M_ico.py")
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




# =============================================================================
# CONFIGURAZIONE
# =============================================================================

M_NAME   = "M"                    # il poliedro, come unica mesh di 240 triangoli
ICO_NAME = "M_icosahedron"        # l'icosaedro-gabbia

# Quanto e' grande la gabbia, in multipli della piu' piccola che contiene M.
# 1.0 = tangente (i 30 picchi di M toccano i 30 spigoli); 1.05 la stacca un po'.
ICO_MARGIN = 1.0

# 'WIRE'  -> modificatore Wireframe: la gabbia diventa un telaio di tubi, si
#            vede in render e lascia vedere M che ci sta dentro;
# 'SOLID' -> facce vere, rese semitrasparenti con ICO_ALPHA.
ICO_STYLE = 'WIRE'
ICO_WIRE_THICKNESS = 0.06         # spessore dei tubi (lo spigolo e' lungo ~2.8)
ICO_ALPHA = 0.15                  # solo per ICO_STYLE = 'SOLID'

M_MATERIAL   = "M_surface"
ICO_MATERIAL = "M_ico_cage"
M_COLOR   = (0.85, 0.35, 0.15, 1.0)   # RGBA
ICO_COLOR = (0.15, 0.45, 0.85, 1.0)


# =============================================================================
# GEOMETRIA
# =============================================================================

# Le misure generali stanno in libreria e sono coperte dai test:
#   extended_face.core_scale()             la scala dell'icosaedro-anima, quella
#                                          vera: a quella scala i suoi 12
#                                          vertici sono 12 vertici di M
#   geometry.face_planes(poly)             normali uscenti e distanze dei piani
#   geometry.enclosing_scale(points, poly) il piu' piccolo k per cui k*poly
#                                          contiene i punti
#   geometry.polyhedron_mesh(poly, scale)  la mesh del poliedro scalato
#
# Per M il vincolo che morde e' quello degli spigoli, ma e' un fatto di *questo*
# poliedro: enclosing_scale passa dai piani delle facce apposta per non darlo
# per scontato.


def describe_contact(points, ico, scale):
    """Stampa dove la gabbia tocca M: e' il contenuto dell'immagine, e vale la
    pena leggerlo dai numeri invece che darlo per buono.

    Misura tre cose: quanti vertici di M stanno sui piani delle facce, quanto
    quei punti distano dai punti medi degli spigoli, e quanto gli apici dei
    ventagli si scostano dai centri delle facce.
    """
    P = np.asarray(points, dtype=float).reshape(-1, 3)
    verts = np.asarray([v.tup() for v in ico.vertices], dtype=float) * scale
    normals, dists = geometry.face_planes(ico)
    tol = 1e-6 * max(1.0, scale)

    # i vertici di M che toccano un piano (M ha vertici doppi sugli spigoli
    # condivisi, quindi si contano i punti distinti, non gli indici). Si
    # raggruppa per coordinate arrotondate ma si tiene il punto originale: con
    # quello arrotondato la distanza misurata sotto sarebbe l'arrotondamento
    # stesso (5e-7) invece dello scarto vero.
    on_plane = P[((P @ normals.T) > (scale * dists - tol)).any(axis=1)]
    contact = list({tuple(np.round(p, 6)): p for p in on_plane}.values())
    print(f"[M_ico] punti di M a contatto con la gabbia: {len(contact)}")

    if len(contact):
        mids = np.asarray(sorted({tuple(sorted((f[i], f[(i + 1) % 3])))
                                  for f in ico.faces for i in range(3)}))
        mids = np.asarray([(verts[a] + verts[b]) / 2 for a, b in mids])
        gap = max(float(np.linalg.norm(mids - p, axis=1).min()) for p in contact)
        print(f"[M_ico]   distanza dai punti medi dei {len(mids)} spigoli: {gap:.2e}")

    centers = np.asarray([verts[list(f)].mean(axis=0) for f in ico.faces])
    worst = 0.0
    for i, face_center in enumerate(centers):
        apex = P[(extended_face.N_TRIANGLES + 1) * i + extended_face.N_TRIANGLES]
        # angolo via atan2(|axb|, a.b) e non via acos: qui l'angolo e' zero, e
        # acos vicino a 1 perde tutte le cifre (darebbe 1e-6 gradi di rumore
        # invece del valore vero, facendo sospettare un disallineamento che non
        # c'e'). atan2 e' ben condizionato anche a zero.
        worst = max(worst, math.degrees(math.atan2(
            float(np.linalg.norm(np.cross(apex, face_center))),
            float(apex @ face_center))))
    print(f"[M_ico]   scarto angolare apici dei ventagli / centri delle facce: "
          f"{worst:.2e} gradi")


# I materiali appartengono allo script: bl_utils.set_material_look li riscrive a
# ogni corsa. Se vuoi ritoccarli a mano, rinominali.

set_material_look = bl_utils.set_material_look


# =============================================================================
# COSTRUZIONE DELLA SCENA
# =============================================================================

def build():
    """Crea i due oggetti e stampa le misure. Rilanciabile: `create_mesh_object`
    sostituisce gli oggetti omonimi."""
    ico = geometry.Polyhedron.ico

    # --- M, come unica mesh di 240 triangoli (come in create_M.py) ---
    md = extended_face.make_M()
    m_obj = bl_utils.create_mesh_object(M_NAME, md, material_name=M_MATERIAL)
    bl_utils.merge_by_distance(m_obj)
    set_material_look(M_MATERIAL, M_COLOR, roughness=0.45)

    # --- l'icosaedro, ingrandito fino a contenere M ---
    k_min = geometry.enclosing_scale(md.vertices, ico)
    scale = k_min * ICO_MARGIN
    ico_md = geometry.polyhedron_mesh(ico, scale)
    ico_obj = bl_utils.create_mesh_object(ICO_NAME, ico_md, material_name=ICO_MATERIAL)

    if ICO_STYLE == 'WIRE':
        set_material_look(ICO_MATERIAL, ICO_COLOR, roughness=0.3)
        mod = ico_obj.modifiers.new(name="Wireframe", type='WIREFRAME')
        mod.thickness = ICO_WIRE_THICKNESS
        # offset 0 = tubo centrato sullo spigolo vero (il default e' -1, cioe'
        # tutto all'interno): serve perche' la tangenza sui punti medi degli
        # spigoli si veda dove effettivamente e'.
        mod.offset = 0.0
    elif ICO_STYLE == 'SOLID':
        set_material_look(ICO_MATERIAL, ICO_COLOR, alpha=ICO_ALPHA, roughness=0.2)
    else:
        raise ValueError(f"ICO_STYLE dev'essere 'WIRE' o 'SOLID', non {ICO_STYLE!r}")

    # --- le misure ---
    radii = np.linalg.norm(np.asarray(md.vertices, dtype=float), axis=1)
    print(f"[M_ico] M: {len(m_obj.data.vertices)} vertici saldati, "
          f"{len(m_obj.data.polygons)} facce; raggio da {radii.min():.6f} "
          f"a {radii.max():.6f}")
    print(f"[M_ico] icosaedro: anima a scala {extended_face.core_scale():.6f}, "
          f"gabbia a {scale:.6f} (minima {k_min:.6f} x margine {ICO_MARGIN})")
    print(f"[M_ico] stile {ICO_STYLE}"
          + (f", tubi da {ICO_WIRE_THICKNESS}" if ICO_STYLE == 'WIRE' else ""))
    if ICO_MARGIN == 1.0:
        describe_contact(md.vertices, ico, scale)
    return m_obj, ico_obj


M_OBJECT, ICO_OBJECT = build()
