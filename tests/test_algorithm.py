"""Der Kern gegen die Handrechnung am Handbeispiel (DEMO-PLAYBOOK §1b): jede Einheit einzeln, dann das Labeling, Dijkstra und die Spaltenerzeugung.

Erwartete Werte stehen als Rechnung da (Summen der Entfernungen und Preise). Die Zählungen der Labels (56, 20, 0, 36) und die Zahl der zulässigen Wege (79) stammen aus der
unabhängigen Vorrechnung `vormessung/hand_05.py` der Planung (Brüche, Mengen statt Bitmasken) und werden in `test_oracle_pricing_dualpreise.py` zusätzlich von einer zweiten
Implementierung in `tests/referenz.py` und von einer Tiefensuche bestätigt."""

import math

import pytest
from conftest import hand_d, mini_instanz

import pdp_algorithm as A
import pdp_colgen as G
import pdp_scenario as S
from pdp_master import loese_master

# --- Szenario ----------------------------------------------------------------------------------------------------------------------------------


def test_scenario_module_has_the_same_hand_example(hand):
    h = S.handbeispiel()
    assert (h.pts, h.d, h.dem, h.ready, h.due, h.H, h.Q, h.svc) == (hand.pts, hand.d, hand.dem, hand.ready, hand.due, hand.H, hand.Q, hand.svc)
    assert h.n == 7


def test_first_round_prices_are_twice_the_distance_to_the_depot(hand, pi_erste_runde):
    assert S.einzelfahrt_preise(hand) == pi_erste_runde == (0.0, 6.0, 6.0, 10.0, 6.0, 6.0, 6.0, 10.0)   # 2 x (3, 3, 5, 3, 3, 3, 5)


def test_generated_instances_are_deterministic_and_respect_the_construction_rules():
    a = S.instanz_aus_seed(12, 7, 100)
    assert a == S.instanz_aus_seed(12, 7, 100) and a != S.instanz_aus_seed(12, 8, 100)
    assert a.n == 12 and a.pts[0] == (50.0, 50.0) and (a.H, a.Q, a.svc) == (300.0, 70.0, 10.0)
    for i in range(1, 13):
        assert 5 <= a.dem[i] <= 25 and 0 <= a.pts[i][0] <= 100 and 0 <= a.pts[i][1] <= 100
        # Fenster: innerhalb von früheste Ankunft (Entfernung zum Depot) und späteste Ankunft (H - Bedienzeit - Entfernung), höchstens so breit wie verlangt
        assert a.d[0][i] <= a.ready[i] <= a.due[i] <= 300 - 10 - a.d[0][i] + 1e-9 and a.due[i] - a.ready[i] <= 100 + 1e-9


def test_clustered_instances_keep_all_customers_inside_the_square():
    g = S.instanz_aus_seed(30, 3, 100, "gruppiert")
    assert all(0 <= x <= 100 and 0 <= y <= 100 for x, y in g.pts[1:]) and g != S.instanz_aus_seed(30, 3, 100)
    with pytest.raises(ValueError):
        S.instanz_aus_seed(5, 0, 100, "unbekannt")


def test_wider_windows_contain_the_narrower_ones_for_the_same_seed():
    eng, weit = S.instanz_aus_seed(10, 4, 40), S.instanz_aus_seed(10, 4, 100)
    assert eng.pts == weit.pts and eng.dem == weit.dem
    assert all(weit.ready[i] <= eng.ready[i] + 1e-9 and eng.due[i] <= weit.due[i] + 1e-9 for i in range(1, 11))     # gleicher Mittelpunkt, breiteres Fenster enthält das engere
    assert any(weit.due[i] - weit.ready[i] > eng.due[i] - eng.ready[i] + 1 for i in range(1, 11))


# --- Verlängerung, Rückkehr -----------------------------------------------------------------------------------------------------------------

def test_extension_from_the_depot_has_no_service_time_and_waits_for_the_window(hand):
    assert A.verlaengerung(hand, 0, 0, 0, 2) == (3, 3)           # Ankunft 0 + d(0,2) = 3, Fensterbeginn 3, Last 0 + 3
    assert A.verlaengerung(hand, 0, 0, 0, 1) == (18, 1)          # Ankunft 3, Fensterbeginn 18: warten bis 18


