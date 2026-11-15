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
`src/scripts/` (prima), `v2/`, `v3/` (esperimenti), `v4/`, `v5/` (quella in corso, appena cominciata con scene-2).
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

**Non ancora committati:** `src/scripts/v4/scene-6.py` (nuovo), `src/scripts/v5/scene-2.py` (nuovo), `src/scripts/draft5/scene-1.py`, `scene-2.py` e `scene-3.py` (nuovi), la riga di
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

### draft5/scene-1.py (2026-11-14)

Cartella `src/scripts/draft5/` (l'utente l'ha creata come `draft4` e poi
rinominata), per il prossimo montaggio. `scene-1.py`
parte da v4/scene-1 (prefisso `S1D5`, collezione `scene-1_draft5`). Richieste dell'utente:

- bagliore della sezione molto piu' brillante: `LINE_STRENGTH` 1,0 (era
  0,3), `GLOW_GAIN` 100 (14), `GLARE_STRENGTH` 2,0 (0,4). Poi l'utente ha
  voluto i segmenti molto piu' sottili: `LINE_RADIUS` 0,004 (0,01),
  l'alone stretto `GLOW_SOFTEN` 3 px peso 0,3 (con 12 px a peso 1 la linea
  diventava una fascia bianca larga); il bloom largo resta.
- il movimento del quadro (`PaintingPath`), descritto dall'utente: la
  camera e' ferma in eye1; il quadro arretra in linea retta lungo l'asse e
  poi il centro passa su un arco di cerchio raccordato (tangente e velocita'
  continue), il quadro sempre perpendicolare alla tangente. Una sola legge
  oraria sulla strada intera, da ferma a ferma (smootherstep): 10:00-11:00.
  Solo quando il quadro e' fermo M lo buca e ne esce perpendicolare
  (11:00-12:00, ease-in/out): e' tutto fuori a 11,62 s, la linea della
  sezione dura da 11,12 a 11,58 s. A 12:00 M e' al centro e comincia a
  girare (ease-in, `SPIN_RAMP`); il quadro svanisce 12-13,5. m_end e eye1
  sono quelli di v4: il raccordo con v4/scene-2 e v5/scene-2 regge.
- calibrazione: la posa finale del quadro e' fissata da m_end e da quanto M
  si allontana (`PAINT_EXTRA`, calibrato perche' le sagome alla fine siano
  staccate del 2%). A 60 gradi l'arco dovrebbe cominciare prima del punto di
  partenza del quadro (nessuna retta), quindi l'angolo lo sceglie lo script
  (`PAINT_TILT` None, `PAINT_MIN_STRAIGHT` 0,6): viene 73 gradi, M si
  allontana 1,45 piu' che in v4, retta 0,64, arco di raggio 4,78.
