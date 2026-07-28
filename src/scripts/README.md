# scripts

Script "main" da eseguire dentro **Blender**. Non sono importabili come moduli:
sono punti d'ingresso che costruiscono/animano una scena.

Le librerie condivise (`geometry`, `extended_face`, `bl_utils`) stanno in
[`../libs`](../libs) e vengono coperte dai test in [`../../test`](../../test).

## Come si esegue uno script in Blender

1. Apri Blender e passa al workspace **Scripting**.
2. Nel *Text Editor* apri il file `.py` (Open) — dev'essere salvato su disco:
   lo script ricava da solo la cartella delle librerie dal percorso del file.
3. Premi **Run Script** (▶) o `Alt+P`.

Il preambolo in testa a ogni script mette `../libs` sul `sys.path` e ricarica i
moduli (`importlib.reload`), così puoi modificare le librerie e rilanciare senza
riavviare Blender. Nota: usa `bpy.context.space_data.text.filepath` invece di
`__file__` perché quest'ultimo non è definito nell'editor di testo di Blender.

## Script disponibili

| file               | cosa fa                                              |
|--------------------|------------------------------------------------------|
| `create_M.py`      | crea l'oggetto "M" (poliedro chiuso) in un colpo solo; nessuna callback, nessun render |
| `single_fan.py`    | una singola faccia estesa (un ventaglio)             |
| `two_fans.py`      | due facce estese saldate su uno spigolo              |
| `20-fans.py`       | le 20 facce estese sull'icosaedro (poliedro M)       |
| `20-fans-bis.py`   | variante con animazione dei 20 ventagli              |

Materiale scartato/sperimentale sta in [`../../trash`](../../trash).