def test_extension_from_a_customer_adds_the_service_time(hand):
    zeit, last = A.verlaengerung(hand, 0, 0, 0, 2)
    assert A.verlaengerung(hand, 2, zeit, last, 7) == (3 + 2 + hand_d(2, 7), 3 + 2)   # Kunde 2 -> 7: 3 + Bedienzeit 2 + 4 = 9, Last 5
    assert A.verlaengerung(hand, 2, 3, 3, 7) == (9, 5)


def test_extension_is_refused_after_the_window_end_and_inclusive_at_it():
    m = mini_instanz([(0, 0), (3, 0)], [1], [(0, 3)])
    assert A.verlaengerung(m, 0, 0, 0, 1) == (3, 1)               # Ankunft 3 = Fensterende: zulässig
    m2 = mini_instanz([(0, 0), (3, 0)], [1], [(0, 2)])
    assert A.verlaengerung(m2, 0, 0, 0, 1) is None


def test_extension_is_refused_over_the_capacity_and_inclusive_at_it(hand):
    assert A.verlaengerung(hand, 5, 3, 3, 3) is not None          # Last 3 + 3 = 6 = Kapazität: zulässig
    assert A.verlaengerung(hand, 5, 3, 4, 3) is None              # Last 7 > 6
    assert A.ablehngrund(hand, 5, 3, 4, 3) == "Last 7 > 6"


def test_refusal_reasons_name_the_violated_rule(hand):
    assert A.ablehngrund(hand, 7, 8, 2, 3) == "Ankunft 20 > Fensterende 15"        # 8 + 2 + d(7,3) = 8 + 2 + 10 = 20
    assert A.ablehngrund(hand, 0, 0, 0, 2) == ""


def test_return_to_the_depot_is_inclusive_at_the_horizon(hand):
    assert A.rueckkehr_moeglich(hand, 6, 13)                      # 13 + 2 + 3 = 18 <= 38
    m = mini_instanz([(0, 0), (3, 0)], [1], [(0, 50)], H=8, svc=2)
    assert A.rueckkehr_moeglich(m, 1, 3) and not A.rueckkehr_moeglich(m, 1, 4)   # 3 + 2 + 3 = 8 = H; 4 + 2 + 3 = 9 > 8


# --- Dominanz ----------------------------------------------------------------------------------------------------------------------------------

def _label(zeit=5.0, kosten=-3.0, last=2, mem=0b100):
    return A.Label(1, zeit, kosten, last, mem, -1)


def test_dominance_needs_all_four_comparisons():
    b = _label()
    assert A.dominiert(_label(), b)                                    # gleiche Werte dominieren sich
    assert A.dominiert(_label(4.0, -4.0, 1, 0b100), b)
    assert not A.dominiert(_label(zeit=6.0), b)                        # Zeit schlechter
    assert not A.dominiert(_label(kosten=-2.0), b)                     # Kosten schlechter
    assert not A.dominiert(_label(last=3), b)                          # Last schlechter
    assert not A.dominiert(_label(mem=0b110), b)                       # Gedächtnis ist keine Teilmenge
    assert A.dominiert(_label(mem=0b000), b) and A.dominiert(_label(mem=0b100), _label(mem=0b110))


def test_dominance_without_the_memory_comparison_is_the_wrong_rule():
    assert A.dominiert(_label(mem=0b110), _label(), mit_gedaechtnis=False)
    assert not A.dominiert(_label(mem=0b110), _label(), mit_gedaechtnis=True)


def test_insert_reports_the_dominator_or_the_displaced_labels():
    labels = [_label(5, -3, 2), _label(7, -3, 2), _label(4, -1, 2), _label(3, -5, 1)]
    assert A.einfuegen(labels, [0], 1) == (0, [])                      # Label 1 (Zeit 7) ist von Label 0 dominiert
    assert A.einfuegen(labels, [0, 2], 3) == (None, [0, 2])            # Label 3 (Zeit 3, Kosten -5, Last 1) dominiert beide
    assert A.einfuegen(labels, [2], 0) == (None, [])                   # Label 0 und 2 sind unvergleichbar (Zeit 5 gegen 4, Kosten -3 gegen -1)


# --- Gedächtnis ------------------------------------------------------------------------------------------------------------------------------

def test_memory_masks(hand):
    assert A.ng_masken(hand, 1) == (0,) + tuple(1 << j for j in range(1, 8))                       # k = 1: nur der Kunde selbst
    assert A.ng_masken(hand, 7) == (0,) + (0b11111110,) * 7                                         # k = n: alle Kunden (elementar)
    assert A.ng_masken(hand, 2)[3] == (1 << 3) | (1 << 4)                                           # d(3,4) = d(3,5) = 2: Gleichstand, kleinere Nummer gewinnt


