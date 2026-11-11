"""Jede Zahl der README an den festen Zufalls-Seeds nachgerechnet (DEMO-PLAYBOOK §4, §11a). Zeiten werden nie festgeschrieben.

Die README-Tabellen werden aus den Messreihen in data/ erzeugt (`tools/readme_tabellen.py`); der Test erzeugt sie noch einmal und sucht sie in der README. Die Zahl-zu-Test-Tabelle
in der README nennt für jede Zahl den Test. Die Zahlen der früheren Messreihe stehen nur aus der Datei da und werden hier nicht neu gerechnet; der Test prüft, dass die README sie
richtig aus der Datei übernimmt. Runden hängen vom LP-Löser ab: Tests prüfen Schranken exakt und Runden nur mit Toleranz."""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest
from alt_instanz import alte_instanz
from conftest import hand_d

import pdp_algorithm as A
import pdp_colgen as G
import pdp_constants as C
import pdp_evaluation as ev
import pdp_scenario as S
from pdp_master import loese_master
from pdp_texts import ASSUMPTIONS_MARKDOWN

ROOT = Path(__file__).resolve().parent.parent
NBSP = " "


def _norm(text: str) -> str:
    return text.replace(NBSP, " ")


README = _norm((ROOT / "README.md").read_text(encoding="utf-8"))
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _tabellen() -> dict:
    spec = importlib.util.spec_from_file_location("readme_tabellen", ROOT / "tools" / "readme_tabellen.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return {k: _norm(v) for k, v in m.alle().items()}


def test_readme_tables_are_generated_from_the_data():
    for name, text in _tabellen().items():
        assert text in README, name


def test_the_assumptions_text_of_the_app_is_in_the_readme_verbatim():
    assert _norm(ASSUMPTIONS_MARKDOWN).strip() in README


def test_readme_names_the_same_test_count_as_the_suite():
    p = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "tests", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True, timeout=300)
    m = re.search(r"(\d+) tests? collected", p.stdout)
    assert m, p.stdout[-300:]
    assert f"{m.group(1)} Tests (`pytest --collect-only -q tests`)" in README


def test_forbidden_words_do_not_occur_in_the_texts():
    texte = {"README": README, "app": APP, "texts": (ROOT / "pdp_texts.py").read_text(encoding="utf-8"), "constants": (ROOT / "pdp_constants.py").read_text(encoding="utf-8")}
    for name, t in texte.items():
        for wort in ("trägt", "tragen", "läuft lokal", "Saatwert", "Phase 0", "Stück", "geplant"):
            assert wort not in t, (name, wort)


# --- Handbeispiel ---------------------------------------------------------------------------------------------------------------------------

def test_hand_example_prices_and_negative_arcs(hand, pi_erste_runde):
    einzel = [2 * hand_d(0, j) for j in range(1, 8)]
    assert einzel == [6, 6, 10, 6, 6, 6, 10] and sum(einzel) == 50 and [hand_d(0, j) for j in range(1, 8)] == [3, 3, 5, 3, 3, 3, 5]
    assert [hand_d(0, j) - pi_erste_runde[j] for j in range(1, 8)] == [-3, -3, -5, -3, -3, -3, -5]
    z = A.negativ_zaehlung(hand, pi_erste_runde)
    assert (z.depot_negativ, z.kunde_negativ, z.paare_negativ) == (7, 27, 12) and (z.depot_gesamt, z.kunde_gesamt, z.paare_gesamt) == (7, 42, 21)
    assert z.kleinstes_paar == (3, 4) and z.kleinster_kreis == 2 * 2 - 10 - 6 == -12
    assert (z.depot_negativ + z.kunde_negativ, z.depot_gesamt + z.kunde_gesamt) == (34, 49) and "(zusammen 34 von 49 Bögen)" in README and "34 von 49 Bögen" in APP
    plus = A.negativ_zaehlung(hand, pi_erste_runde, "plus")
    assert (plus.depot_negativ, plus.kunde_negativ, plus.paare_negativ) == (0, 0, 0)
    for art in ("ueberdeckung", "partition"):
        m = loese_master(hand, G.einzelfahrten(hand), art)
        assert m.wert == pytest.approx(50) and m.pi == pytest.approx(tuple(pi_erste_runde))


