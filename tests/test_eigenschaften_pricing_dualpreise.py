"""Eigenschaftstests (ORACLE-PLAYBOOK §5.2): Aussagen, die für das Verfahren gelten müssen, ohne dass man das richtige Ergebnis kennt.

Master-Wert fällt je Runde nie; alle angehängten Spalten sind zulässig; zusätzliche Spalten, breitere Fenster und größere Kapazität verschlechtern die Schranke nie; ein größeres
Gedächtnis k gibt eine höhere oder gleiche Schranke; Umnummerieren der Kunden ändert die Schranke nicht; die Glättung ändert die Schranke nie; gleicher Zufalls-Seed gleiche Ausgabe,
auch in einem zweiten Prozess mit anderem Hash-Seed. Jede Eigenschaft gilt an 6 bis 20 festen Instanzen (kleine, damit die Datei unter 10 Sekunden bleibt)."""

import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

import pdp_algorithm as A
import pdp_colgen as G
import pdp_scenario as S
from pdp_master import loese_master
from pdp_scenario import Instanz

ROOT = Path(__file__).resolve().parent.parent


def _umnummeriert(inst: Instanz, perm) -> Instanz:
    """Dieselbe Instanz mit anderer Kundennummerierung: neuer Index i' = perm[i - 1] (perm ist eine Permutation von 1 bis n)."""
    n = inst.n
    neu = [0] * (n + 1)                        # neu[i'] = alter Index
    for alt, i in enumerate(perm, 1):
        neu[i] = alt
    idx = neu
    return Instanz(tuple(inst.pts[a] for a in idx), tuple(tuple(inst.d[a][b] for b in idx) for a in idx), tuple(inst.dem[a] for a in idx),
                   tuple(inst.ready[a] for a in idx), tuple(inst.due[a] for a in idx), inst.H, inst.Q, inst.svc, inst.breite)


@pytest.mark.parametrize("k", [None, 5])
def test_master_value_never_rises_and_every_new_column_is_feasible(k):
    for seed in range(10):
        inst = S.instanz_aus_seed(10, seed, 100)
        lauf = G.spaltenerzeugung(inst, k)
        werte = [r.master_wert for r in lauf.runden]
        assert all(b <= a + 1e-7 for a, b in zip(werte, werte[1:])), seed
        assert werte[0] == pytest.approx(sum(2 * inst.d[0][j] for j in range(1, 11)))        # Runde 1: Summe der Einzelfahrten
        for r in lauf.runden:
            for spalte in r.neue:
                assert A.pruefe_route(inst, spalte, elementar=k is None)[0], (seed, spalte)
                assert A.reduzierte_kosten(inst, r.pi, spalte) < -1e-7


def test_adding_columns_never_worsens_the_master():
    for seed in range(8):
        inst = S.instanz_aus_seed(7, seed, 100)
        rng = random.Random(seed)
        alle = A.alle_zulaessigen_wege(inst)
        teil = [(j,) for j in range(1, 8)] + rng.sample(alle, min(10, len(alle)))
        mehr = teil + rng.sample(alle, min(10, len(alle)))
        assert loese_master(inst, mehr).wert <= loese_master(inst, teil).wert + 1e-7


def test_wider_windows_and_a_larger_capacity_never_raise_the_bound():
    for seed in range(6):
        eng = G.spaltenerzeugung(S.instanz_aus_seed(8, seed, 40), None).schranke
        weit = G.spaltenerzeugung(S.instanz_aus_seed(8, seed, 100), None).schranke
        gross = G.spaltenerzeugung(S.instanz_aus_seed(8, seed, 100, Q=120), None).schranke
        assert weit <= eng + 1e-6 and gross <= weit + 1e-6, seed


def test_a_larger_memory_gives_a_higher_or_equal_bound():
    for seed in range(8):
        inst = S.instanz_aus_seed(8, seed, 100)
        b1, b3, b8 = (G.spaltenerzeugung(inst, k).schranke for k in (1, 3, 8))
        assert b1 <= b3 + 1e-6 <= b8 + 2e-6, seed
        assert b8 == pytest.approx(G.spaltenerzeugung(inst, None).schranke, abs=1e-6)             # k = n ist elementar