# --- Labeling am Handbeispiel ---------------------------------------------------------------------------------------------------------------

def test_labeling_first_round_finds_the_best_route_with_hand_computed_costs(hand, pi_erste_runde):
    erg = A.labeling(hand, pi_erste_runde, None)
    rc, route = erg.wege[0]
    assert route == (2, 7, 6)
    fahrt = hand_d(0, 2) + hand_d(2, 7) + hand_d(7, 6) + hand_d(6, 0)                # 3 + 4 + 2 + 3 = 12
    preise = pi_erste_runde[2] + pi_erste_runde[7] + pi_erste_runde[6]              # 6 + 10 + 6 = 22
    assert rc == pytest.approx(fahrt - preise) == pytest.approx(-10)
    assert A.reduzierte_kosten(hand, pi_erste_runde, route) == pytest.approx(-10)


def test_labeling_counts_of_the_hand_example(hand, pi_erste_runde):
    erg = A.labeling(hand, pi_erste_runde, None, behalte_labels=True)
    assert (erg.erzeugt, erg.verworfen, erg.verdraengt, erg.lebend) == (56, 20, 0, 36)
    assert erg.dominiert == 20 and erg.erzeugt == erg.lebend + erg.dominiert
    assert len(erg.wege) == 35 and not erg.abgebrochen
    assert len(erg.labels) == erg.erzeugt and sum(1 for L in erg.labels if L.tot == 1) == 20


def test_all_returned_routes_are_feasible_and_have_the_right_reduced_costs(hand, pi_erste_runde):
    for rc, route in A.labeling(hand, pi_erste_runde, None).wege:
        ok, text = A.pruefe_route(hand, route)
        assert ok, (route, text)
        assert rc == pytest.approx(A.reduzierte_kosten(hand, pi_erste_runde, route))


def test_the_dominated_example_of_the_plan(hand, pi_erste_runde):
    """„0-2-3 von Label 3 dominiert: Kosten -5 <= -5, Zeit 5 <= 13, Last 3 <= 6, Menge {3} in {2, 3}“: das Label 0-2-3 hat Zeit 3 + 2 + 8 = 13 (Fenster [5, 15]), Kosten (3 - 6) + (8 - 10) = -5, Last 6."""
    erg = A.labeling(hand, pi_erste_runde, None, behalte_labels=True)
    weg = {i: A.weg_von(list(erg.labels), i) for i in range(len(erg.labels))}
    neu = next(i for i, L in enumerate(erg.labels) if weg[i] == (2, 3))
    L = erg.labels[neu]
    assert L.tot == 1 and (L.zeit, L.kosten, L.last) == (13, -5, 6)
    assert weg[L.von] == (3,) and (erg.labels[L.von].zeit, erg.labels[L.von].kosten, erg.labels[L.von].last) == (5, -5, 3)


def test_rejection_counters_add_up_with_the_generated_labels(hand, pi_erste_runde):
    erg = A.labeling(hand, pi_erste_runde, None)
    assert erg.abgelehnt_last > 0 and erg.abgelehnt_fenster > 0 and erg.verboten > 0


def test_switching_off_dominance_changes_the_count_but_not_the_best_route(hand, pi_erste_runde):
    mit = A.labeling(hand, pi_erste_runde, None)
    ohne = A.labeling(hand, pi_erste_runde, None, dominanz=False)
    assert ohne.erzeugt > mit.erzeugt and ohne.dominiert == 0
    assert ohne.wege[0] == mit.wege[0] and len(ohne.wege) == 79       # ohne Dominanz entstehen alle 79 zulässigen Wege


def test_switching_off_the_memory_comparison_changes_the_result(hand, pi_erste_runde):
    falsch = A.labeling(hand, pi_erste_runde, None, mit_gedaechtnis=False)
    richtig = A.labeling(hand, pi_erste_runde, None)
    assert (falsch.erzeugt, falsch.dominiert) != (richtig.erzeugt, richtig.dominiert)


def test_label_cap_stops_the_run_and_marks_it(hand, pi_erste_runde):
    erg = A.labeling(hand, pi_erste_runde, None, max_labels=10)
    assert erg.abgebrochen and erg.erzeugt >= 10


def test_the_memory_k_changes_the_labeling(hand, pi_erste_runde):
    zahlen = {k: A.labeling(hand, pi_erste_runde, k).erzeugt for k in (1, 2, 3, 7)}
    assert len(set(zahlen.values())) > 1 and A.labeling(hand, pi_erste_runde, 7).erzeugt == A.labeling(hand, pi_erste_runde, None).erzeugt


