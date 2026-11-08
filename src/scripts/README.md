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
| `scene_5b.py`      | M_story coi tempi del video (40 s): icosaedro pieno a 5 s, la faccia sola a 8, il ventaglio di 12 a 15, il grado di liberta' fra 17 e 19, A e B saldate a 25; spigoli piu' sottili, i raggi del ventaglio ancora di piu' |
| `v2/scene-1.py`    | scene_1 per la seconda versione del video (28 s): quadro via a 8 s, scheletro a 15, a 20 M lascia il posto alle facce dell'icosaedro, a 22 torna, esplosione in un secondo a 25; senza solidi platonici |
| `v2/scene-2.py`    | scene_2 per la seconda versione (34 s), raccordata con v2/scene-1: tetraedro formato a 17 s, ottaedro a 21, icosaedro a 22, gli altri cinque a 30 |
| `v2/scene-3.py`    | scene_3 per la seconda versione (10 s): i cinque deltaedri di Cundy escono a 3 s, il primo tetraedro a 4, gli altri da 8 |
| `v2/scene-4.py`    | scene_4 per la seconda versione (17 s): scritte da 5 a 10 s, la stella va al suo posto e la platea compare fra 11 e 13 |
| `v2/scene-6.py`    | scene_5b per la seconda versione (43 s): faccia sola a 5 s, 6 triangoli a 11, 12 a 17, grado di liberta' a 22, A e B combaciano a 29, M ricomposto a 32, staccato da 34 a 40 |
| `v2/scene-7.py`    | M al centro dei tredici deltaedri di Saffaro su una spirale, quasi a contatto, la camera che gira stretta attorno a M in prima persona, all'altezza del suo centro, poi resta solo M che riprende i colori del quadro, e il quadro (24 s) |
| `v3/scene1a.py`    | esperimento per l'inizio: M dietro il quadro, con la camera in asse su M, viene avanti e lo attraversa restando identico al poliedro dipinto |
| `v3/scene1b.py`    | esperimento per l'inizio: la camera va di lato, M esce dal quadro in un secondo col contorno della sezione che brilla, poi M e quadro si separano e M gira |
| `v3/scene2b.py`    | v2/scene-2 con M e l'icosaedro che crescono dentro il cerchio lasciato libero dai triangoli, e i deltaedri convessi come scheletri (cilindretti e sferette) con le facce semitrasparenti |
| `v4/scene-1.py`    | la camera arretra dal quadro, il quadro gira su un arco e M ne esce col contorno della sezione che brilla; lo scheletro dell'icosaedro e le sue 20 facce, poi i 240 triangoli migrano uno dopo l'altro nella griglia (36 s) |
| `v4/scene-2.py`    | raccordata con v4/scene-1: i triangoli spariscono, M e l'icosaedro, poi sale dal basso un pavimento inclinato (la camera resta dritta) e i deltaedri convessi ci stanno appoggiati, nella disposizione di v3/scene2b (38 s) |
| `v4/scene-3.py`    | sul pavimento di v4/scene-2 i deltaedri non convessi; poi il composto di tre tetraedri si sdoppia, e ogni copia nuova cresce di un tetraedro, sempre piu' in fretta (17 s) |
| `v4/scene-4.py`    | v2/scene-4 con le sferette sui vertici fin dall'inizio, piu' piccole; i due ai lati escono a 10 s, la stella va nella platea e compaiono gli altri a 13; nell'ultimo secondo svaniscono tutti, uno dopo l'altro (18 s) |
| `v4/scene-5.py`    | il quadro senza il poliedro dipinto, con M che gira al suo posto; dissolvenza, un istante di buio, il libro di Saffaro (Scienza & Tecnica 87/88) che si apre a V e sfoglia fino a 328-329 arretrando; davanti compaiono a 12 s i cinque deltaedri di scene_5a (18 s) |
| `v4/scene-6.py`    | v2/scene-6 con facce azzurre e pieghe scure, 43 s: icosaedro intero a 3 s, faccia inquadrata a 4, ventaglio di 12 a 10; flessione libera (P3, P7, P11 sfalsati, 10-13) mentre il ventaglio comincia a girare sul suo asse (un giro fino a 25); la camera resta ferma e il modello s'inclina attorno a P0 per mostrarlo da sotto, mentre i tre pentagoni trasparenti compaiono insieme come finestrini che si chiudono dall'alto in basso, col bordo inferiore del vetro in arancio sottilissimo che diventa il lato P1-P5 (14,5-16,5), e resta inclinato fino a quando tutte le facce sono unite (32); t1 su e giu' coi piani che restano piani (19-25); B entra col suo triangolo arancio mentre i piani svaniscono, e compaiono i due assi di simmetria, che sporgono oltre i ventagli con una freccia a cono, col settore dell'angolo fra loro (25-26); B combacia con A (26-29, lati in comune accesi); le altre 18 compaiono staccate, sfalsate per distanza da A, e si avvicinano (29-31) mentre M comincia a girare; si staccano un poco (35-37) e si riuniscono a 39 con tutti i lati accesi, e M gira fino a 43; il pavimento delle scene precedenti, bordo piu' spesso, raggi e spezzata senza riflessi |
| `Creating_Helix.py`| lo script dello studente con l'elica di Boerdijk-Coxeter (handler di fotogramma), riferimento per scene_3 |

Materiale scartato/sperimentale sta in [`../../trash`](../../trash).
