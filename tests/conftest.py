"""Gemeinsame Fixtures: das Handbeispiel von Hand (DEMO-PLAYBOOK §1b), unabhängig vom Szenario-Modul noch einmal hingeschrieben.

Das Handbeispiel (Tabelle der Aufgabe): Depot (0, 0) und 7 Kunden, Entfernung = Fahrzeit = Kosten = Manhattan-Abstand, Bedienzeit 2, Kapazität 6, Rückkehr bis 38.
Die erwarteten Werte stehen in den Tests als Rechnung (Summen, Differenzen), nicht als abgeschriebene Ergebnisse des Codes. Ein Test prüft, dass das Szenario-Modul
dieselben Zahlen enthält."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pdp_scenario import Instanz  # noqa: E402

# Kunde: Lage, Last, Fenster (Beginn der Bedienung), laut Tabelle der Aufgabe
HAND_TABELLE = {
    1: ((-1, 2), 1, (18, 28)),
    2: ((0, 3), 3, (3, 16)),
    3: ((-3, -2), 3, (5, 15)),
    4: ((-1, -2), 3, (20, 28)),
    5: ((-2, -1), 1, (3, 12)),
    6: ((2, 1), 1, (11, 21)),
    7: ((3, 2), 2, (8, 20)),
}
HAND_SVC, HAND_Q, HAND_H = 2, 6, 38


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def hand_lage(i):
    return (0, 0) if i == 0 else HAND_TABELLE[i][0]


def hand_d(i, j):
    return manhattan(hand_lage(i), hand_lage(j))


@pytest.fixture
def hand():
    """Das Handbeispiel als Instanz, aus der Tabelle oben gebaut (nicht aus pdp_scenario)."""
    pts = tuple(hand_lage(i) for i in range(8))
    d = tuple(tuple(hand_d(i, j) for j in range(8)) for i in range(8))
    dem = (0,) + tuple(HAND_TABELLE[i][1] for i in range(1, 8))
    ready = (0,) + tuple(HAND_TABELLE[i][2][0] for i in range(1, 8))
    due = (HAND_H,) + tuple(HAND_TABELLE[i][2][1] for i in range(1, 8))
    return Instanz(pts, d, dem, ready, due, HAND_H, HAND_Q, HAND_SVC)


@pytest.fixture
def pi_erste_runde():
    """Dualpreise der ersten Runde von Hand: Dualpreis = Kosten der Einzelfahrt = 2 x Abstand zum Depot (Abstände 3, 3, 5, 3, 3, 3, 5)."""
    return (0.0,) + tuple(2.0 * hand_d(0, j) for j in range(1, 8))


def mini_instanz(lagen, dem, fenster, H=100, Q=10, svc=1):
    """Kleine Instanz aus Lagen (Index 0 = Depot, Manhattan), Lasten ab Kunde 1 und Fenstern (früh, spät) ab Kunde 1."""
    d = tuple(tuple(manhattan(a, b) for b in lagen) for a in lagen)
    ready = (0,) + tuple(f[0] for f in fenster)
    due = (H,) + tuple(f[1] for f in fenster)
    return Instanz(tuple(lagen), d, (0,) + tuple(dem), ready, due, H, Q, svc)
