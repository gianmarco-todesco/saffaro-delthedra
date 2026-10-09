# scripts

Script "main" da eseguire dentro **Blender**. Non sono importabili come moduli:
sono punti d'ingresso che costruiscono/animano una scena.

Le librerie condivise (`geometry`, `extended_face`, `pieces`, `textures`, `bl_utils`, `bl_anim`, `m_scene`, `story`) stanno in
[`../libs`](../libs) e vengono coperte dai test in [`../../test`](../../test).

## Come si esegue uno script in Blender

1. Apri Blender e passa al workspace **Scripting**.
2. Nel *Text Editor* apri il file `.py` (Open) — dev'essere salvato su disco:
   lo script ricava da solo la cartella delle librerie dal percorso del file.
3. Premi **Run Script** (▶) o `Alt+P`.

Il preambolo in testa a ogni script (`_find_libs_dir()`) mette `../libs` sul
`sys.path` e ricarica i moduli (`importlib.reload`), così puoi modificare le
librerie e rilanciare senza riavviare Blender.

Nota: usa `bpy.context.space_data.text.filepath` invece di `__file__` perché
quest'ultimo non è definito nell'editor di testo di Blender.

## Il path dello script: attenzione a "Relative Path"

`text.filepath` **non è sempre assoluto**. Se il file è stato aperto con
l'opzione **Relative Path** spuntata (default di Blender), il percorso è
relativo al `.blend` e inizia con `//` — e questo capita di sicuro quando il
`.blend` sta fuori da questo repo (es. in `saffaro/blender/`). Python non
conosce quella convenzione e interpreta `//` come radice UNC, quindi
`os.path.dirname` produce un percorso inesistente: `sys.path` riceve una
cartella fantasma e l'import fallisce con un fuorviante
`ModuleNotFoundError: No module named 'geometry'`.

Per questo il preambolo passa da **`bpy.path.abspath()`**, che risolve i path
`//` (lasciando intatti quelli assoluti), e poi verifica con `os.path.isdir()`
che la cartella `libs` esista davvero, segnalando subito l'errore vero.

Se vedi comunque un errore sul path, controlla cosa restituisce, nella console
Python di Blender:

```python
import bpy; print(repr(bpy.context.space_data.text.filepath))
```

Stringa vuota = il testo non è salvato su disco (è un blocco "interno": usa
*Text > Save As*).

## Script disponibili

| file               | cosa fa                                              |
|--------------------|------------------------------------------------------|
| `create_M.py`      | crea l'oggetto "M" (poliedro chiuso) in un colpo solo; nessuna callback, nessun render |
| `single_fan.py`    | una singola faccia estesa (un ventaglio)             |
| `two_fans.py`      | due facce estese saldate su uno spigolo              |
| `20-fans.py`       | le 20 facce estese sull'icosaedro (poliedro M)       |
| `20-fans-bis.py`   | variante con animazione dei 20 ventagli              |
| `explode_M.py`     | M come 240 istanze di un solo triangolo, animate dal poliedro a una griglia piana |
| `M_ico.py`         | M dentro l'icosaedro-anima ingrandito fino a contenerlo: mostra che hanno la stessa simmetria |
| `M_story.py`       | l'animazione completa (icosaedro -> ventaglio -> M), tutta bakerata in keyframe e shape key: nessun handler, quindi Render Animation non crasha |
| `M_video.py`       | il video: dal quadro di Saffaro a M, che gira dentro l'icosaedro ed esplode nei 240 triangoli allineati per contarli; usa `../../../assets` (m.jpg, m2face_texture.png) |
| `M_video2.py`      | il secondo video: fondo scuro sfumato fra i quattro angoli, M nella posa del quadro che gira, l'icosaedro, M che sparisce e ricompare, l'esplosione |
| `deltahedra_1.py`  | M e l'icosaedro, poi gli otto deltaedri convessi (da `../../../modelli-3d/convex-deltahedra`) in un girotondo, ordinati per numero di facce |
| `biform_deltahedra.py` | deltaedri monoformi, biformi e triformi (icosaedro, stella octangula, catena di tre tetraedri): sferette colorate per tipo di vertice, scritte collegate ai vertici visibili |
| `cundy_deltahedra.py` | i 25 deltaedri di Cundy e Olshevsky (`../../../3dmodels/cundy`) in una platea, i piccoli davanti e i grandi in fondo, in colori pastello |
| `scene_1.py`       | dal quadro a M (dal materiale dipinto al pastello), lo scheletro e le facce dell'icosaedro, i solidi platonici, e l'esplosione dei 240 triangoli in 20 gruppi |
| `scene_2.py`       | continua scene_1 (stesso fotogramma): i triangoli spariscono, poi icosaedro e M, il tetraedro, e gli otto deltaedri convessi in triangolo e pentagono; texture del triangolo bordato generata in `assets/face_border.png` |
| `scene_3.py`       | cinque deltaedri di Cundy non convessi attorno al composto di tre tetraedri, che restando al centro cresce in verticale, dalle due parti, nell'elica di Boerdijk-Coxeter; la torre rimpicciolisce finche' sborda di poco |
| `scene_4.py`       | biform_deltahedra piu' cundy_deltahedra: icosaedro, stella e composto con sferette, titoli e frecce sui tipi di vertice; poi la stella salta al suo posto nella platea, che compare mentre la camera indietreggia |
| `scene_5a.py`      | M con la texture del quadro sul pavimento ardesia, e davanti, su un arco, cinque deltaedri di Saffaro (`../../../modelli-3d/saffaro-deltahedra`) grandi un terzo, in pastello |
| `Creating_Helix.py`| lo script dello studente con l'elica di Boerdijk-Coxeter (handler di fotogramma), riferimento per scene_3 |

Materiale scartato/sperimentale sta in [`../../trash`](../../trash).