def test_renumbering_the_customers_does_not_change_the_bound():
    for seed in range(8):
        inst = S.instanz_aus_seed(8, seed, 100)
        perm = random.Random(seed).sample(range(1, 9), 8)
        b0 = G.spaltenerzeugung(inst, None).schranke
        b1 = G.spaltenerzeugung(_umnummeriert(inst, perm), None).schranke
        assert b1 == pytest.approx(b0, abs=1e-6), seed


def test_renumbering_keeps_the_label_counts_of_the_labeling_up_to_ties_and_the_best_route_value():
    for seed in range(8):
        inst = S.instanz_aus_seed(8, seed, 100)
        pi = tuple(0.0 if j == 0 else 1.7 * inst.d[0][j] for j in range(9))
        perm = random.Random(seed + 100).sample(range(1, 9), 8)
        inst2 = _umnummeriert(inst, perm)
        pi2 = [0.0] * 9
        for alt, i in enumerate(perm, 1):
            pi2[i] = pi[alt]
        a, b = A.labeling(inst, pi, None), A.labeling(inst2, tuple(pi2), None)
        assert a.wege[0][0] == pytest.approx(b.wege[0][0], abs=1e-9) and len(a.wege) >= 1
        assert len(a.wege) == pytest.approx(len(b.wege), abs=max(3, 0.2 * len(a.wege)))         # Gleichstände können andere Labels dominieren, die Routen bleiben fast alle


@pytest.mark.parametrize("alpha", [0.5, 0.8, 0.9])
def test_smoothing_never_changes_the_bound(alpha):
    for seed in range(6):
        inst = S.instanz_aus_seed(10, seed, 100)
        assert G.spaltenerzeugung(inst, 5, alpha=alpha).schranke == pytest.approx(G.spaltenerzeugung(inst, 5).schranke, abs=1e-6), seed


def test_smoothing_with_a_positive_alpha_differs_from_no_smoothing_on_some_instance():
    """Zweig-Test: die Glättung wirkt (mehr Pricing-Aufrufe), sonst wäre der Schalter tot."""
    unterschied = 0
    for seed in range(6):
        inst = S.instanz_aus_seed(10, seed, 100)
        a, b = G.spaltenerzeugung(inst, 5, alpha=0.8), G.spaltenerzeugung(inst, 5)
        unterschied += (a.aufrufe, a.anzahl_runden) != (b.aufrufe, b.anzahl_runden)
    assert unterschied >= 1


def test_the_partition_master_equals_the_cover_master_for_metric_costs_in_the_column_generation():
    for seed in range(6):
        inst = S.instanz_aus_seed(8, seed, 100)
        assert G.spaltenerzeugung(inst, None, "partition").schranke == pytest.approx(G.spaltenerzeugung(inst, None).schranke, abs=1e-6), seed


SKRIPT = """
import sys
sys.path.insert(0, {root!r})
import pdp_scenario as S, pdp_algorithm as A, pdp_colgen as G
inst = S.instanz_aus_seed(9, 11, 100)
pi = S.einzelfahrt_preise(inst)
e = A.labeling(inst, pi, 5)
lauf = G.spaltenerzeugung(inst, 5)
print(e.erzeugt, e.dominiert, e.wege[0], round(lauf.schranke, 6), len(lauf.spalten), lauf.labels)
"""


def test_same_seed_same_output_in_a_second_process_with_another_hash_seed():
    ausgaben = []
    for hashseed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=hashseed)
        p = subprocess.run([sys.executable, "-c", SKRIPT.format(root=str(ROOT))], capture_output=True, text=True, env=env, timeout=120)
        assert p.returncode == 0, p.stderr[-500:]
        ausgaben.append(p.stdout)
    assert ausgaben[0] == ausgaben[1] and ausgaben[0].strip()
