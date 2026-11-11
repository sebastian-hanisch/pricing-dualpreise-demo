"""Szenarien: das Handbeispiel (7 Kunden, feste ganze Zahlen) und die Solomon-artigen Kundeninstanzen (selbst erzeugt, nicht die Originalinstanzen).

Beide sind reine Daten ohne Rechenregel. Der Zufall der Kundeninstanzen kommt über einen übergebenen Generator (`pdp_rng.SplitMix64`),
nie aus einem Modul-Global. Knoten 0 ist das Depot, die Kunden sind 1 bis n.

Zeit = Entfernung = Kosten (Fahrzeit und Kosten sind gleich), Bedienzeit `svc`, Fenster [ready, due] für den **Beginn der Bedienung**
(früher ankommen heißt warten, später ankommen ist unzulässig), Last `dem` gegen Kapazität `Q`, Rückkehr zum Depot bis `H`."""

import math
from dataclasses import dataclass

import pdp_constants as C
from pdp_rng import SplitMix64


@dataclass(frozen=True)
class Instanz:
    pts: tuple                  # Lage von Depot und Kunden
    d: tuple                    # Entfernungsmatrix (= Fahrzeit = Kosten)
    dem: tuple                  # Last je Knoten (Depot 0)
    ready: tuple                # frühester Beginn der Bedienung (Depot 0)
    due: tuple                  # spätester Beginn der Bedienung (Depot: H)
    H: float                    # Rückkehr zum Depot bis H
    Q: float                    # Kapazität
    svc: float                  # Bedienzeit je Kunde
    breite: float = 0.0         # Fensterbreite, aus der die Fenster erzeugt wurden (0 beim Handbeispiel)

    @property
    def n(self) -> int:
        """Zahl der Kunden (ohne Depot)."""
        return len(self.pts) - 1


# --- Handbeispiel: das gemeinsame Handbeispiel der Linie -------------------------------------------------------------------------------------
# Depot (0, 0) und 7 Kunden, Entfernung = Fahrzeit = Kosten = Manhattan-Abstand, Bedienzeit 2, Kapazität 6, Rückkehr bis 38.
HAND_PUNKTE = ((0, 0), (-1, 2), (0, 3), (-3, -2), (-1, -2), (-2, -1), (2, 1), (3, 2))
HAND_LAST = (0, 1, 3, 3, 3, 1, 1, 2)
HAND_FENSTER = ((0, 38), (18, 28), (3, 16), (5, 15), (20, 28), (3, 12), (11, 21), (8, 20))   # (früh, spät) je Knoten
HAND_H, HAND_Q, HAND_SVC = 38, 6, 2


def handbeispiel() -> Instanz:
    pts = HAND_PUNKTE
    d = tuple(tuple(abs(a[0] - b[0]) + abs(a[1] - b[1]) for b in pts) for a in pts)
    return Instanz(pts, d, HAND_LAST, tuple(f[0] for f in HAND_FENSTER), tuple(f[1] for f in HAND_FENSTER), HAND_H, HAND_Q, HAND_SVC)


# --- Kundeninstanzen im Solomon-Stil ---------------------------------------------------------------------------------------------------------

def make_instanz(n: int, rng, breite: float, typ: str = "zufaellig", H: float = C.HORIZONT, Q: float = C.KAPAZITAET, svc: float = C.BEDIENZEIT) -> Instanz:
    """Depot in der Mitte (50, 50), n Kunden im Quadrat 100 x 100 („zufaellig“ gleichverteilt, „gruppiert“ um fünf Zentren), Last 5 bis 25 je Kunde.

    Fenster: Mittelpunkt gleichverteilt zwischen frühester und spätester möglicher Ankunft, Breite `breite`, auf den möglichen Bereich beschnitten.
    Reihenfolge der Zufallszahlen: Lage (bei „gruppiert“ zuerst die fünf Zentren), dann alle Lasten, dann alle Fenster. Der Generator kommt von außen."""
    if typ == "gruppiert":
        zentren = [(rng.uniform(15, 85), rng.uniform(15, 85)) for _ in range(5)]
        kunden = []
        for _ in range(n):
            cx, cy = zentren[rng.wahl(5)]
            kunden.append((min(100.0, max(0.0, rng.gauss(cx, 6))), min(100.0, max(0.0, rng.gauss(cy, 6)))))
    elif typ == "zufaellig":
        kunden = [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(n)]
    else:
        raise ValueError(f"unbekannter Typ {typ!r}")
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


def instanz_aus_seed(n: int, seed: int, breite: float, typ: str = "zufaellig", H: float = C.HORIZONT, Q: float = C.KAPAZITAET) -> Instanz:
    """Dieselbe Eingabe gibt immer dieselbe Instanz (SplitMix64 mit dem Zufalls-Seed)."""
    return make_instanz(n, SplitMix64(seed), breite, typ, H, Q)


def einzelfahrt_preise(inst: Instanz) -> tuple:
    """Dualpreise der ersten Runde: nur die Einzelfahrten 0-j-0 stehen im Master, jede Zeile bindet, der Dualpreis ist ihre Kosten 2 d(0, j). Index 0 = Depot (0)."""
    return (0.0,) + tuple(2.0 * inst.d[0][j] for j in range(1, inst.n + 1))
