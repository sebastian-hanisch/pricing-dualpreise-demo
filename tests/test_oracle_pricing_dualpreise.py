"""Orakel-Tests (ORACLE-PLAYBOOK §5, DEMO-PLAYBOOK §12): Pricing, Master und Dijkstra gegen einen anderen Rechenweg.

* Labeling gegen die Tiefensuche über alle zulässigen elementaren Wege (180 Fälle: 60 Instanzen mit 7 Kunden und 3 Fensterbreiten, zufällige Dualpreise), gegen die zweite Labeling-
  Implementierung mit Mengen und Brüchen (`tests/referenz.py`) und, für ein Gedächtnis k kleiner als n, gegen die Tiefensuche mit der ng-Regel auf dem ganzen Weg.
* Master gegen einen exakten Master mit Brüchen (Simplex nach Bland, kein scipy) und gegen die Aufzählung aller Wege als Spalten; Dualitätszertifikat.
* Spaltenerzeugung gegen den Master über alle Wege, am Handbeispiel Zeile für Zeile gegen die exakte Spaltenerzeugung.
* Dijkstra gegen networkx und gegen die Aufzählung aller einfachen Wege.
Zusammen unter 10 Sekunden; der große Lauf (mehr Instanzen) gehört in den Scratch-Ordner."""

import random
from fractions import Fraction

import numpy as np
import pytest
import referenz as R
from conftest import mini_instanz

import pdp_algorithm as A
import pdp_colgen as G
import pdp_scenario as S
from pdp_master import loese_master, spaltenmatrix

BREITEN = (40, 100, 200)


def _zufalls_preise(inst, rng, hoch=1.5):
    """Zufällige Dualpreise, oft größer als die Entfernungen (viele negative Bögen) und manchmal null."""
    return (0.0,) + tuple(0.0 if rng.random() < 0.15 else rng.uniform(0, 2 * hoch * inst.d[0][j]) for j in range(1, inst.n + 1))


# --- Labeling ----------------------------------------------------------------------------------------------------------------------------------

def test_labeling_equals_depth_first_search_on_180_cases():
    gepruft = 0
    for seed in range(60):
        for breite in BREITEN:
            inst = S.instanz_aus_seed(7, seed, breite)
            pi = _zufalls_preise(inst, random.Random(seed * 3 + breite))
            alle = {w: R.kosten(inst, w) - sum(pi[j] for j in w) for w in R.wege_dfs(inst)}
            erg = A.labeling(inst, pi, None)
            if not alle:
                assert not erg.wege
                continue
            assert erg.wege and erg.wege[0][0] == pytest.approx(min(alle.values()), abs=1e-9), (seed, breite)
            for rc, route in erg.wege:
                assert route in alle and rc == pytest.approx(alle[route], abs=1e-9)
            gepruft += 1
    assert gepruft >= 170


def test_labeling_equals_the_second_implementation_with_sets_and_fractions():
    for seed in range(40):
        inst = S.instanz_aus_seed(7, seed, 100.0)
        rng = random.Random(seed)
        pi = (0,) + tuple(rng.randint(0, 120) for _ in range(7))
        a = A.labeling(inst, pi, None)
        erzeugt, dominiert, route, rc, anzahl, _ = R.labeling_ref(inst, pi)
        assert (a.erzeugt, a.dominiert, len(a.wege)) == (erzeugt, dominiert, anzahl), seed
        if route is not None:
            assert a.wege[0][0] == pytest.approx(float(rc), abs=1e-9)


def test_labeling_at_the_hand_example_equals_the_second_implementation(hand, pi_erste_runde):
    erzeugt, dominiert, route, rc, anzahl, _ = R.labeling_ref(hand, pi_erste_runde)
    a = A.labeling(hand, pi_erste_runde, None)
    assert (a.erzeugt, a.dominiert, a.wege[0][1], len(a.wege)) == (erzeugt, dominiert, route, anzahl) == (56, 20, (2, 7, 6), 35)
    assert rc == -10 and a.wege[0][0] == -10


def _ng_regel_ok(inst, k, weg):
    """Gedächtnis auf dem ganzen Weg: ein Kunde j darf wieder besucht werden, wenn zwischen den beiden Besuchen ein Knoten r kommt, dessen Nachbarschaft j nicht enthält."""
    ng = {j: set(sorted(range(1, inst.n + 1), key=lambda i: (inst.d[j][i], i))[:k]) | {j} for j in range(1, inst.n + 1)}
    j = weg[-1]
    for p in range(len(weg) - 2, -1, -1):
        if weg[p] == j:
            return any(j not in ng[weg[r]] for r in range(p + 1, len(weg) - 1))
    return True


