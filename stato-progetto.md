# Stato del progetto (2026-11-08)

Documento di ripresa: serve a far partire una chat nuova senza rileggere tutto.
Va aggiornato quando cambia qualcosa che dai sorgenti non si capisce.

## Che cosa e'

Gli script Blender (5.1) per il video sul poliedro M di Lucio Saffaro e sui
deltaedri. Cos'e' M e come e' organizzato il repository lo dice il
[`README.md`](README.md); che cosa fa ogni script lo dice la tabella in
[`src/scripts/README.md`](src/scripts/README.md), che si tiene aggiornata a ogni
scena nuova o cambiata.

Il video si e' fatto per versioni successive, ognuna in una cartella:
`src/scripts/` (prima), `v2/`, `v3/` (esperimenti), `v4/` (quella in corso).
Una scena nuova parte di solito dalla stessa scena della versione precedente,
che resta com'e'.

Fuori dal repository, nella cartella di sopra (`Projects/saffaro/`): `assets/`
(texture, foto del quadro, il libro), `modelli-3d/` e `3dmodels/` (i deltaedri
in `.obj`), i voiceover, le cartelle `draft-AAAAMMGG` con i montaggi.

## Come si lavora

- Si risponde in italiano, a parole piane.
- **Blender lo lancia l'utente.** Le prove si fanno senza finestra (sotto).
- **Ogni scena usa Cycles a 256 campioni**: `m_scene.use_cycles(scene)` dentro
  `build()`.
- Ogni scena v4 ha nomi propri (prefisso `S6V4`, collezione `scene-6_v4`, ...)
  cosi' tutte possono stare nello stesso `.blend`.
- Niente handler di fotogramma: lo script calcola tutto una volta e lo scrive in
  keyframe e shape key (il perche' e' in testa a `v4/scene-6.py`).
- Commit solo quando l'utente lo chiede, messaggio in italiano, che finisce con
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Quando cambia una scena si corregge la sua riga in `src/scripts/README.md`.

## Prove senza finestra

Blender va chiamato per esteso: ne sono installati quattro (3.5, 4.0, 4.5, 5.1)
e un glob prende il 3.5.

```
"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b --factory-startup --python build_save.py -- <scena.py> <out.blend>
"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b --python cycles_frames.py -- <out.blend> <cartella> 442 476 553
```

I due script d'appoggio, da tenere nella cartella temporanea della chat:

```python
# build_save.py: esegue la scena e salva il .blend
import bpy, sys
argv = sys.argv[sys.argv.index("--") + 1:]
script, out = argv[0], argv[1]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
txt = bpy.data.texts.load(script)
exec(compile(txt.as_string(), script, "exec"), {"__name__": "__main__"})
bpy.ops.wm.save_as_mainfile(filepath=out)
```

```python
# cycles_frames.py: rende i fotogrammi dati a meta' risoluzione, 32 campioni
import bpy, sys, os
argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 32
sc.render.resolution_percentage = 50
for f in [int(x) for x in argv[2:]]:
    sc.frame_set(f); sc.render.filepath = os.path.join(argv[1], f"cy_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
```

Si mettono poi i fotogrammi in un foglio solo e lo si manda all'utente.

I test delle librerie: `python -m unittest discover -s test -t test -v`.

## Dove siamo

Ultimo commit: `b2e3946 Quarta versione degli script` (v4/scene-1 ... scene-5).

**Non ancora committati:** `src/scripts/v4/scene-6.py` (nuovo), la riga di
v4/scene-6 in `src/scripts/README.md` (con la riga di v4/scene-5 corretta) e
questo file.

### v4/scene-6.py