- tempi (2026-11-15, secondi:fotogrammi), sulla voce delle 13:21 di 39,97 s
  (`draft-5/scene-1/scene-1-voice.mp3`; le versioni precedenti sono i
  `-old*.mp3`; il testo ha una frase in piu', "Il quadro ce lo mostra da un
  solo punto di vista: giriamogli intorno.", detta fra 10,9 e 15,3 s mentre
  il quadro gira e M esce): il quadro si allontana 0-10:04 e gira
  10:04-12:04, M esce 12:04-15:20 (il piu' lento possibile, chiesto
  dall'utente: finisce mezzo secondo dopo "giriamogli intorno") e allora
  comincia a girare, il quadro svanisce 15:20-17:08; M cresce 16:20-23:22;
  icosaedro 24:02, facce 27:18, M 30:23, migrazione 35:03-39:15 (la voce
  finisce a 39,63), fine a 40:15 (fotogrammi 1-976): un secondo di pausa
  sulla griglia, chiesto dall'utente. L'mp3 ha solo 0,34 s di silenzio in
  fondo, quindi il video e' 0,66 s piu' lungo della voce. Le pause della
  voce si misurano con `ffmpeg -af silencedetect=noise=-35dB:d=0.25`.
- l'allontanamento del quadro fin dall'inizio (chiesto il 2026-11-15, c'era
  in v4 come arretramento della camera): da `DRIFT_FROM` = 0 a `PAINT_MOVE`
  il quadro fa `DRIFT_PART` = tutta la retta, partendo da fermo con
  accelerazione uniforme; poi un raccordo cubico (`hermite`) fino alla fine
  dell'arco. La retta e' corta (0,64): il quadro passa dal 100% al 93%
  dell'altezza dell'immagine (in v4 arrivava al 91%). Per farlo allontanare
  di piu' si alza `PAINT_MIN_STRAIGHT`, ma allora il quadro gira di piu'.
- il percorso del quadro (rifatto il 2026-11-15 su indicazione dell'utente):
  la retta e' l'asse della camera, quindi il quadro resta perfettamente
  centrato mentre si allontana (al primo fotogramma ne riempie l'altezza);
  l'arco, orizzontale, e' tangente all'asse. M sta dietro il centro del
  disegno (che e' 0,284 sopra il centro del quadro) ed esce perpendicolare
  al quadro fino a `m_target`: al centro dell'immagine in orizzontale, alla
  profondita' di m_end, ma 0,284 piu' in alto (3,9% dell'altezza
  dell'immagine), perche' il quadro gira solo attorno alla verticale.
  Durante `GROW` M scende in m_end insieme alla crescita (`path.lift`); da
  li' la scena e' quella di prima. Retta 0,61, arco di raggio 4,81, 73 gradi.
  (Una versione intermedia, con il quadro che scivolava di lato verso il suo
  vecchio posto, e' stata scartata.)
- M cresce (chiesto il 2026-11-15): `GROW` 16:20-23:22, `GROW_FACTOR` 1,25,
  smootherstep, sulla scala di `mover`. La sfera di M passa dal 56% al 71%
  dell'altezza dell'immagine, quella dell'icosaedro arriva all'84%. La
  griglia finale non cambia, quindi nemmeno il raccordo con scene-2.

Da guardare: mentre gira, M (attaccato al
quadro) va fin quasi al bordo destro e poi torna al centro uscendo. La
versione precedente (quadro che scivola nel suo piano) e' stata scartata.

### draft5/scene-3.py (2026-11-14)

Copia di v4/scene-3 (prefisso `S3D5`), tempi e movimenti invariati. Cambi
chiesti dall'utente: i sei deltaedri compaiono da sinistra a destra
nell'immagine (scala 0->1, stesso intervallo di v4); stile di draft5/scene-2:
scheletri (cilindretti e sferette, `TUBE_RADIUS`) con facce di vetro
emissivo sempre trasparenti (`FACE_OPACITY`, `FACE_GLOW`), un colore per
solido: catene rosse come il tetraedro di scene-2 (`CHAIN_LCH`), gli altri
`story.pastel` con le tinte di `OTHERS`. Per il vetro le facce interne delle
catene non si disegnano (`tetra_faces`: base solo sul primo, cima solo
sull'ultimo; spigoli solo quelli nuovi); la cima di una copia, finche' il
tetraedro nuovo non esce, la chiude un coperchio (`lid`). Il composto ora
cresce tutto insieme dal piede (scala sul perno della catena 0): in v4 ogni
tetraedro cresceva per conto suo. I materiali hanno tutti il nodo Global
(dissolvenza finale) per la proprieta' `alpha` dell'oggetto.

Cambi del 2026-11-15: le catene non sono piu' rosse. Il composto e' giallo
chiaro (`CHAIN_FIRST_LCH` 0,92 / 0,10 / 100) e le catene vanno, una tinta
per catena, fino all'azzurro chiaro (`CHAIN_LAST_LCH` 0,86 / 0,08 / 230),
raggiunto dall'ultima catena nata prima della dissolvenza finale
(`hue_at`); in mezzo passano per un verde acqua. Ogni catena ha i suoi
materiali; la copia nasce col colore della catena da cui viene e passa al
suo mentre si sposta (`tint_keys`, un keyframe per fotogramma sul nodo
`Tint`, interpolato in OKLCH). Corretto anche un difetto che c'era gia':
nel fotogramma di ogni sdoppiamento la copia, trasparente e coincidente con
l'originale, lo faceva sparire (Cycles salta le facce coincidenti); ora la
copia e il suo coperchio compaiono un fotogramma dopo. La stella (`OTHERS["stella"]`) e' passata dal giallo al corallo
(tinta 25), perche' non si confonda col composto.

### draft5/scene-4.py (2026-11-15)

Copia di v4/scene-4 (prefisso ancora `S4V4`). Unico cambio: sferette dei
vertici piu' piccole, `VERTEX_RADIUS` 0,042 (era 0,055). La punta delle
frecce si calcola con `ARROW_CLEAR_RADIUS` 0,055, cioe' come prima: con
il raggio nuovo le scritte si avvicinavano ai poliedri e la scelta
automatica delle scritte del composto ne prendeva una con una
sovrapposizione. Cosi' frecce e scritte restano dove erano.

### draft5/scene-2.py (2026-11-14)

Copia di v5/scene-2 (prefisso `S2D5`) con due cambi chiesti dall'utente:
le facce degli otto restano trasparenti anche dove le prende il sole
(`glass_material`: trasparente + emissione del colore, `FACE_GLOW`, mescolati
dal nodo Fade a `FACE_OPACITY`; in v5 il Principled illuminato sembrava
opaco), e il tetraedro sta come una piramide, con una faccia sul pavimento
(`base_down`, al posto di `TETRA_TILT`). I fili restano illuminati.
Alla fine, invece del fade-out di v5, gli otto rimpiccioliscono (scala da
1 a 0) nell'ultimo mezzo secondo, scaglionati da sinistra a destra, ognuno
in 0,25 s, restando appoggiati al pavimento (`SHRINK_OUT`,
`SHRINK_SECONDS`, `shrink_keys`).

Cambi del 2026-11-15, sulla voce (`draft-5/scene-2/scene-2-voice.mp3`, 36,3
s; nel montaggio comincia esattamente con la scena). Le parole si trovano
dall'inviluppo dell'energia (pacchetti di 20 ms): "icosaedro" 5,55-6,25,
"M" 6,5-6,9, "tetraedro" 12,64-13,4. L'utente aveva stimato 3:16 e 4:15
per i primi due: si sono usati i tempi misurati.
- `PAIR_GROW` 2,5 s (era 2), `PAIR_DONE`: icosaedro intero a 5:22, M a 6:18.
- `SPLIT` 12:02-14:02 (la coppia esce, ease-in), `TETRA_IN` 12:16-13:16,
  `FLOOR_IN` 8:18-11:18 e `FLOOR_SETTLE` 11:18-12:12: il pavimento e' fermo
  prima che il tetraedro compaia.
- `HOVER` 0,12 raggi: gli otto sospesi sopra il pavimento (le ombre di un
  pezzo appoggiato non erano belle); anche rimpicciolendo alla fine il punto
  piu' basso resta a quella quota.
- `TRIO_RATIO` 1,65 (era `INNER_RATIO` 1,45, che resta per il gruppo di
  destra): i tre platonici piu' distanti. Prima il triangolo sembrava
  isoscele perche' il tetraedro, con la base in basso, sembra piu' alto del
  suo centro: ora ogni platonico e' messo perche' il suo centro visivo (il
  centro del rettangolo che lo contiene nell'immagine, in media sul giro;
  `visual_offset`, `place_visual`) stia al vertice del triangolo
  equilatero. Lati 2,86 raggi. Anche il tetraedro che cresce al centro e'
  centrato cosi'. I due piu' vicini nell'immagine sono ottaedro e
  bipiramide pentagonale, staccati di 0,40 raggi.
- Raccordo verificato: l'ultimo fotogramma di draft5/scene-1 e il primo di
  questa, resi allo stesso modo, differiscono al massimo di 9 su 255 (rumore).

### v5/scene-2.py (2026-11-08)

Prima scena della versione 5: parte da `v4/scene-2.py` (che resta com'e') e
si raccorda come lei con la fine di `v4/scene-1.py`. Prefisso `S2V5`. I tempi
li ha dati l'utente in secondi:fotogrammi (`tc(s, f)` nello script), 36:21 in
tutto, fotogrammi 1-886: triangoli via in 0,3-4,3 s; icosaedro intero a 4, M
a 4,5; pavimento da 10 (sale fino a 13, si ferma a 13,75); tetraedro intero
a 12:19, mentre M e l'icosaedro escono nei 2 s prima; ottaedro entra a 17:21,
icosaedro a 18:20 (l'inizio dello scivolamento, che dura 1,8 s); gli altri
cinque crescono da 28:21 a 0,25 s l'uno dall'altro, prima le bipiramidi.

I tre platonici ora finiscono col centro al centro dell'immagine
(`TRIO_CENTERED`); gli altri cinque stanno rispetto a loro come in v4, e per
ora non si spostano (scelta dell'utente). Il gruppo di destra usciva un poco
dall'immagine (+1,03 della mezza larghezza): l'utente l'ha fatto spostare a
sinistra e piu' lontano sul pavimento, cioe' piu' in alto nell'immagine
(`RIGHT_SHIFT` = (-0,7, 0,6) raggi dei pezzi), e la bipiramide pentagonale
un po' a sinistra (`PENTBI_SHIFT` = -0,4 raggi); ora la fila va da -0,73 a
+0,93. L'utente ha approvato la disposizione finale.

Nell'ultimo secondo (35:21-36:21) gli otto spariscono con un fade-out,
scaglionato da sinistra a destra secondo la x nell'immagine (`FADE_OUT`,
`FADE_SECONDS` 0,5, `fade_out_start`): facce e fili hanno il nodo Fade
(i fili ora sono `fading_material`), e con loro svaniscono le ombre. Il
pavimento resta.

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