def _wege_ng(inst, k):
    out = []

    def rec(weg, zeit, last):
        i = weg[-1] if weg else 0
        if weg and zeit + inst.svc + inst.d[i][0] <= inst.H + 1e-9:
            out.append(tuple(weg))
        for j in range(1, inst.n + 1):
            if j == i or last + inst.dem[j] > inst.Q:
                continue
            ank = zeit + (inst.svc if i != 0 else 0) + inst.d[i][j]
            if ank > inst.due[j] + 1e-9:
                continue
            weg.append(j)
            if _ng_regel_ok(inst, k, weg):
                rec(weg, max(ank, inst.ready[j]), last + inst.dem[j])
            weg.pop()

    rec([], 0, 0)
    return out


@pytest.mark.parametrize("k", [1, 2, 3])
def test_labeling_with_a_memory_smaller_than_n_equals_the_depth_first_search_with_the_ng_rule(k):
    for seed in range(12):
        inst = S.instanz_aus_seed(5, seed, 40)
        pi = _zufalls_preise(inst, random.Random(seed))
        alle = {w: R.kosten(inst, w) - sum(pi[j] for j in w) for w in _wege_ng(inst, k)}
        erg = A.labeling(inst, pi, k)
        assert alle and erg.wege[0][0] == pytest.approx(min(alle.values()), abs=1e-9), (k, seed)
        assert all(r in alle and rc == pytest.approx(alle[r], abs=1e-9) for rc, r in erg.wege)


def test_memory_k_one_allows_cycles_that_the_elementary_rule_forbids():
    inst = S.instanz_aus_seed(5, 3, 100)
    pi = tuple(0.0 if j == 0 else 4.0 * inst.d[0][j] for j in range(6))
    gefunden = [r for _, r in A.labeling(inst, pi, 1).wege if len(set(r)) < len(r)]
    assert gefunden and not [r for _, r in A.labeling(inst, pi, None).wege if len(set(r)) < len(r)]


# --- Master ------------------------------------------------------------------------------------------------------------------------------------

def _dual_zulaessig(inst, spalten, pi, wert):
    """Dualitätszertifikat eines Masters: A^T pi <= c, pi >= 0 und die Summe der Dualpreise gleich dem Wert (starke Dualität)."""
    A_ = spaltenmatrix(inst, spalten)
    c = np.array([R.kosten(inst, r) for r in spalten], dtype=float)
    p = np.array(pi[1:])
    return bool(np.all(A_.T @ p <= c + 1e-7) and np.all(p >= -1e-9) and abs(p.sum() - wert) < 1e-6)


def test_master_equals_the_exact_master_on_column_sets_of_the_hand_example(hand):
    runden, spalten = R.spaltenerzeugung_exakt(hand, "labeling")
    for ende in (7, len(spalten)):
        menge = spalten[:ende]
        pi_ex, wert_ex, _ = R.master_exakt(hand, menge)
        m = loese_master(hand, menge)
        assert m.wert == pytest.approx(float(wert_ex), abs=1e-7)
        assert _dual_zulaessig(hand, menge, m.pi, m.wert)                     # die Dualpreise von HiGHS sind eine optimale Dual-Lösung (nicht dieselbe wie die exakte)
        assert float(sum(pi_ex)) == pytest.approx(float(wert_ex))


def test_master_equals_the_exact_master_on_small_integer_instances():
    for seed in range(12):
        rng = random.Random(seed)
        lagen = [(0, 0)] + [(rng.randint(-6, 6), rng.randint(-6, 6)) for _ in range(5)]
        inst = mini_instanz(lagen, [rng.randint(1, 4) for _ in range(5)], [(rng.randint(0, 10), rng.randint(20, 60)) for _ in range(5)], H=80, Q=9, svc=2)
        wege = R.wege_dfs(inst)
        _, wert_ex, _ = R.master_exakt(inst, wege)
        assert loese_master(inst, wege).wert == pytest.approx(float(wert_ex), abs=1e-7), seed


def test_cover_equals_partition_with_all_routes_as_columns_for_metric_costs():
    for seed in range(30):
        inst = S.instanz_aus_seed(6, seed, BREITEN[seed % 3])
        wege = R.wege_dfs(inst)
        assert loese_master(inst, wege, "ueberdeckung").wert == pytest.approx(loese_master(inst, wege, "partition").wert, abs=1e-6), seed


# --- Spaltenerzeugung --------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("art", ["ueberdeckung", "partition"])
def test_column_generation_bound_equals_the_master_over_all_routes_and_the_duals_certify_it(art):
    for seed in range(20):
        inst = S.instanz_aus_seed(7, seed, BREITEN[seed % 3])
        lauf = G.spaltenerzeugung(inst, None, art)
        alle = R.wege_dfs(inst)
        assert lauf.schranke == pytest.approx(loese_master(inst, alle, art).wert, abs=1e-6), seed
        pi = lauf.runden[-1].pi
        assert min(R.kosten(inst, w) - sum(pi[j] for j in w) for w in alle) >= -1e-6, seed      # mit den letzten Dualpreisen hat kein zulässiger Weg negative reduzierte Kosten


