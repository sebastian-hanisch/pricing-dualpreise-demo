"""Verdikte und Texte an von Hand gesetzten Werten (DEMO-PLAYBOOK §12): jede Zahl im Text und jede Schwelle der Art steht hier.

Ein Verdikt ist eine reine Funktion (Art, Text) und bekommt Werte, nicht Seeds. Die erwartete Verdikt-Zeile je Voreinstellung steht in `test_app.py`."""

import pytest

import pdp_algorithm as A
import pdp_colgen as G
import pdp_evaluation as ev

NBSP = " "


def test_number_format_is_german():
    assert ev.zahl(1040) == f"1{NBSP}040" and ev.zahl(26678.5, 1) == f"26{NBSP}678,5" and ev.zahl(12.0) == "12" and ev.zahl(-57.3, 2) == "-57,30"
    assert ev.zahl(-0.0, 1) == "0,0" and ev.zahl(0.04, 1) == "0,0" and ev.prozent(88.44) == "88,4 %" and ev.zahl(4.5, 1) == "4,5"
    assert ev.zahl_kurz(-10.0) == "-10" and ev.zahl_kurz(2.5) == "2,50" and ev.zahl_kurz(30.0) == "30"
    assert ev.alpha_text(0) == "0" and ev.alpha_text(50) == "0,5" and ev.alpha_text(80) == "0,8" and ev.alpha_text(90) == "0,9"


def _bogen(neg_depot, neg_kunde, dij_laenge, dij_weg, einfach_laenge, einfach_weg, dij_ok=(True, "zulässig (Last, Fenster, Rückkehr)"), verpasst=0, anzahl=13699):
    z = A.NegativZaehlung(neg_depot, 7, neg_kunde, 42, 0, 21, None, None)
    return ev.BogenAnalyse((), z, A.DijkstraErgebnis((), dij_weg, dij_laenge, verpasst), (anzahl, einfach_laenge, einfach_weg), dij_ok, (True, "zulässig"), ())


def test_dijkstra_verdict_misses_only_with_a_negative_arc_and_a_different_value():
    b = _bogen(7, 27, -24.0, (3, 4, 5, 1, 7, 6, 2), -28.0, (4, 3, 5, 1, 2, 7, 6), (False, "unzulässig bei Kunde 5: Last 7 > 6"), 21)
    kind, text = ev.verdict_dijkstra(b)
    assert kind == "warning" and "Dijkstra trifft den besten Weg nicht" in text
    assert "3-4-5-1-7-6-2 hat die Länge -24" in text and "4-3-5-1-2-7-6 mit Länge -28" in text and f"13{NBSP}699" in text and "34 Bögen sind negativ" in text and "21 Verbesserungen" in text
    assert "unzulässig bei Kunde 5: Last 7 > 6" in text and "kennt Last und Fenster nicht" in text


def test_dijkstra_verdict_without_negative_arcs_is_equal():
    kind, text = ev.verdict_dijkstra(_bogen(0, 0, 12.0, (1,), 12.0, (1,)))
    assert kind == "success" and "nicht negativ" in text and "Länge 12" in text and f"13{NBSP}699" in text and "kennt Last und Fenster nicht" not in text


def test_dijkstra_verdict_with_negative_arcs_but_the_same_value_is_not_a_miss():
    kind, text = ev.verdict_dijkstra(_bogen(1, 0, -3.0, (2,), -3.0, (2,), verpasst=0))
    assert kind == "info" and "Obwohl 1 Bögen negativ sind, trifft Dijkstra hier den besten einfachen Weg 2" in text and "0 verpasste" in text


def test_dijkstra_verdict_threshold_for_equal_values_is_1e_minus_9():
    assert ev.verdict_dijkstra(_bogen(1, 0, -3.0 + 1e-12, (2,), -3.0, (2,)))[0] == "info"
    assert ev.verdict_dijkstra(_bogen(1, 0, -3.0 + 1e-6, (2,), -3.0, (2,)))[0] == "warning"


def _lab(beste, aufz, verworfen=20, verdraengt=0, lebend=36, erzeugt=56, wege=35, negativ=28):
    return ev.LabelingAnalyse(erzeugt, verworfen, verdraengt, lebend, 0, 0, 0, (), (), beste, wege, negativ, aufz, ())


