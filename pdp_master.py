"""Der Master der Spaltenerzeugung: ein LP über die bisher bekannten Routen (Spalten), gelöst mit scipy/HiGHS.

Überdeckung: jeder Kunde mindestens einmal, `min c x` mit `A x >= 1`. Partitionierung: jeder Kunde genau einmal, `A x = 1`. Die **Dualpreise** sind die Schattenpreise der
Kunden-Zeilen; ihr Vorzeichen ist hier an den Handwerten geprüft (`tests/test_algorithm.py`): bei der Überdeckung `-ineqlin.marginals`, bei der Partitionierung `eqlin.marginals`.

scipy wird erst in der Funktion importiert (kürzerer Kaltstart der App)."""

from dataclasses import dataclass

import numpy as np

from pdp_algorithm import route_kosten
from pdp_scenario import Instanz


@dataclass(frozen=True)
class MasterErgebnis:
    wert: float                 # Zielwert des Masters
    pi: tuple                   # Dualpreise, Index 0 = Depot (0)
    x: tuple                    # Menge je Spalte (gleiche Reihenfolge wie die Spalten)


def spaltenmatrix(inst: Instanz, spalten) -> np.ndarray:
    """Zeile = Kunde 1 bis n, Spalte = Route; ein Eintrag zählt, wie oft die Route den Kunden besucht."""
    A = np.zeros((inst.n, len(spalten)))
    for c, r in enumerate(spalten):
        for j in r:
            A[j - 1, c] += 1
    return A


def loese_master(inst: Instanz, spalten, art: str = "ueberdeckung") -> MasterErgebnis:
    """Löst den Master über die Spalten. `art`: „ueberdeckung“ oder „partition“. Löst HiGHS nicht bis zum Optimum, gibt es einen RuntimeError mit dem Status."""
    from scipy.optimize import linprog

    A = spaltenmatrix(inst, spalten)
    c = [route_kosten(inst, r) for r in spalten]
    if art == "ueberdeckung":
        res = linprog(c, A_ub=-A, b_ub=-np.ones(inst.n), bounds=(0, None), method="highs")
    elif art == "partition":
        res = linprog(c, A_eq=A, b_eq=np.ones(inst.n), bounds=(0, None), method="highs")
    else:
        raise ValueError(f"unbekannte Art {art!r}")
    if res.status != 0:
        raise RuntimeError(f"Master nicht gelöst (Status {res.status}: {res.message})")
    duals = -res.ineqlin.marginals if art == "ueberdeckung" else res.eqlin.marginals
    return MasterErgebnis(float(res.fun), (0.0,) + tuple(float(p) for p in duals), tuple(float(v) for v in res.x))