def test_new_columns_take_negative_unknown_routes_in_order(hand, pi_erste_runde):
    wege = ((-10.0, (2, 7, 6)), (-8.0, (6, 7, 1)), (-4.0, (2, 1)), (0.0, (2,)))
    assert A.neue_spalten(wege, pi_erste_runde, hand, set(), 5) == [     # echte reduzierte Kosten: 12 - 22, 12 - 22 (Fahrt 3 + 2 + 4 + 3), 8 - 12
        (pytest.approx(-10), (2, 7, 6)), (pytest.approx(-10), (6, 7, 1)), (pytest.approx(-4), (2, 1))]
    assert [r for _, r in A.neue_spalten(wege, pi_erste_runde, hand, {(2, 7, 6)}, 5)] == [(6, 7, 1), (2, 1)]
    assert [r for _, r in A.neue_spalten(wege, pi_erste_runde, hand, set(), 2)] == [(2, 7, 6), (6, 7, 1)]     # höchstens 2 des Pricings
    # erst auf die besten `anzahl` Routen des Pricings kürzen, dann filtern: mit der bekannten Route (2, 7, 6) bleibt nur (6, 7, 1), die dritte Route (2, 1) rückt nicht nach
    assert [r for _, r in A.neue_spalten(wege, pi_erste_runde, hand, {(2, 7, 6)}, 2)] == [(6, 7, 1)]
    # unter anderen echten Dualpreisen (alle 0) hat keine Route negative reduzierte Kosten
    assert A.neue_spalten(wege, (0.0,) * 8, hand, set(), 5) == []


# --- Prüfer und Fahrplan -------------------------------------------------------------------------------------------------------------------

def test_route_checker_names_the_first_violated_rule(hand):
    assert A.pruefe_route(hand, (2, 7, 6)) == (True, "zulässig (Last, Fenster, Rückkehr)")
    assert A.pruefe_route(hand, (3, 4, 5, 1, 7, 6, 2)) == (False, "unzulässig bei Kunde 5: Last 7 > 6")       # Weg von Dijkstra: Last 3 + 3 + 1 = 7
    assert A.pruefe_route(hand, (4, 3, 5, 1, 2, 7, 6))[1] == "unzulässig bei Kunde 3: Ankunft 24 > Fensterende 15"   # Fahrt 4 -> 3: Beginn 20 + 2 + 2 = 24
    assert A.pruefe_route(hand, ())[0] is False and A.pruefe_route(hand, (2, 2))[1] == "ein Kunde kommt mehrfach vor"
    assert A.pruefe_route(hand, (9,))[0] is False
    assert A.pruefe_route(hand, (2, 2), elementar=False)[0] is True       # nichtelementar erlaubt: Kunde 2 zweimal, Last 3 + 3 = 6, Ankunft 3 + 2 + 0 = 5 <= 16, Rückkehr 5 + 2 + 3 <= 38
    m = mini_instanz([(0, 0), (5, 0)], [1], [(0, 50)], H=8, svc=2)
    assert A.pruefe_route(m, (1,))[1].startswith("unzulässig: Rückkehr 5 + 2 + 5 > 8")


def test_schedule_of_the_best_route(hand, pi_erste_runde):
    plan = A.fahrplan(hand, pi_erste_runde, (2, 7, 6))
    assert [(j, ank, beginn, last) for j, ank, beginn, last, _ in plan] == [(2, 3, 3, 3), (7, 9, 9, 5), (6, 13, 13, 6)]
    assert plan[-1][4] == pytest.approx((3 - 6) + (4 - 10) + (2 - 6))                       # reduzierte Kosten bis Kunde 6 ohne Rückfahrt: -13


# --- Aufzählung aller zulässigen Wege ------------------------------------------------------------------------------------------------------

def test_enumeration_of_all_feasible_elementary_routes(hand, pi_erste_runde):
    wege = A.alle_zulaessigen_wege(hand)
    assert len(wege) == 79 and len(set(wege)) == 79 and all(A.pruefe_route(hand, w)[0] for w in wege)
    assert min(A.reduzierte_kosten(hand, pi_erste_runde, w) for w in wege) == pytest.approx(-10)
    assert sum(1 for w in wege if A.reduzierte_kosten(hand, pi_erste_runde, w) < -1e-9) == 58