def test_labeling_verdict_names_the_counts_and_compares_with_the_enumeration():
    kind, text = ev.verdict_labeling(_lab((-10.0, (2, 7, 6)), -10.0), 79)
    assert kind == "success" and "Weg 2-7-6 mit reduzierten Kosten -10" in text and "79 zulässigen elementaren Wege gibt -10 (gleich)" in text
    assert "56 Labels, davon 20 sofort verworfen" in text and "0 später verdrängt, 36 blieben übrig" in text and "35 Routen kehren ins Depot zurück, 28 davon mit negativen" in text
    kind2, text2 = ev.verdict_labeling(_lab((-9.0, (2, 7)), -10.0), 79)
    assert kind2 == "error" and "ABWEICHUNG" in text2
    assert ev.verdict_labeling(_lab(None, None), 0)[0] == "info"


def _lauf(runden, spalten, schranke, aufrufe=None, fehlgriffe=0, abgebrochen=False, labels=100):
    """Ein von Hand gesetzter Lauf (Daten, keine Rechnung): so hängen die Texte nicht am LP-Löser."""
    rs = tuple(G.Runde(i + 1, 50.0, (0.0,), (0.0,), (), None, 10, 1, 0, ()) for i in range(runden))
    return G.Lauf(rs, tuple((j,) for j in range(spalten)), schranke, labels, runden if aufrufe is None else aufrufe, fehlgriffe, abgebrochen)


def test_gegenprobe_verdict_branches(hand):
    lauf = _lauf(7, 13, 30.0)
    h = ev.HandAnalyse(hand, lauf, tuple(range(79)), 30.0, 58, 0, None)
    kind, text = ev.verdict_gegenprobe(h)
    assert kind == "success" and "nach 7 Runden" in text and "Schranke 30" in text and "6 neuen Spalten" in text and "alle 79 zulässigen" in text and "gibt 30 (gleich)" in text
    assert "0 dieser Wege negative" in text and "mit denen der ersten Runde 58" in text
    assert ev.verdict_gegenprobe(ev.HandAnalyse(hand, lauf, tuple(range(79)), 29.0, 58, 0, None))[0] == "error"       # Schranke weicht ab
    assert ev.verdict_gegenprobe(ev.HandAnalyse(hand, lauf, tuple(range(79)), 30.0, 58, 1, None))[0] == "error"      # ein Weg hat noch negative Kosten
    assert ev.verdict_gegenprobe(ev.HandAnalyse(hand, lauf, tuple(range(79)), 30.0 + 5e-7, 58, 0, None))[0] == "success"     # Toleranz 1e-6


def test_alpha_class_thresholds_are_ten_percent_and_inclusive():
    assert ev.klasse_runden(11.0, 10.0) == "etwa gleich viele"             # genau +10 %
    assert ev.klasse_runden(11.1, 10.0) == "mehr"
    assert ev.klasse_runden(9.0, 10.0) == "etwa gleich viele"              # genau -10 %
    assert ev.klasse_runden(8.9, 10.0) == "weniger"
    assert ev.klasse_runden(10.0, 10.0) == "etwa gleich viele"


def _zeile(alpha, runden, aufrufe, fehl, weniger, gleich, mehr, gleich_schranke=True, n=20, anz=12):
    st = lambda m: {"mittel": m, "median": m, "min": m, "max": m, "n": anz}  # noqa: E731
    return {"alpha": alpha, "n": n, "instanzen": anz, "runden": st(runden), "aufrufe": st(aufrufe), "fehlgriffe": st(fehl), "weniger": weniger, "gleich": gleich, "mehr": mehr,
            "schranke_gleich": gleich_schranke, "quelle": ""}


def test_smoothing_band_verdict_counts_and_classes():
    zeilen = [_zeile(0, 14.0, 14.0, 0, 0, 12, 0), _zeile(50, 14.5, 17.0, 3, 5, 2, 5), _zeile(80, 18.4, 23.6, 5, 1, 0, 11), _zeile(90, 9.0, 12.0, 8, 12, 0, 0)]
    kind, text = ev.verdict_glaettung_band(zeilen)
    assert kind == "info" and text.startswith("20 Kunden, 12 Instanzen, einfache Glättung zur Vorrunde")
    assert "α = 0,5: etwa gleich viele Runden (im Mittel 14,5 gegen 14,0; weniger / gleich / mehr in 5 / 2 / 5 von 12 Instanzen), mehr Pricing-Aufrufe (im Mittel 17,0 gegen 14,0)" in text
    assert "α = 0,8: mehr Runden (im Mittel 18,4 gegen 14,0" in text and "1 / 0 / 11 von 12" in text
    assert "α = 0,9: weniger Runden" in text and "in allen Instanzen und allen α gleich" in text
    assert "NICHT in allen gleich" in ev.verdict_glaettung_band([zeilen[0], _zeile(50, 14, 17, 3, 5, 2, 5, gleich_schranke=False)])[1]
    assert "nicht mehr Pricing-Aufrufe" in ev.verdict_glaettung_band([zeilen[0], _zeile(50, 14, 14, 0, 0, 12, 0)])[1]


