"""Feste Messreihen (data/*.json): Raster und Quellen stimmen, die Einzelwerte sind in sich schlüssig, und Stichproben werden mit dem Kern der Demo neu gerechnet.

Alle vier Reihen sind mit `tools/messreihen.py` und demselben Kern wie die App gerechnet (SplitMix64-Instanzen). Was nicht vom LP-Löser abhängt (negative Bögen der ersten Runde,
Schranken), wird exakt nachgerechnet; Runden hängen von den gewählten Dualpreisen ab (Entartung, HiGHS-Version) und werden nur mit Toleranz verglichen."""

import statistics

import pytest

import pdp_algorithm as A
import pdp_colgen as G
import pdp_constants as C
import pdp_evaluation as ev
import pdp_scenario as S


def _zeilen(name):
    return ev.lade_baender(name)["zeilen"]


# --- Raster, Quellen, Schlüssigkeit -----------------------------------------------------------------------------------------------------------

def test_negative_rows_cover_both_rounds_with_six_instances_and_name_their_source():
    zeilen = _zeilen("negativ")
    assert [z["runde"] for z in zeilen] == ["erste", "letzte"]
    for z in zeilen:
        assert [i["seed"] for i in z["instanzen"]] == list(range(6)) and (z["n"], z["breite"], z["k"]) == (30, 100, C.BAND_K)
        assert (z["depot_gesamt"], z["kunde_gesamt"], z["paare_gesamt"]) == (30, 870, 435)
        assert "tools/messreihen.py negativ" in z["quelle"] and f"{z['runde']} Runde" in z["quelle"] and "n = 30" in z["quelle"]
        for i in z["instanzen"]:
            assert 0 <= i["depot"] <= 30 and 0 <= i["kunde"] <= 870 and 0 <= i["paare"] <= 435


def test_the_last_round_has_fewer_negative_arcs_than_the_first_in_every_instance():
    erste, letzte = (z["instanzen"] for z in _zeilen("negativ"))
    assert all(l["depot"] < e["depot"] and l["kunde"] < e["kunde"] and l["paare"] < e["paare"] for e, l in zip(erste, letzte))


def test_round_rows_are_three_widths_with_six_instances_each():
    zeilen = _zeilen("runden")
    assert [z["breite"] for z in zeilen] == list(C.BAND_BREITEN)
    for z in zeilen:
        assert [i["seed"] for i in z["instanzen"]] == list(range(6)) and (z["n"], z["k"]) == (30, C.BAND_K)
        assert "tools/messreihen.py runden" in z["quelle"] and f"Breite {z['breite']}" in z["quelle"]
        assert all(i["spalten"] > 30 and i["runden"] >= 2 and i["labels"] > 0 and i["schranke"] > 0 for i in z["instanzen"])


def test_smoothing_rows_form_the_grid_and_keep_the_bound_in_every_instance():
    zeilen = _zeilen("glaettung")
    assert [(z["n"], z["alpha"]) for z in zeilen] == [(n, a) for n in (20, 30) for a in C.ALPHA_OPTIONEN]
    for z in zeilen:
        assert len(z["instanzen"]) == (12 if z["n"] == 20 else 6) and f"α = {z['alpha']} %" in z["quelle"]
        assert all(i["aufrufe"] == i["runden"] + i["fehlgriffe"] for i in z["instanzen"])
    for n in (20, 30):
        assert all(r["schranke_gleich"] for r in ev.zeilen_glaettung(ev.lade_baender("glaettung"), n))
    ohne = {z["n"]: z for z in zeilen if z["alpha"] == 0}
    assert all(i["fehlgriffe"] == 0 and i["aufrufe"] == i["runden"] for z in ohne.values() for i in z["instanzen"])      # ohne Glättung gibt es keinen Fehlgriff


def test_master_rows_form_the_grid_and_both_masters_agree_in_every_pair():
    zeilen = _zeilen("master")
    assert [(z["typ"], z["k"]) for z in zeilen] == [(t, k) for t in ("zufaellig", "gruppiert", "lang") for k in (1, 5, 8)]
    for z in zeilen:
        assert [i["seed"] for i in z["instanzen"]] == list(range(5)) and "tools/messreihen.py master" in z["quelle"]
        assert all(abs(i["ueberdeckung"] - i["partition"]) < 1e-6 for i in z["instanzen"])
    for t in ("zufaellig", "gruppiert", "lang"):
        k1, k5, k8 = ([i["ueberdeckung"] for i in z["instanzen"]] for z in zeilen if z["typ"] == t)
        assert all(a <= b + 1e-6 <= c + 2e-6 for a, b, c in zip(k1, k5, k8))                    # größeres Gedächtnis: höhere oder gleiche Schranke
    assert len(ev.paare_master(ev.lade_baender("master"))) == 45