# --- Bogenlängen, Dijkstra -------------------------------------------------------------------------------------------------------------------

def test_arc_lengths(hand, pi_erste_runde):
    assert A.bogenlaenge(hand, pi_erste_runde, 0, 3, "minus") == hand_d(0, 3) - 10 == -5
    assert A.bogenlaenge(hand, pi_erste_runde, 4, 3, "minus") == hand_d(4, 3) - 10 == -8
    assert A.bogenlaenge(hand, pi_erste_runde, 4, 3, "plus") == hand_d(4, 3) + 10 == 12
    assert A.bogenlaenge(hand, pi_erste_runde, 6, 8, "minus") == hand_d(6, 0) == 3             # Bogen ins Ende: Entfernung zum Depot


def test_negative_counts_of_the_hand_example(hand, pi_erste_runde):
    z = A.negativ_zaehlung(hand, pi_erste_runde)
    depot = sum(1 for j in range(1, 8) if hand_d(0, j) - pi_erste_runde[j] < 0)
    kunde = sum(1 for i in range(1, 8) for j in range(1, 8) if i != j and hand_d(i, j) - pi_erste_runde[j] < 0)
    paare = sum(1 for i in range(1, 8) for j in range(i + 1, 8) if 2 * hand_d(i, j) - pi_erste_runde[i] - pi_erste_runde[j] < 0)
    assert (z.depot_negativ, z.kunde_negativ, z.paare_negativ) == (depot, kunde, paare) == (7, 27, 12)
    assert (z.depot_gesamt, z.kunde_gesamt, z.paare_gesamt) == (7, 42, 21)
    assert z.kleinstes_paar == (3, 4) and z.kleinster_kreis == 2 * hand_d(3, 4) - 10 - 6 == -12


def test_dijkstra_with_nonnegative_lengths_finds_the_single_trip(hand, pi_erste_runde):
    r = A.dijkstra(hand, pi_erste_runde, "plus")
    assert r.weg == (1,) and r.laenge == (hand_d(0, 1) + 6) + hand_d(1, 0) == 12 and r.verpasst == 0          # 3 + 6 + 3


def test_dijkstra_with_the_pricing_lengths_misses_improvements(hand, pi_erste_runde):
    r = A.dijkstra(hand, pi_erste_runde, "minus")
    assert r.schritte[0] == ("schliesse", 0, 0.0)
    assert r.schritte[1] == ("schliesse", 3, hand_d(0, 3) - 10)                                               # Kunde 3 zuerst: Abstand 5 - 10 = -5
    assert r.schritte[2] == ("schliesse", 4, (hand_d(0, 3) - 10) + (hand_d(3, 4) - 6))                       # -5 + (2 - 6) = -9
    verpasst = [s for s in r.schritte if s[0] == "verpasst"][0]
    assert verpasst == ("verpasst", 4, 3, -9.0, hand_d(4, 3) - 10, -5.0) and -9 + (hand_d(4, 3) - 10) == -17 < -5   # -9 + (-8) = -17 wäre besser als -5
    assert r.verpasst == 21 and r.weg == (3, 4, 5, 1, 7, 6, 2) and r.laenge == -24
    assert A.weg_laenge(hand, pi_erste_runde, r.weg, "minus") == pytest.approx(r.laenge)


def test_best_simple_path_by_enumeration(hand, pi_erste_runde):
    anzahl, laenge, weg = A.beste_einfache_wege(hand, pi_erste_runde, "minus")
    assert anzahl == sum(math.perm(7, r) for r in range(1, 8)) == 13699
    assert weg == (4, 3, 5, 1, 2, 7, 6)
    summe = ((3 - 6) + (2 - 10) + (2 - 6) + (4 - 6) + (2 - 6) + (4 - 10) + (2 - 6)) + hand_d(6, 0)             # Bogenlängen 0-4-3-5-1-2-7-6 und zurück: -28
    assert laenge == pytest.approx(summe) == pytest.approx(-28)


# --- Master und Spaltenerzeugung ---------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("art", ["ueberdeckung", "partition"])
def test_master_of_the_first_round_gives_the_single_trip_costs_as_prices(hand, art):
    spalten = G.einzelfahrten(hand)
    m = loese_master(hand, spalten, art)
    assert m.wert == pytest.approx(sum(2 * hand_d(0, j) for j in range(1, 8))) == pytest.approx(50)           # 6 + 6 + 10 + 6 + 6 + 6 + 10
    assert m.pi == pytest.approx((0.0, 6, 6, 10, 6, 6, 6, 10)) and m.x == pytest.approx((1.0,) * 7)