def test_live_smoothing_verdict():
    ohne, mit = _lauf(7, 14, 30.0), _lauf(7, 14, 30.0, aufrufe=10, fehlgriffe=3)
    kind, text = ev.verdict_glaettung_live(80, ev.GlaettungHand(ohne, mit, None))
    assert kind == "info" and text == ("Mit α = 0,8: 7 Runden und 10 Pricing-Aufrufe (davon 3 Fehlgriffe) gegen 7 Runden und 7 Aufrufe ohne Glättung; Schranke in beiden 30. Eine Instanz, kein Befund.")
    kind0, text0 = ev.verdict_glaettung_live(0, ev.GlaettungHand(ohne, ohne, None))
    assert text0.startswith("Ohne Glättung: 7 Runden und 7 Pricing-Aufrufe, Schranke 30") and "α > 0" in text0


def _negativ_zeilen(e_depot, e_kunde, e_paare, l_depot, l_kunde, l_paare, n=6):
    def zeile(d, k, p):
        st = lambda m: {"mittel": m, "min": m, "max": m, "median": m, "n": n}  # noqa: E731
        return {"depot": st(d), "kunde": st(k), "paare": st(p), "n": n, "depot_gesamt": 30, "kunde_gesamt": 870, "paare_gesamt": 435}
    return {"erste": zeile(e_depot, e_kunde, e_paare), "letzte": zeile(l_depot, l_kunde, l_paare)}


def test_negative_verdict_names_means_shares_and_the_all_cases():
    kind, text = ev.verdict_negativ(_negativ_zeilen(30, 670.0, 435, 5.0, 160.0, 70.0))
    assert kind == "info" and "Erste Runde (6 Instanzen, 30 Kunden): in allen Instanzen alle 30 Bögen Depot-Kunde negativ" in text
    assert "im Mittel 670,0 von 870 Bögen Kunde-Kunde (77,0 %)" in text and "435,0 von 435 Kundenpaaren" in text and "(in allen Instanzen alle)" in text
    assert "Letzte Runde: im Mittel 5,0 von 30, 160,0 von 870 (18,4 %) und 70,0 von 435 Paaren" in text
    zeilen = _negativ_zeilen(29.5, 670.0, 430.0, 5.0, 160.0, 70.0)
    zeilen["erste"]["depot"]["min"] = 29
    zeilen["erste"]["paare"]["min"] = 430
    text2 = ev.verdict_negativ(zeilen)[1]
    assert "im Mittel 29,5 von 30 Bögen Depot-Kunde negativ" in text2 and "in allen Instanzen alle" not in text2.split("Letzte Runde")[0]


def test_master_verdict_with_and_without_deviations():
    paare = [("zufaellig", 1, 0, 756.1, 756.1), ("zufaellig", 5, 0, 811.3, 811.3)]
    kind, text = ev.verdict_master(paare)
    assert kind == "success" and "In allen 2 Paaren" in text and "größte Abweichung 0,000000" in text and "metrische Kosten" in text and "nicht gemessen" in text
    assert ev.verdict_master([("zufaellig", 1, 0, 756.1, 756.1 + 1e-7)])[0] == "success"          # Schwelle 1e-6
    kind2, text2 = ev.verdict_master(paare + [("lang", 5, 1, 800.0, 801.5)])
    assert kind2 == "warning" and "In 1 von 3 Paaren" in text2 and "größte Abweichung 1,500000" in text2


def test_rounds_verdict_names_the_medians_and_the_trend():
    def zeile(b, med, mn, mx, sp):
        return {"breite": b, "n_kunden": 30, "runden": {"median": med, "min": mn, "max": mx, "n": 6}, "spalten": {"median": sp}}
    kind, text = ev.verdict_runden([zeile(40, 18.0, 11, 31, 239.0), zeile(100, 20.0, 15, 29, 282.5), zeile(200, 23.5, 23, 35, 338.5)])
    assert kind == "info" and "30 Kunden, 6 Instanzen je Breite" in text and "Breite 40: Runden im Median 18,0 (Minimum 11, Maximum 31), Spalten im Median 239,0" in text and "steigt von Stufe zu Stufe" in text
    assert "steigt nicht von Stufe zu Stufe" in ev.verdict_runden([zeile(40, 18.0, 11, 31, 239.0), zeile(100, 18.0, 15, 29, 282.5)])[1]