def test_every_band_file_names_python_and_scipy_and_every_row_its_source():
    for name in ("negativ", "runden", "glaettung", "master"):
        d = ev.lade_baender(name)
        assert d["umgebung"].startswith("Python 3.") and "scipy" in d["umgebung"] and d["beschreibung"]
        assert all(z["quelle"].startswith("tools/messreihen.py") for z in d["zeilen"])


def test_summaries_follow_from_the_single_values():
    zn = {z["runde"]: ev.zeile_negativ(z) for z in _zeilen("negativ")}
    z0 = _zeilen("negativ")[0]["instanzen"]
    assert zn["erste"]["kunde"]["mittel"] == sum(i["kunde"] for i in z0) / 6 and zn["erste"]["depot"]["min"] == min(i["depot"] for i in z0)
    for z in _zeilen("runden"):
        s = ev.zeile_runden(z)
        assert s["runden"]["max"] == max(i["runden"] for i in z["instanzen"]) and s["spalten"]["median"] == statistics.median(i["spalten"] for i in z["instanzen"])
        assert s["labels"]["mittel"] == statistics.mean(i["labels"] for i in z["instanzen"])


# --- Stichproben neu gerechnet -----------------------------------------------------------------------------------------------------------

def test_first_round_counts_are_reproduced_for_all_six_instances():
    """Die erste Runde braucht keinen LP-Löser: die Zählung stimmt exakt."""
    for i in _zeilen("negativ")[0]["instanzen"]:
        inst = S.instanz_aus_seed(30, i["seed"], 100)
        z = A.negativ_zaehlung(inst, S.einzelfahrt_preise(inst))
        assert (z.depot_negativ, z.kunde_negativ, z.paare_negativ) == (i["depot"], i["kunde"], i["paare"])


def test_last_round_counts_are_plausible_on_a_sample():
    """Die Dualpreise der letzten Runde hängen vom LP-Löser ab (Entartung): die Zählung muss in der Größenordnung der Datei liegen, nicht exakt gleich sein."""
    i = _zeilen("negativ")[1]["instanzen"][1]
    inst = S.instanz_aus_seed(30, 1, 100)
    z = A.negativ_zaehlung(inst, G.spaltenerzeugung(inst, C.BAND_K).runden[-1].pi)
    assert 0.5 * i["kunde"] <= z.kunde_negativ <= 2 * i["kunde"] and z.depot_negativ < 30 and z.paare_negativ < 435


@pytest.mark.parametrize("seed", [0, 1, 3])
def test_round_row_bound_is_reproduced_and_rounds_within_the_solver_tolerance(seed):
    z = next(z for z in _zeilen("runden") if z["breite"] == 40)["instanzen"][seed]
    lauf = G.spaltenerzeugung(S.instanz_aus_seed(30, seed, 40), C.BAND_K, max_labels=10 ** 9)
    assert lauf.schranke == pytest.approx(z["schranke"], abs=1e-4)                              # die Schranke hängt nicht vom Löser ab
    assert abs(lauf.anzahl_runden - z["runden"]) <= 4 and abs(len(lauf.spalten) - z["spalten"]) <= 0.3 * z["spalten"]


@pytest.mark.parametrize("alpha", [0, 50, 90])
def test_smoothing_row_bound_is_reproduced_and_rounds_within_the_solver_tolerance(alpha):
    z = next(z for z in _zeilen("glaettung") if z["n"] == 20 and z["alpha"] == alpha)
    for seed in (0, 5):
        lauf = G.spaltenerzeugung(S.instanz_aus_seed(20, seed, 100), C.BAND_K, alpha=alpha / 100, max_labels=10 ** 9)
        j = z["instanzen"][seed]
        assert lauf.schranke == pytest.approx(j["schranke"], abs=1e-4) and abs(lauf.anzahl_runden - j["runden"]) <= 5
        assert lauf.aufrufe == lauf.anzahl_runden + lauf.fehlgriffe


def test_master_row_bounds_are_reproduced_for_both_masters_on_a_sample():
    for k in (1, 5):
        z = next(z for z in _zeilen("master") if z["typ"] == "zufaellig" and z["k"] == k)
        for seed in (0, 1):
            inst = S.instanz_aus_seed(30, seed, 100)
            ue, pa = G.spaltenerzeugung(inst, k).schranke, G.spaltenerzeugung(inst, k, "partition").schranke
            assert ue == pytest.approx(z["instanzen"][seed]["ueberdeckung"], abs=1e-4) and pa == pytest.approx(z["instanzen"][seed]["partition"], abs=1e-4)


def test_the_messreihen_tool_reproduces_a_row_of_the_negative_series():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("messreihen", Path(__file__).resolve().parent.parent / "tools" / "messreihen.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    d = m.messung_negativ(n=30, breite=100, seeds=range(2))
    assert d["zeilen"][0]["instanzen"] == _zeilen("negativ")[0]["instanzen"][:2]