def test_master_rejects_an_unknown_kind(hand):
    with pytest.raises(ValueError):
        loese_master(hand, G.einzelfahrten(hand), "unbekannt")


@pytest.mark.parametrize("art", ["ueberdeckung", "partition"])
def test_column_generation_reaches_the_bound_of_the_hand_example(hand, art):
    lauf = G.spaltenerzeugung(hand, None, art, spalten_je_runde=1)
    assert lauf.schranke == pytest.approx(30) and not lauf.abgebrochen
    assert lauf.runden[0].master_wert == pytest.approx(50) and lauf.runden[0].neue == ((2, 7, 6),) and lauf.runden[0].beste_rc == pytest.approx(-10)
    assert lauf.runden[-1].neue == () and lauf.runden[-1].beste_rc is None
    assert all(A.pruefe_route(hand, c)[0] for c in lauf.spalten)
    assert [r.master_wert for r in lauf.runden] == sorted((r.master_wert for r in lauf.runden), reverse=True)
    assert lauf.labels == sum(r.labels for r in lauf.runden) and lauf.aufrufe >= lauf.anzahl_runden


def test_column_generation_with_the_all_routes_master_gives_the_same_bound(hand):
    assert loese_master(hand, A.alle_zulaessigen_wege(hand)).wert == pytest.approx(30)


def test_lower_memory_gives_a_lower_or_equal_bound(hand):
    schranken = {k: G.spaltenerzeugung(hand, k).schranke for k in (1, 2, 3, 7)}
    assert schranken[1] <= schranken[2] <= schranken[3] + 1e-9 and schranken[3] == pytest.approx(30) == pytest.approx(schranken[7])
    assert schranken[1] < 30 - 1e-6


def test_smoothing_with_alpha_zero_is_the_unsmoothed_run(hand):
    assert G.spaltenerzeugung(hand, None, alpha=0.0, spalten_je_runde=1) == G.spaltenerzeugung(hand, None, spalten_je_runde=1)


def test_a_miss_is_followed_by_a_call_with_the_true_prices(hand):
    lauf = G.spaltenerzeugung(hand, None, alpha=0.9, spalten_je_runde=1)
    assert lauf.fehlgriffe > 0 and lauf.aufrufe == lauf.anzahl_runden + lauf.fehlgriffe
    assert lauf.schranke == pytest.approx(30)


def test_label_cap_marks_the_run_as_aborted(hand):
    lauf = G.spaltenerzeugung(hand, None, max_labels=60, spalten_je_runde=1)
    assert lauf.abgebrochen


def test_round_cap_marks_the_run_as_aborted(hand):
    assert G.spaltenerzeugung(hand, None, max_runden=2, spalten_je_runde=1).abgebrochen


def test_worst_case_at_the_slider_maximum_finishes_without_hitting_the_cap():
    """20 Kunden, Fensterbreite 100 (Regler-Maximum), elementar: kein Zeit-Test, nur die Label-Obergrenze als Netz."""
    inst = S.instanz_aus_seed(20, 3, 100)
    lauf = G.spaltenerzeugung(inst, None)
    assert not lauf.abgebrochen and lauf.runden[-1].neue == () and lauf.schranke < lauf.runden[0].master_wert


def test_negative_counts_for_the_plus_lengths_and_free_prices(hand, pi_erste_runde):
    """Entfernung plus Preis ist bei nichtnegativen Preisen nie negativ; mit negativen Dualpreisen (Partitionierung) kann es wieder negative Bögen geben."""
    z = A.negativ_zaehlung(hand, pi_erste_runde, "plus")
    assert (z.depot_negativ, z.kunde_negativ, z.paare_negativ) == (0, 0, 0) and z.kleinster_kreis == min(2 * hand_d(i, j) + pi_erste_runde[i] + pi_erste_runde[j] for i in range(1, 8) for j in range(i + 1, 8))
    frei = (0.0, -9.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    z2 = A.negativ_zaehlung(hand, frei, "plus")
    assert z2.depot_negativ == 1 and hand_d(0, 1) + frei[1] == -6 < 0                      # nur der Bogen vom Depot zu Kunde 1: 3 - 9
    assert z2.kunde_negativ == sum(1 for i in range(2, 8) if hand_d(i, 1) - 9 < 0)           # Bögen von Kunde i nach Kunde 1 (d - 9), keine anderen
