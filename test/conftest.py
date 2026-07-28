"""
Configurazione per pytest (facoltativo).

I test sono scritti con `unittest` e girano gia' con la sola libreria standard:

    python -m unittest discover -s test -v

Se invece si usa pytest, questo file assicura che `src/` sia sul sys.path prima
della raccolta dei test, esattamente come fa `context.py`.
"""

import context  # noqa: F401  (l'import ha come effetto collaterale di sistemare il path)