def test_big_verdict_branches(hand):
    inst = ev.instanz_aus_seed(12, 7, 100)
    lauf = G.spaltenerzeugung(inst, None)
    s = ev.Settings()
    kind, text = ev.verdict_gross(s, ev.GrossAnalyse(inst, lauf, None, 0.1))
    assert kind == "info" and text.startswith("12 Kunden, Fensterbreite 100: die Spaltenerzeugung endet nach") and "Schranke 497,87" in text and "45,3 % darunter" in text
    assert f"{len(lauf.spalten) - 12} neue Spalten an die 12 Einzelfahrten" in text and f"{lauf.anzahl_runden} Runden" in text
    abgebr = G.Lauf(lauf.runden[:2], lauf.spalten, lauf.schranke, 3_000_001, 4, 0, True)
    kind2, text2 = ev.verdict_gross(s, ev.GrossAnalyse(inst, abgebr, None, 0.1))
    assert kind2 == "warning" and f"3{NBSP}000{NBSP}001 erzeugten Labels" in text2 and f"3{NBSP}000{NBSP}000" in text2 and "untere Schranken" in text2


def test_text_helpers():
    assert ev.knoten_text(0, 7) == "das Depot" and ev.knoten_text(8, 7) == "das Ende" and ev.knoten_text(3, 7) == "Kunde 3"
    assert ev.dijkstra_text(("schliesse", 3, -5.0), 7) == "Dijkstra schließt Kunde 3 ab, Abstand -5."
    assert ev.dijkstra_text(("verpasst", 4, 3, -9.0, -8.0, -5.0), 7) == ("Bogen 4 → 3: -9 + (-8) = -17 wäre besser als -5, aber Kunde 3 ist schon abgeschlossen (Dijkstra ändert ihn nicht mehr).")
    assert ev.fahrplan_text((2, 3, 3, 3, -3.0)) == "Kunde 2: Ankunft 3, Beginn 3, Last 3, reduzierte Kosten bis dahin -3"
    assert ev.fahrplan_text((5, 24, None, 7, "Last 7 > 6")) == "Kunde 5: Ankunft 24, Last 7 > 6"
    assert ev.weg_text((2, 7, 6)) == "2-7-6" and ev.weg_text(()) == "leer"


def test_statistics_helper_and_the_summaries_follow_from_the_single_values():
    s = ev.statistik([3, 1, 2, 10])
    assert (s["n"], s["mittel"], s["median"], s["min"], s["max"]) == (4, 4.0, 2.5, 1, 10)
    daten = {"zeilen": [
        {"n": 20, "alpha": 0, "instanzen": [{"runden": 10, "aufrufe": 10, "fehlgriffe": 0, "schranke": 1.0}, {"runden": 12, "aufrufe": 12, "fehlgriffe": 0, "schranke": 2.0}], "quelle": "q0"},
        {"n": 20, "alpha": 50, "instanzen": [{"runden": 9, "aufrufe": 12, "fehlgriffe": 3, "schranke": 1.0}, {"runden": 12, "aufrufe": 14, "fehlgriffe": 2, "schranke": 2.0}], "quelle": "q1"},
        {"n": 30, "alpha": 0, "instanzen": [{"runden": 1, "aufrufe": 1, "fehlgriffe": 0, "schranke": 1.0}], "quelle": "q2"}]}
    z = ev.zeilen_glaettung(daten, 20)
    assert [x["alpha"] for x in z] == [0, 50] and z[1]["weniger"] == 1 and z[1]["gleich"] == 1 and z[1]["mehr"] == 0 and z[1]["schranke_gleich"] is True
    assert z[1]["runden"]["mittel"] == 10.5 and z[1]["aufrufe"]["mittel"] == 13 and z[1]["fehlgriffe"]["mittel"] == 2.5
    daten["zeilen"][1]["instanzen"][1]["schranke"] = 2.5
    assert ev.zeilen_glaettung(daten, 20)[1]["schranke_gleich"] is False


@pytest.mark.parametrize("name", ["negativ", "runden", "glaettung", "master"])
def test_each_band_file_names_its_environment_and_every_row_its_source(name):
    daten = ev.lade_baender(name)
    assert "scipy" in daten["umgebung"] and daten["beschreibung"]
    assert daten["zeilen"] and all(z["quelle"].startswith("tools/messreihen.py") for z in daten["zeilen"])


def test_dijkstra_verdict_without_negative_arcs_but_with_a_deviation_is_an_error():
    kind, text = ev.verdict_dijkstra(_bogen(0, 0, 13.0, (1,), 12.0, (2,)))
    assert kind == "error" and "ABWEICHUNG" in text