def test_hand_example_dijkstra(hand, pi_erste_runde):
    plus = A.dijkstra(hand, pi_erste_runde, "plus")
    anzahl, laenge, weg = A.beste_einfache_wege(hand, pi_erste_runde, "plus")
    assert (plus.weg, plus.laenge, plus.verpasst) == ((1,), 12, 0) and (anzahl, laenge, weg) == (13699, 12, (1,))
    minus = A.dijkstra(hand, pi_erste_runde, "minus")
    assert minus.schritte[1] == ("schliesse", 3, -5.0)
    # Gleichstandsregel: Kunde 3 und Kunde 7 haben beide den Abstand -5; mit Kunde 7 zuerst ändern sich die Zahlen (README und App nennen die Regel und -22)
    assert -5.0 == hand_d(0, 7) * -1 == hand_d(0, 3) * -1 and pi_erste_runde[7] - hand_d(0, 7) == pi_erste_runde[3] - hand_d(0, 3)
    umgekehrt = A.dijkstra(hand, pi_erste_runde, "minus", kleinere_nummer_zuerst=False)
    assert umgekehrt.schritte[1] == ("schliesse", 7, -5.0)
    assert (umgekehrt.weg, umgekehrt.laenge, umgekehrt.verpasst) == ((7, 6, 3, 5, 4, 1, 2), -22, 20)
    assert A.weg_laenge(hand, pi_erste_runde, umgekehrt.weg, "minus") == -22 and A.beste_einfache_wege(hand, pi_erste_runde, "minus")[1] == -28
    for text in (README, APP):
        assert "bei gleichem Abstand zuerst der Kunde mit der kleineren Nummer" in text or "Gleichstandsregel: bei gleichem Abstand zuerst der Kunde mit der kleineren Nummer" in text
    assert "7-6-3-5-4-1-2 mit Länge −22 und 20 verpassten Verbesserungen" in README and "Länge −22 (20 verpasste Verbesserungen)" in APP
    assert [s for s in minus.schritte if s[0] == "verpasst"][0][:4] == ("verpasst", 4, 3, -9.0) and -9 + (hand_d(4, 3) - 10) == -17
    assert (minus.weg, minus.laenge, minus.verpasst) == ((3, 4, 5, 1, 7, 6, 2), -24, 21)
    assert A.beste_einfache_wege(hand, pi_erste_runde, "minus")[1:] == (-28, (4, 3, 5, 1, 2, 7, 6))
    assert A.pruefe_route(hand, minus.weg) == (False, "unzulässig bei Kunde 5: Last 7 > 6")
    assert A.pruefe_route(hand, (4, 3, 5, 1, 2, 7, 6)) == (False, "unzulässig bei Kunde 3: Ankunft 24 > Fensterende 15")


def test_hand_example_labeling(hand, pi_erste_runde):
    erg = A.labeling(hand, pi_erste_runde, None)
    assert (erg.erzeugt, erg.verworfen, erg.verdraengt, erg.lebend) == (56, 20, 0, 36) and erg.wege[0] == (-10, (2, 7, 6))
    assert hand_d(0, 2) + hand_d(2, 7) + hand_d(7, 6) + hand_d(6, 0) == 12 and pi_erste_runde[2] + pi_erste_runde[7] + pi_erste_runde[6] == 22
    assert [(j, a, b, q) for j, a, b, q, _ in A.fahrplan(hand, pi_erste_runde, (2, 7, 6))] == [(2, 3, 3, 3), (7, 9, 9, 5), (6, 13, 13, 6)]
    wege = A.alle_zulaessigen_wege(hand)
    rc = [A.reduzierte_kosten(hand, pi_erste_runde, w) for w in wege]
    assert len(wege) == 79 and min(rc) == pytest.approx(-10) and sum(1 for r in rc if r < -1e-9) == 58
    beste = {w for w, r in zip(wege, rc) if r == pytest.approx(-10)}
    assert beste == {(2, 7, 6), (6, 7, 1), (5, 6, 7, 1)}
    assert "zählt 79 zulässige Wege; 3 davon haben den besten Wert −10 (2-7-6, 6-7-1 und 5-6-7-1), 58 haben negative reduzierte Kosten." in README
    geliefert = {r for _, r in erg.wege}
    assert len(geliefert) == 35 and geliefert <= set(wege)


def test_hand_example_highs_bound():
    inst = S.handbeispiel()
    for art in ("ueberdeckung", "partition"):
        lauf = G.spaltenerzeugung(inst, None, art, spalten_je_runde=1)
        assert lauf.schranke == pytest.approx(30) and not lauf.abgebrochen
    h = ev.analyse_hand(False)
    assert h.fehler is None and h.gegen_wert == pytest.approx(30) and len(h.wege) == 79 and (h.negativ_erste, h.negativ_letzte) == (58, 0)