Parte da `v2/scene-6.py`: la faccia dell'icosaedro che diventa un ventaglio di
12 triangoli, i gradi di liberta', le facce A e B che combaciano, M ricomposto.
43 s, 24 fps, fotogrammi 1-1033 (il finale e' passato da 3 a 4 s). I tempi li ha dati l'utente il 2026-11-08
(la scaletta completa e' nel docstring in testa al file e in `BEATS`):

- 0-3 l'icosaedro compare girando (gli spigoli nell'ultimo secondo); 3-4 le
  altre spariscono, A si stacca, la camera e' su A a 4 s.
- 4-10 il ventaglio si forma (fasi 2-5 compresse).
- 10-13 flessione libera (`FLEX_*`, `flex_at`, `flexed`): P3, P7, P11 su e
  giu' sfalsati, angoli fermi. Da 10 a 25 il ventaglio A fa un giro intero sul
  suo asse (`FAN_SPIN_TURNS`, `spin_keys`): deve essere intero, altrimenti il
  lato che si accende non e' quello che tocca B.
- 13-18 la camera resta ferma (scelta dell'utente) e il modello s'inclina
  di 32,6 gradi attorno a P0 di A (`TILT_NAME` padre del pivot, `tilt_matrix`,
  `BELOW_TRACK`), fino a vedere il ventaglio a 75 gradi dall'asse invece di 42
  (`CAMERA_BELOW_DEG`). L'asse di rotazione e' a 4,3 gradi dall'orizzontale
  dell'immagine. Resta inclinato fino a 32 s e torna dritto fra 32 e 35. I tre
  pentagoni compaiono insieme da 14,5 a 16,5 s, come finestrini che si
  chiudono dall'alto in basso (nodi `Reveal` e `Alpha` del materiale, un
  keyframe per fotogramma da `reveal_height`, `PLANE_WIPE_*`). Il lato
  arancio e' il bordo inferiore del vetro: nasce in P3 e si allarga
  scendendo fino a P1-P5 (`chord_height`, `chord_shape(t1, h)`,
  `CHORD_RADIUS` 0,0035). Idea dell'utente, che non era sicuro: e' da
  confermare a vederla.
- 19-25 t1: massimo, minimo, massimo; i piani restano piani.
- 25-26 la camera si allarga (`CAMERA_PAIR` 11,5), entra B col suo triangolo
  arancio (`build_chords`: una mesh, due oggetti, opacita' dalla proprieta'
  `fade<lato>`), i piani svaniscono, compaiono i due assi di simmetria e il
  settore dell'angolo (`build_axes`, `AXIS_*`, `SECTOR_*`). Gli assi vanno 1,3 oltre P0 (circa 0,7 oltre le punte del ventaglio) e finiscono con un cono affilato dello stesso materiale (`ARROW_*`, `_cone`); le punte entrano nel controllo dell'inquadratura. Assi e triangoli
  arancio svaniscono a 29-30. Gli assi si incontrano sempre nel centro del
  poliedro (ogni faccia si muove lungo il proprio asse), quindi il punto non
  si muove nel modello: l'utente si aspettava che si muovesse.
- 26-29 avvicina (fessura, lati in comune accesi), oltre, giusto.
- 29-31 le altre 18 compaiono gia' staccate con ritardo proporzionale alla
  distanza da A (`enter_start`, `ENTER_*`, `APPEAR_SECONDS`, `JOIN_*`) e si
  avvicinano; il pivot riparte con ease-in e gira fino alla fine
  (`pivot_angle`, un keyframe per fotogramma, lineare).
- 35-36 si staccano di `Z_APART`, 36-37 ferme, 37-39 si riuniscono; a 39
  bagliore su tutti i lati di tutte le facce (`glow_keys`). Gli spigoli
  restano fino alla fine (lo `spigoli_via` di v2 non c'e' piu').
- `z_keys(face)` ora e' per faccia.

Pavimento di v4/scene-2 e scene-5 (`FLOOR_*`), orizzontale a `FLOOR_BELOW` =
3,2 sotto il centro; il fondo ora sta a 300 (`BACKGROUND_DEPTH`), dietro
l'orizzonte; sole largo 8 gradi. Le facce non fanno ombra (come nelle altre
scene). Bordo piu' spesso: `TUBE_RADIUS` 0,011 (era 0,0075). Raggi e
spezzata senza riflessi (`WIRE_SPECULAR` 0, `WIRE_ROUGHNESS` 1, `_matte`).
Il punto piu' basso delle facce col modello inclinato e' z = -2,72, sopra il
pavimento (-3,2).

Colori come prima: facce `FACE_SRGB`, pieghe `SPOKE_SRGB`, spezzata
`EDGE_SRGB`. Limite della flessione: poco sopra 15 gradi P2 e P4
non esistono piu', per questo su 11 e giu' 14 (`FLEX_UP_DEG`, `FLEX_DOWN_DEG`).

Verificato (2026-11-08): si costruisce senza errori; M si ricompone con errore
3,45e-07; i pentagoni sono piani a 3e-16; h2 minimo della flessione 0,107;
mentre la camera segue A (e B, e il punto d'incontro degli assi) il margine
minimo dal bordo e' 6,3% (a 25,5 s, con le punte delle frecce), su M intera 5,5% (`check_framing` ora dice anche il fotogramma, e conta B solo da
quando e' grande almeno a meta'). Render di prova di 16 fotogrammi a 32
campioni.

**Aperto, da tarare a occhio:** quanto scende la camera (75 gradi), la
trasparenza dei piani (sembrano piuttosto opachi), la forza del bagliore
finale su tutti i lati, la velocita' del giro del ventaglio (un giro in 15 s)
e del poliedro (un giro ogni 12 s), 25-26 s e' un secondo solo per camera che
si allarga e B che entra.

## Geometria del ventaglio (per non rifarla)

- `extended_face.make_extended_face(phi)` da' 13 vertici: l'indice k (0..11) e'
  il P(k+1) dell'utente, l'indice 12 e' l'apice P0 in (0, 0, cq). Gli angoli P1,
  P5, P9 (indici 0, 4, 8) stanno nel piano z = 0.
- In M, visti da P0, gli angoli stanno a 148 gradi dall'asse, P3/P7/P11 a 54,
  i pari a 88,5.
- `fan_shape(t1, s, a)`: t1 e' il grado di liberta' di M, s la crescita del
  ventaglio, `a` la terna della flessione (si usa solo con s = 0).
- Le forme vanno in shape key con `bake_shapes(obj, frames, key_fn, shape_fn)`:
  la chiave e' la tupla dei parametri, e la terna `a` sta dentro come tupla.
