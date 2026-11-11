"""Der Instanzgenerator der früheren Vormessung (Pythons `random.Random`), nachgebaut für die Gegenprobe gegen deren Zahlen.

Die Demo selbst erzeugt Instanzen mit SplitMix64 (`pdp_scenario.make_instanz`); die frühere Messreihe benutzte `random.Random(seed)`. Mit diesem Nachbau lässt sich
der Kern der Demo auf genau den früheren Instanzen laufen lassen (`tests/test_claims.py`, Gegenprobe). Die Reihenfolge der Zufallszahlen ist dieselbe wie dort."""

import math
import random

from pdp_scenario import Instanz


def alte_instanz(n: int, seed: int, breite: float, H: float = 300.0, Q: float = 70, svc: float = 10.0, gruppiert: bool = False) -> Instanz:
    rng = random.Random(seed)
    if gruppiert:
        zentren = [(rng.uniform(15, 85), rng.uniform(15, 85)) for _ in range(5)]
        kunden = []
        for _ in range(n):
            cx, cy = rng.choice(zentren)
            kunden.append((min(100.0, max(0.0, rng.gauss(cx, 6))), min(100.0, max(0.0, rng.gauss(cy, 6)))))
    else:
        kunden = [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(n)]
    pts = ((50.0, 50.0),) + tuple(kunden)
    d = tuple(tuple(math.dist(a, b) for b in pts) for a in pts)
    dem = (0,) + tuple(rng.randint(5, 25) for _ in range(n))
    ready, due = [0.0], [float(H)]
    for i in range(1, n + 1):
        lo = d[0][i]
        hi = H - svc - d[0][i]
        c = rng.uniform(lo, hi)
        ready.append(max(lo, c - breite / 2))
        due.append(min(hi, c + breite / 2))
    return Instanz(pts, d, dem, tuple(ready), tuple(due), float(H), float(Q), float(svc), float(breite))