# --- Kundeninstanzen live ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("n, breite, seed, erste, schranke", [(12, 100, 7, "909,75", "497,87"), (20, 40, 7, "1 612,66", "710,77"), (20, 100, 3, "1 468,28", "509,43")])
def test_live_presets_numbers(n, breite, seed, erste, schranke):
    inst = S.instanz_aus_seed(n, seed, breite)
    lauf = G.spaltenerzeugung(inst, None)
    assert not lauf.abgebrochen
    zeile = f"| {n} Kunden, Fensterbreite {breite} ({seed}) | {erste} | {schranke} |"
    assert _norm(zeile) in README
    assert _norm(ev.zahl(lauf.runden[0].master_wert, 2)) == erste and _norm(ev.zahl(lauf.schranke, 2)) == schranke
    assert lauf.runden[0].master_wert == pytest.approx(sum(2 * inst.d[0][j] for j in range(1, n + 1)))


def test_the_presets_of_the_app_are_the_ones_of_the_readme_table():
    live = {(p["n"], p["breite"], p["seed"]) for p in C.PRESETS.values()}
    assert {(12, 100, 7), (20, 40, 7), (20, 100, 3)} <= live


# --- Aussagen über die Messreihen --------------------------------------------------------------------------------------------------------------

def test_statements_about_the_bands():
    neg = ev.lade_baender("negativ")
    erste = neg["zeilen"][0]["instanzen"]
    assert len(erste) == 6 and all(i["depot"] == 30 for i in erste) and all(i["paare"] == 435 for i in erste)
    assert "In der ersten Runde sind in allen 6 Instanzen alle 30 Bögen vom Depot und alle 435 Kundenpaare negativ." in README
    zr = [ev.zeile_runden(z) for z in ev.lade_baender("runden")["zeilen"]]
    med = [z["runden"]["median"] for z in zr]
    assert all(b > a for a, b in zip(med, med[1:])) and "Der Median der Runden steigt von Breite 40 über 100 auf 200 von Stufe zu Stufe." in README
    gl = ev.lade_baender("glaettung")
    g20, g30 = ev.zeilen_glaettung(gl, 20), ev.zeilen_glaettung(gl, 30)
    by = lambda zz, a: next(z for z in zz if z["alpha"] == a)  # noqa: E731
    for zz in (g20, g30):
        assert ev.klasse_runden(by(zz, 50)["runden"]["mittel"], by(zz, 0)["runden"]["mittel"]) == "etwa gleich viele"
        assert by(zz, 50)["aufrufe"]["mittel"] > by(zz, 0)["aufrufe"]["mittel"] and all(z["schranke_gleich"] for z in zz)
    assert (ev.zahl(by(g20, 50)["runden"]["mittel"], 1), ev.zahl(by(g20, 0)["runden"]["mittel"], 1)) == ("13,7", "13,7")
    assert (ev.zahl(by(g30, 50)["runden"]["mittel"], 1), ev.zahl(by(g30, 0)["runden"]["mittel"], 1)) == ("19,8", "20,5")
    assert (ev.zahl(by(g20, 50)["aufrufe"]["mittel"], 1), ev.zahl(by(g20, 0)["aufrufe"]["mittel"], 1)) == ("17,5", "13,7")
    assert (ev.zahl(by(g30, 50)["aufrufe"]["mittel"], 1), ev.zahl(by(g30, 0)["aufrufe"]["mittel"], 1)) == ("22,8", "20,5")
    assert "13,7 gegen 13,7 bei 20 Kunden, 19,8 gegen 20,5 bei 30 Kunden" in README and "17,5 gegen 13,7 und 22,8 gegen 20,5" in README
    assert [by(g20, a)["mehr"] for a in (80, 90)] == [11, 11] and [by(g30, a)["mehr"] for a in (80, 90)] == [6, 6] and (g20[0]["instanzen"], g30[0]["instanzen"]) == (12, 6)
    assert "bei 20 Kunden in 11 von 12 Instanzen mehr Runden als ohne Glättung, bei 30 Kunden in 6 von 6 Instanzen" in README
    paare = ev.paare_master(ev.lade_baender("master"))
    assert len(paare) == 45 and max(abs(u - p) for _, _, _, u, p in paare) < 1e-6
    zr_n = {z["breite"]: z["runden"] for z in zr}
    assert (zr_n[40]["min"], zr_n[40]["max"], zr_n[40]["median"]) == (11, 31, 18.0) and (zr_n[100]["min"], zr_n[100]["max"], zr_n[100]["median"]) == (15, 29, 20.0)
    assert "bei Breite 40 reichen die Runden von 11 bis 31 bei einem Median von 18,0, bei Breite 100 von 15 bis 29 bei einem Median von 20,0" in README
    assert "bei Fensterbreite 40 reichen die Runden von 11 bis 31 bei einem Median von 18,0" in APP
    assert "In allen 45 Paaren ist die Schranke mit Überdeckung und mit Partitionierung gleich (größte Abweichung unter 0,000001)." in README


