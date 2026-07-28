# saffaro-delthedra

Materiale per un video sul **poliedro M**, scoperto e dipinto dal pittore Lucio
Saffaro. Il progetto genera il poliedro in Blender tramite script Python.

## Il poliedro M

M si costruisce a partire da un **icosaedro regolare** sostituendo ogni faccia
triangolare con una **"faccia estesa"**: un ventaglio (*fan*) di 12 triangoli
equilateri identici che condividono un vertice (l'apice) e formano un anello
chiuso con simmetria di ordine 3.

Ogni lato del triangolo di partenza è sostituito da 4 segmenti ripiegati, tutti
complanari sul piano che passa per il centro dell'icosaedro e per quello spigolo:
così due facce estese adiacenti si saldano senza fessure. La configurazione ha
**un solo grado di libertà**; il valore che "chiude" il poliedro è la costante
`extended_face.PHI_CLOSING` (≈ 73.49°), calcolata per bisezione da
`find_closing_parameter()`.

## Struttura del progetto

```
src/
  libs/                 libreria Python (coperta dai test)
    geometry.py         vettori, matrici, icosaedro, poliedri  (puro, no Blender)
    extended_face.py    costruzione della faccia estesa + chiusura di M  (puro)
    bl_utils.py         utilità di scena Blender (mesh, materiali, ...)  (richiede bpy)
  scripts/              entry-point da eseguire dentro Blender  (vedi scripts/README.md)
    single_fan.py       una faccia estesa
    two_fans.py         due facce estese saldate
    20-fans.py          le 20 facce estese: il poliedro M
    20-fans-bis.py      variante con animazione
test/                   test di non regressione (unittest)  (vedi test/README.md)
trash/                  materiale sperimentale/scartato
```

Le librerie `geometry` ed `extended_face` sono **pure** (nessuna dipendenza da
Blender) e testate; `bl_utils` richiede `bpy` e gira solo dentro Blender.

## Eseguire in Blender

1. Lancia Blender (5.x) e cancella il cubo iniziale.
2. Vai nel tab **Scripting** (ultimo tab in alto).
3. Nell'editor di testo a destra premi **Open** (o `Alt+O`) e carica uno script
   da `src/scripts/`, ad esempio `20-fans.py` per vedere il poliedro M. Il file
   dev'essere salvato su disco: lo script ricava da solo la cartella `../libs`.
4. Dai **Run Script** (`Alt+P` o il bottone ▶ sopra l'editor).
5. Se tutto va bene compare il modello nella finestra 3D.

Dettagli sull'esecuzione degli script in [`src/scripts/README.md`](src/scripts/README.md).

Al modello è associato un materiale, ma il colore è ancora bianco: nel video la
texture era stata assegnata manualmente, estraendola dalla foto del dipinto.

## Eseguire i test

Non richiedono dipendenze oltre a `numpy` (usano `unittest` della stdlib):

```
python -m unittest discover -s test -t test -v
```

Dettagli in [`test/README.md`](test/README.md).
