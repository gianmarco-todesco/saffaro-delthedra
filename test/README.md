# Test

Test di non regressione per `src/geometry.py`. Fanno anche da esempio d'uso
della libreria (vedi in particolare `test_usage.py`).

Non richiedono dipendenze oltre a `numpy`: usano il modulo `unittest` della
libreria standard.

## Eseguire i test

Dalla radice del progetto:

```
python -m unittest discover -s test -t test -v
```

Oppure un singolo file:

```
python -m unittest test.test_vector -v
```

Se hai `pytest` installato funziona anche quello (`conftest.py` sistema il path):

```
pytest test -v
```

## Contenuto

| file                 | copre                                             |
|----------------------|---------------------------------------------------|
| `test_vector.py`     | classe `Vector` (algebra, metriche, cross)        |
| `test_matrix.py`     | `apply_matrix`, `matrix_from_triples`             |
| `test_polyhedron.py` | `Polyhedron`, `make_icosahedron`, `Polyhedron.ico`|
| `test_misc.py`       | `compute_angle_from_sides`, `MeshData`            |
| `test_usage.py`      | pattern d'uso reali (stile `20-fans.py`, `prova2.py`) |
| `test_extended_face.py` | faccia estesa di M: triangoli equilateri, reparametrizzazione `a`, chiusura di M |
| `test_pieces.py`     | M come 240 pezzi rigidi, la griglia, `face_planes`/`enclosing_scale`/`core_scale` |

`context.py` mette `src/libs/` sul `sys.path`; ogni test fa `from context import geometry`.
