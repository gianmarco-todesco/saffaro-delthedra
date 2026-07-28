"""
Bootstrap del path per i test.

Le librerie vivono in `src/libs/` e vengono importate dagli script Blender con
`import geometry` (cioè `src/libs/` sul sys.path, non come package). Qui
riproduciamo la stessa condizione aggiungendo `src/libs/` in testa al path, così
i test importano esattamente i moduli che usa il resto del progetto.

Ogni file di test fa `from context import ...` (oppure `import context`) come
prima riga utile.
"""

import os
import sys

LIBS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "libs"
)
if LIBS_DIR not in sys.path:
    sys.path.insert(0, LIBS_DIR)

import geometry  # noqa: E402  (import dopo la modifica del path: voluto)