def test_exact_column_generation_at_the_hand_example_line_by_line(hand):
    runden, spalten = R.spaltenerzeugung_exakt(hand, "labeling")
    assert [w for w, _, _ in runden] == [50, 40, 32, 32, 32, 30, 30]
    assert [n for _, _, n in runden] == [(2, 7, 6), (5, 3, 1), (2, 1), (3, 4), (5, 4, 1), (6, 7, 1), None]
    assert [str(p) for p in runden[0][1]] == ["0", "6", "6", "10", "6", "6", "6", "10"]
    pi_ende, wert_ende, x = R.master_exakt(hand, spalten)
    mengen = {w: m for w, m in zip(spalten, x) if m > 0}
    assert mengen == {(2, 7, 6): 1, (5, 3, 1): Fraction(1, 2), (3, 4): Fraction(1, 2), (5, 4, 1): Fraction(1, 2)}
    deckung = [sum(m for w, m in mengen.items() if j in w) for j in range(1, 8)]
    assert deckung == [1] * 7 and wert_ende == 30
    # mit den Dualpreisen der letzten Runde hat keiner der 79 zulässigen Wege negative reduzierte Kosten, die Aufzählung aller Wege als Spalten gibt dieselbe Schranke
    alle = R.wege_dfs(hand)
    assert len(alle) == 79 and min(R.kosten(hand, w) - sum(pi_ende[j] for j in w) for w in alle) >= 0
    assert R.master_exakt(hand, alle)[1] == 30
    # Pricing mit der Tiefensuche statt des Labelings: dieselben Master-Werte
    assert [w for w, _, _ in R.spaltenerzeugung_exakt(hand, "dfs")[0]] == [50, 40, 32, 32, 32, 30, 30]


def test_hand_example_column_generation_with_highs_has_the_same_bound_as_the_exact_one(hand):
    exakt = R.spaltenerzeugung_exakt(hand, "labeling")[0][-1][0]
    for art in ("ueberdeckung", "partition"):
        assert G.spaltenerzeugung(hand, None, art, spalten_je_runde=1).schranke == pytest.approx(float(exakt), abs=1e-7)


# --- Dijkstra ----------------------------------------------------------------------------------------------------------------------------

def _nx_graph(inst, pi, typ):
    nx = pytest.importorskip("networkx")
    g = nx.DiGraph()
    n = inst.n
    for i in range(0, n + 1):
        for j in range(1, n + 1):
            if i != j:
                g.add_edge(i, j, weight=A.bogenlaenge(inst, pi, i, j, typ))
    for i in range(1, n + 1):
        g.add_edge(i, n + 1, weight=inst.d[i][0])
    return g


def test_dijkstra_with_nonnegative_lengths_equals_networkx_and_the_enumeration_of_all_simple_paths():
    nx = pytest.importorskip("networkx")
    for seed in range(12):
        inst = S.instanz_aus_seed(6, seed, 100)
        pi = tuple(0.0 if j == 0 else random.Random(seed * 7 + j).uniform(0, 100) for j in range(7))
        dij = A.dijkstra(inst, pi, "plus")
        assert dij.verpasst == 0
        bester = min(A.weg_laenge(inst, pi, w, "plus") for w in R.einfache_wege(6))
        assert dij.laenge == pytest.approx(bester, abs=1e-9)
        assert dij.laenge == pytest.approx(nx.dijkstra_path_length(_nx_graph(inst, pi, "plus"), 0, 7), abs=1e-9)
        assert A.weg_laenge(inst, pi, dij.weg, "plus") == pytest.approx(dij.laenge)


def test_dijkstra_with_negative_lengths_is_never_better_than_the_best_simple_path_and_is_worse_in_some_cases():
    schlechter = 0
    for seed in range(30):
        inst = S.instanz_aus_seed(6, seed, 100)
        pi = S.einzelfahrt_preise(inst)
        dij = A.dijkstra(inst, pi, "minus")
        beste = A.beste_einfache_wege(inst, pi, "minus")[1]
        assert dij.laenge >= beste - 1e-9                       # der Weg von Dijkstra ist ein gültiger Weg: er kann nicht besser sein als der beste
        schlechter += dij.laenge > beste + 1e-9
    assert schlechter >= 1


def test_negative_counts_equal_a_matrix_computation():
    for seed in range(10):
        inst = S.instanz_aus_seed(12, seed, 100)
        pi = _zufalls_preise(inst, random.Random(seed))
        d = np.array(inst.d)
        p = np.array(pi)
        laengen = d[1:, 1:] - p[1:][None, :]
        np.fill_diagonal(laengen, 1.0)                           # die Diagonale gehört nicht dazu
        kreise = d[1:, 1:] * 2 - p[1:][:, None] - p[1:][None, :]
        z = A.negativ_zaehlung(inst, pi)
        assert z.depot_negativ == int(np.sum(d[0, 1:] - p[1:] < -1e-9))
        assert z.kunde_negativ == int(np.sum(laengen < -1e-9)) and z.paare_negativ == int(np.sum(np.triu(kreise < -1e-9, 1)))