def test_columns_per_round_and_instance_counts_are_stated_as_measured():
    assert C.SPALTEN_JE_RUNDE == 15
    assert "bis zu 15 je Runde, im Handbeispiel eine" in README and "bis zu 15 je Runde, im Handbeispiel eine" in APP
    inst = S.handbeispiel()
    assert all(len(r.neue) <= 1 for r in G.spaltenerzeugung(inst, None, spalten_je_runde=1).runden)
    gl = ev.lade_baender("glaettung")
    assert (ev.zeilen_glaettung(gl, 20)[0]["instanzen"], ev.zeilen_glaettung(gl, 30)[0]["instanzen"]) == (12, 6)
    assert "bei der Glättung mit 20 Kunden 12 Instanzen je Zelle" in ASSUMPTIONS_MARKDOWN and "mit 30 Kunden 6 Instanzen je Zelle" in ASSUMPTIONS_MARKDOWN
    assert "bei 20 Kunden 12, bei 30 Kunden 6 Instanzen" in APP


def test_memory_k_of_the_bands_is_stated_as_measured():
    """Die Messreihen rechnen mit k = 5, nur der Vergleich der Master mit k = 1, 5 und 8 (data/baender_*.json)."""
    for name in ("negativ", "runden", "glaettung"):
        for z in ev.lade_baender(name)["zeilen"]:
            assert f"Pricing k = {C.BAND_K}" in z["quelle"], (name, z["quelle"])
    assert C.BAND_K == 5 and sorted({z["k"] for z in ev.lade_baender("master")["zeilen"]}) == [1, 5, 8]
    satz = "der Vergleich von Überdeckung und Partitionierung mit k = 1, 5 und 8"
    assert satz in README and satz in _norm(ASSUMPTIONS_MARKDOWN)
    assert "nur der Vergleich von Überdeckung und Partitionierung rechnet mit k = 1, 5 und 8" in README
    assert "die Messreihen mit 30 Kunden rechnen mit einem Gedächtnis" not in README and "Die Messreihen mit 30 Kunden rechnen mit einem Gedächtnis" not in APP
    assert "beim Vergleich der Master auch k = 1 und 8" in APP


def test_endless_rounds_are_prevented_by_either_condition_alone(hand, pi_erste_runde):
    """Mit negativen Kreisen: Die Grenzen allein (Gedächtnis k = 1 erlaubt Wiederholungen) beenden das Labeling, weil die Zeit bei jedem Halt um mindestens die Bedienzeit wächst."""
    erg = A.labeling(hand, pi_erste_runde, 1, behalte_labels=True)
    assert not erg.abgebrochen and any(len(set(r)) < len(r) for _, r in erg.wege)
    ls = erg.labels
    assert all(L.zeit >= ls[L.eltern].zeit + hand.svc for L in ls if L.eltern >= 0 and ls[L.eltern].knoten != 0) and hand.svc > 0
    assert all(L.zeit <= hand.due[L.knoten] for L in ls)
    elementar = A.labeling(hand, pi_erste_runde, None)     # die Regel allein: höchstens n Kunden je Weg
    assert not elementar.abgebrochen and all(len(set(r)) == len(r) for _, r in elementar.wege)
    for text in (README, APP):
        assert "Die endlosen Runden verhindert aber schon jede der beiden Bedingungen allein: die Regel „jeder Kunde höchstens einmal“ oder die Grenzen" in text
        assert "Dürfte ein Kunde mehrmals vorkommen und gäbe es keine" in text
    assert "Ohne Last- und Zeitgrenzen gäbe es unter den Wegen mit Wiederholungen" not in README


