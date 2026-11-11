"""Randfälle (DEMO-PLAYBOOK §12): ein Kunde, zwei Kunden, alle Dualpreise null, Kunden, die sich nicht kombinieren lassen, Kapazität unter fast jeder Last,
zwei Kunden am selben Ort, Gleichstand, Grenzen inklusive."""

import pytest
import referenz as R
from conftest import mini_instanz

import pdp_algorithm as A
import pdp_colgen as G
import pdp_scenario as S


def test_one_customer():
    inst = mini_instanz([(0, 0), (3, 0)], [2], [(0, 50)])
    lauf = G.spaltenerzeugung(inst, None)
    assert lauf.anzahl_runden == 1 and lauf.schranke == pytest.approx(6) and lauf.spalten == ((1,),) and lauf.runden[0].neue == ()
    gross = A.labeling(inst, (0.0, 20.0), None)                       # Dualpreis 20 > 6: die Einzelfahrt hat negative Kosten 6 - 20
    assert gross.wege == ((-14.0, (1,)),) and gross.erzeugt == 2
    gleich = A.labeling(inst, (0.0, 6.0), None)                       # Dualpreis = Kosten der Einzelfahrt: reduzierte Kosten genau 0, keine neue Spalte
    assert gleich.wege == ((0.0, (1,)),) and A.neue_spalten(gleich.wege, (0.0, 6.0), inst, {(1,)}, 5) == []


def test_two_customers_equal_the_exact_bound():
    inst = mini_instanz([(0, 0), (3, 0), (3, 4)], [2, 2], [(0, 50), (0, 50)])
    lauf = G.spaltenerzeugung(inst, None)
    # Fahrt 0-1-2-0: 3 + 4 + 7 = 14 gegen die Einzelfahrten 6 + 14 = 20: die Tour mit beiden Kunden gewinnt
    assert lauf.schranke == pytest.approx(14) and (1, 2) in lauf.spalten
    assert lauf.schranke == pytest.approx(float(R.master_exakt(inst, R.wege_dfs(inst))[1]))


def test_all_prices_zero_give_no_negative_route_and_no_new_column(hand):
    pi0 = (0.0,) * 8
    erg = A.labeling(hand, pi0, None)
    assert erg.wege and all(rc >= 0 for rc, _ in erg.wege)           # reduzierte Kosten = Fahrtkosten, nie negativ
    assert A.neue_spalten(erg.wege, pi0, hand, set(), 15) == []
    assert A.negativ_zaehlung(hand, pi0).depot_negativ == 0 and A.negativ_zaehlung(hand, pi0).kunde_negativ == 0 and A.negativ_zaehlung(hand, pi0).paare_negativ == 0


def test_customers_that_cannot_be_combined_leave_the_bound_at_the_sum_of_the_single_trips():
    # drei Kunden mit Zeitfenstern, die so weit auseinander und so eng liegen, dass keine zwei in einer Tour bedient werden können
    inst = mini_instanz([(0, 0), (5, 0), (0, 5), (-5, 0)], [1, 1, 1], [(5, 5), (5, 5), (5, 5)], H=40, Q=9, svc=1)
    assert R.wege_dfs(inst) == [(1,), (2,), (3,)]
    lauf = G.spaltenerzeugung(inst, None)
    assert lauf.anzahl_runden == 1 and lauf.schranke == pytest.approx(3 * 10) and len(lauf.spalten) == 3


def test_a_customer_whose_window_ends_late_is_still_bound_by_the_horizon():
    # Kunde 2 hat das Fenster [0, 100], aber der Horizont ist 20: die Rückkehr begrenzt, nicht das Fenster
    inst = mini_instanz([(0, 0), (2, 0), (0, 3)], [1, 1], [(0, 100), (0, 100)], H=20, Q=9, svc=2)
    for rc, route in A.labeling(inst, (0.0, 30.0, 30.0), None).wege:
        assert A.pruefe_route(inst, route)[0]
    # 0-1-2-0: Beginn 2, dann 2 + 2 + 5 = 9, Rückkehr 9 + 2 + 3 = 14 <= 20: zulässig; mit Horizont 13 nicht mehr
    assert (1, 2) in R.wege_dfs(inst)
    eng = mini_instanz([(0, 0), (2, 0), (0, 3)], [1, 1], [(0, 100), (0, 100)], H=13, Q=9, svc=2)
    assert (1, 2) not in R.wege_dfs(eng) and (1, 2) not in [r for _, r in A.labeling(eng, (0.0, 30.0, 30.0), None).wege]


def test_capacity_below_all_loads_but_the_smallest():
    inst = mini_instanz([(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)], [2, 3, 4, 5], [(0, 90)] * 4, H=100, Q=2, svc=1)
    erg = A.labeling(inst, (0.0,) + (50.0,) * 4, None)
    assert [r for _, r in erg.wege] == [(1,)] and erg.abgelehnt_last > 0
    with pytest.raises(ValueError, match="Einzelfahrt zu Kunde 2"):
        G.spaltenerzeugung(inst, None)                                # die Einzelfahrt zu Kunde 2 (Last 3 > 2) ist nicht zulässig


def test_two_customers_at_the_same_place_are_a_tie_and_the_result_is_exact():
    inst = mini_instanz([(0, 0), (4, 0), (4, 0), (0, 4)], [1, 1, 1], [(0, 60)] * 3, H=80, Q=9, svc=1)
    assert inst.d[1][2] == 0
    pi = (0.0, 9.0, 9.0, 9.0)
    a = A.labeling(inst, pi, None)
    erzeugt, dominiert, route, rc, anzahl, _ = R.labeling_ref(inst, pi)
    assert (a.erzeugt, a.dominiert, len(a.wege)) == (erzeugt, dominiert, anzahl) and a.wege[0][0] == pytest.approx(float(rc))
    lauf = G.spaltenerzeugung(inst, None)
    assert lauf.schranke == pytest.approx(float(R.master_exakt(inst, R.wege_dfs(inst))[1]))
    assert (1, 2) in R.wege_dfs(inst) and (2, 1) in R.wege_dfs(inst)


def test_horizon_and_window_end_are_inclusive_in_the_labeling():
    inst = mini_instanz([(0, 0), (3, 0)], [1], [(0, 3)], H=8, svc=2)           # Ankunft 3 = Fensterende, Rückkehr 3 + 2 + 3 = 8 = H
    assert [r for _, r in A.labeling(inst, (0.0, 20.0), None).wege] == [(1,)]
    zu_spaet = mini_instanz([(0, 0), (3, 0)], [1], [(0, 2)], H=8, svc=2)
    assert A.labeling(zu_spaet, (0.0, 20.0), None).wege == ()


def test_generated_single_trips_are_always_feasible_at_the_corners_of_the_sliders():
    for n, breite in ((5, 40), (20, 40), (5, 100), (20, 100)):
        for seed in (0, 7, 999999):
            inst = S.instanz_aus_seed(n, seed, breite)
            assert all(A.pruefe_route(inst, (j,))[0] for j in range(1, n + 1))
