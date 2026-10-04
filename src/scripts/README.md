# scripts

Script "main" da eseguire dentro **Blender**. Non sono importabili come moduli:
sono punti d'ingresso che costruiscono/animano una scena.

Le librerie condivise (`geometry`, `extended_face`, `pieces`, `bl_utils`, `bl_anim`, `m_scene`) stanno in
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

Materiale scartato/sperimentale sta in [`../../trash`](../../trash).