def test_dual_price_is_the_saving_only_in_the_first_round(hand, pi_erste_runde):
    """Erste Runde: Der Master besteht aus den Einzelfahrten, ohne Kunde j sinkt er genau um die Einzelfahrt c_j = π_j. Später: höchstens π_j (Überdeckung, π ≥ 0)."""
    einzel = [2 * hand_d(0, j) for j in range(1, 8)]
    assert [pi_erste_runde[j] for j in range(1, 8)] == einzel and sum(einzel) - einzel[0] == 50 - pi_erste_runde[1]
    lauf = G.spaltenerzeugung(hand, None, "ueberdeckung", 0.0, spalten_je_runde=1)
    for r in lauf.runden:
        assert all(p >= -1e-9 for p in r.pi[1:])
        for j in range(1, 8):                                # Dualitätsschranke: ohne die Zeile j ist π mit π_j = 0 dual zulässig, also sinkt der Wert um höchstens π_j
            ohne = list(r.pi)
            ohne[j] = 0.0
            assert sum(ohne) == pytest.approx(r.master_wert - r.pi[j])
    for text in (README, APP):
        assert "höchstens" in text and "nur in der ersten Runde, in der der Master aus den Einzelfahrten besteht, sinkt er genau um π(j)" in text


def test_smoothing_centre_is_the_price_vector_of_the_last_search_of_the_previous_round():
    """Zentrum = die Preise, mit denen das Pricing der Vorrunde gerechnet hat (nach einem Fehlgriff die echten Dualpreise), nicht die Dualpreise des Masters der Vorrunde."""
    inst = S.handbeispiel()
    lauf = G.spaltenerzeugung(inst, None, "ueberdeckung", 0.8, spalten_je_runde=1)
    assert lauf.runden[0].pi_pricing == lauf.runden[0].pi and any(r.fehlgriffe for r in lauf.runden) and any(not r.fehlgriffe for r in lauf.runden[1:])
    for vor, r in zip(lauf.runden, lauf.runden[1:]):
        if r.fehlgriffe:
            erwartet = r.pi
        else:
            erwartet = tuple(0.8 * a + 0.2 * b for a, b in zip(vor.pi_pricing, r.pi))
        assert r.pi_pricing == pytest.approx(erwartet)
    assert any(vor.pi_pricing != vor.pi for vor in lauf.runden[:-1])      # das Zentrum ist nicht immer das echte Dual der Vorrunde
    assert "α · (Preise, mit denen das Pricing der Vorrunde gerechnet hat) + (1 − α)" in README and "α · (Preise, mit denen das Pricing der Vorrunde gerechnet hat) + (1 − α) · π" in APP


def test_the_sentences_about_unmeasured_things_say_so():
    assert "ist nicht gezählt" in README and "nicht neu gerechnet" in README and "nicht geprüft" in README
    assert "Wie viele zulässige Wege es bei 30 Kunden insgesamt gibt, ist nicht gezählt" in README
    assert "(6 neue Spalten zusätzlich zu den 7 Einzelfahrten, zusammen 13 von 79 Wegen)" in README


def test_comparison_table_follows_from_the_data():
    t = _tabellen()["vergleich"]
    fr = ev.lade_fruehere_messreihe()
    assert t in README
    assert "nicht neu gerechnet" in fr["beschreibung"] and all(k in fr for k in ("negativ", "runden", "glaettung", "master", "v4_schranken"))
    assert all("quelle" in fr[k] for k in ("negativ", "runden", "master", "v4_schranken")) and all("quelle" in fr["glaettung"][k] for k in ("n20", "n30"))
    assert fr["master"]["paare"] == 47 and fr["master"]["groesste_abweichung"] == 0.0


def test_cross_check_with_the_earlier_implementation():
    """Der Kern dieser Demo auf den 6 früheren Instanzen (random.Random, 30 Kunden, Breite 100, k = 5): dieselbe Schranke wie in out_v4.txt, auf 4 Stellen."""
    erwartet = ev.lade_fruehere_messreihe()["v4_schranken"]["werte"]
    for seed, soll in enumerate(erwartet):
        lauf = G.spaltenerzeugung(alte_instanz(30, seed, 100.0), C.BAND_K)
        assert round(lauf.schranke, 4) == pytest.approx(soll, abs=1.1e-4), seed
        assert lauf.runden[-1].neue == () and not lauf.abgebrochen
