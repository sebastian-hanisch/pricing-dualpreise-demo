"""End-to-end Smoke-Test via Streamlits offiziellem AppTest-Framework: lädt app.py mit den Standardeinstellungen, klickt jeden Knopf, fährt jeden Regler an seine Grenzen
(einzeln sowie alle Minima und alle Maxima zugleich), prüft jede Voreinstellung mit ihrer erwarteten Verdikt-Zeile und den Permalink.
Expander werden nie per Index oder als feste Titelliste angesprochen (DEMO-PLAYBOOK §2)."""

import os
import re

import pytest
from streamlit.testing.v1 import AppTest

import pdp_constants as C

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))  # unter Last (parallele Läufe) reichen 180 s nicht immer; Umgebungsvariable zum Anpassen
NBSP = " "
PLUS = "Entfernung + Dualpreis (nie negativ)"


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _texts(at) -> str:
    return " ".join(x.value for kind in (at.success, at.warning, at.info, at.error) for x in kind).replace(NBSP, " ")


def _alle_texte(at) -> str:
    return (_texts(at) + " " + " ".join(m.value for m in at.markdown)).replace(NBSP, " ")


def test_app_loads_without_exception():
    at = _fresh_app()
    assert not at.error


def test_every_button_click_does_not_raise():
    labels = [b.label for b in _fresh_app().button]
    assert labels, "keine Buttons gefunden"
    for index, label in enumerate(labels):
        at = _fresh_app()
        at.button[index].click().run(timeout=TIMEOUT)
        assert not at.exception, (label, [str(e) for e in at.exception])


def test_every_slider_at_its_min_and_max_does_not_raise():
    labels = [s.label for s in _fresh_app().slider]
    assert labels, "keine Slider gefunden"
    for index, label in enumerate(labels):
        for edge in ("min", "max"):
            at = _fresh_app()
            slider = at.slider[index]
            value = slider.min if edge == "min" else slider.max
            if isinstance(slider.value, int):
                value = int(value)
            slider.set_value(value).run(timeout=TIMEOUT)
            assert not at.exception, (label, edge, [str(e) for e in at.exception])


@pytest.mark.parametrize("edge", ["min", "max"])
def test_all_controls_at_their_minimum_or_maximum_together(edge):
    at = _fresh_app()
    for key in ("n_slider", "breite_slider"):
        s = at.sidebar.slider(key=key)
        s.set_value(int(s.min if edge == "min" else s.max))
    at.sidebar.select_slider(key="alpha_pct").set_value(max(C.ALPHA_OPTIONEN) if edge == "max" else 0)
    at.sidebar.toggle(key="partition").set_value(edge == "max")
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert not at.error


def test_seed_extremes_do_not_raise():
    for seed in (0, C.SEED_MAX):
        at = _fresh_app()
        at.sidebar.number_input(key="seed_input").set_value(seed).run(timeout=TIMEOUT)
        assert not at.exception, (seed, [str(e) for e in at.exception])


def test_every_alpha_option_runs():
    for a in C.ALPHA_OPTIONEN:
        at = _fresh_app()
        at.sidebar.select_slider(key="alpha_pct").set_value(a).run(timeout=TIMEOUT)
        assert not at.exception and not at.error, a


# --- Voreinstellungen: erwartete Verdikt-Zeile -------------------------------------------------------------------------------------------------

GEGENPROBE = "ein Master über alle 79 zulässigen elementaren Wege als Spalten gibt 30 (gleich)"


@pytest.mark.parametrize("name, erwartet", [
    ("Standard: Handbeispiel und 12 Kunden", ["Dijkstra trifft den besten Weg nicht", "12 Kunden, Fensterbreite 100", "Schranke 497,87", "Ohne Glättung:", GEGENPROBE]),
    ("Handbeispiel mit Glättung α = 0,8", ["Mit α = 0,8:", "Schranke in beiden 30", "12 Kunden, Fensterbreite 100", "Schranke 497,87", GEGENPROBE]),
    ("Partitionierungs-Master, 15 Kunden", ["Master (Partitionierung)", GEGENPROBE, "15 Kunden, Fensterbreite 100"]),
    ("20 Kunden, enge Fenster (40)", ["20 Kunden, Fensterbreite 40", "Schranke 710,77"]),
    ("20 Kunden, weite Fenster (100)", ["20 Kunden, Fensterbreite 100", "Schranke 509,43"]),
])
def test_each_preset_runs_and_shows_its_expected_verdict(name, erwartet):
    at = _fresh_app()
    at.sidebar.button(key=f"preset_{name}").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    text = _alle_texte(at)
    for stueck in erwartet:
        assert stueck in text, (name, stueck)


def test_preset_sets_every_regler_value():
    at = _fresh_app()
    name = "Handbeispiel mit Glättung α = 0,8"
    at.sidebar.button(key=f"preset_{name}").click().run(timeout=TIMEOUT)
    p = C.PRESETS[name]
    assert [at.sidebar.slider(key=k).value for k in ("n_slider", "breite_slider")] == [p["n"], p["breite"]]
    assert at.sidebar.number_input(key="seed_input").value == p["seed"] and at.sidebar.select_slider(key="alpha_pct").value == p["alpha"] and at.sidebar.toggle(key="partition").value is p["partition"]


# --- Permalink ---------------------------------------------------------------------------------------------------------------------------

def test_permalink_sets_the_regler_clamps_to_the_bounds_and_snaps_to_the_grid():
    at = AppTest.from_file(APP_PATH)
    at.query_params["n"] = "999"          # über dem Maximum
    at.query_params["b"] = "63"           # nicht auf dem Raster 40, 60, 80, 100
    at.query_params["a"] = "65"           # zwischen den Optionen 50 und 80 (gleich weit): die kleinere gewinnt
    at.query_params["p"] = "True"
    at.query_params["seed"] = "42"
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert at.sidebar.slider(key="n_slider").value == C.N_MAX
    assert at.sidebar.slider(key="breite_slider").value == 60
    assert at.sidebar.select_slider(key="alpha_pct").value == 50
    assert at.sidebar.toggle(key="partition").value is True
    assert at.sidebar.number_input(key="seed_input").value == 42


def test_permalink_ignores_garbage_values():
    at = AppTest.from_file(APP_PATH)
    at.query_params["n"] = "abc"
    at.query_params["seed"] = ""
    at.query_params["a"] = "x"
    at.query_params["p"] = "vielleicht"
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert at.sidebar.slider(key="n_slider").value == C.DEFAULT_N and at.sidebar.select_slider(key="alpha_pct").value == C.DEFAULT_ALPHA and at.sidebar.toggle(key="partition").value is False


# --- Experimente -------------------------------------------------------------------------------------------------------------------------

def test_the_round_slider_changes_the_dual_prices_and_the_negative_counts():
    at = _fresh_app()
    letzte = at.slider(key="runde_hand").max
    assert at.slider(key="runde_hand").value == 1 and letzte >= 2
    at.slider(key="runde_hand").set_value(letzte).run(timeout=TIMEOUT)
    assert not at.exception
    z = [m for m in at.metric if m.label == "Negative Bögen Depot → Kunde"]
    assert z and z[0].value != "7 von 7"                    # in der letzten Runde sind nicht mehr alle Bögen negativ


def test_the_length_type_plus_shows_no_negative_arc_and_a_matching_verdict():
    at = _fresh_app()
    at.radio(key="laengentyp").set_value(PLUS).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert [m.value for m in at.metric if m.label == "Negative Bögen Depot → Kunde"] == ["0 von 7"]
    assert [m.value for m in at.metric if m.label == "Negative Bögen Kunde → Kunde"] == ["0 von 42"]
    assert "Alle Bogenlängen sind nicht negativ (gleich)" in _texts(at)


def test_the_labeling_round_slider_shows_the_last_round_without_a_new_column():
    at = _fresh_app()
    letzte = at.slider(key="runde_labeling").max
    at.slider(key="runde_labeling").set_value(letzte).run(timeout=TIMEOUT)
    assert not at.exception
    assert "findet das Pricing keine Route mit negativen reduzierten Kosten" in _alle_texte(at)


def test_the_round_sliders_follow_when_the_number_of_rounds_shrinks():
    """Mit Partitionierung hat das Handbeispiel eine Runde mehr als mit Überdeckung: steht der Regler auf der letzten Runde und wird der Master umgestellt, bleibt er innerhalb der Grenzen."""
    at = _fresh_app()
    at.sidebar.toggle(key="partition").set_value(True).run(timeout=TIMEOUT)
    n_partition = at.slider(key="runde_hand").max
    at.slider(key="runde_hand").set_value(n_partition).run(timeout=TIMEOUT)
    at.sidebar.toggle(key="partition").set_value(False).run(timeout=TIMEOUT)
    assert not at.exception
    assert 1 <= at.slider(key="runde_hand").value <= at.slider(key="runde_hand").max


def test_live_smoothing_compares_with_the_run_without_smoothing():
    at = _fresh_app()
    at.sidebar.select_slider(key="alpha_pct").set_value(90).run(timeout=TIMEOUT)
    assert "Mit α = 0,9:" in _texts(at)


# --- Aufbau ------------------------------------------------------------------------------------------------------------------------------

def test_expanders_are_found_by_their_titles_and_the_first_is_the_how_it_works_one():
    at = _fresh_app()
    titel = {e.label for e in at.expander}
    assert {"💬 In einfachen Worten", "So funktioniert das Pricing in der Spaltenerzeugung", "📐 Mathematische Formulierung", "⚠️ Annahmen, Grenzen und bekannte Probleme"} <= titel
    assert next(e for e in at.expander if e.label == "So funktioniert das Pricing in der Spaltenerzeugung").proto.expanded


def test_five_experiments_and_the_section_of_the_assumptions_exist():
    at = _fresh_app()
    koepfe = [s.value for s in at.subheader]
    assert len([k for k in koepfe if k.startswith("🔬 Experiment")]) == 5
    assert "🚧 Wo die Annahmen enden" in koepfe


def test_no_dead_file_links_in_the_markdown():
    at = _fresh_app()
    for m in at.markdown:
        for ziel in re.findall(r"\]\(([^)]+)\)", m.value):
            assert ziel.startswith("http"), ziel


def test_every_chart_has_its_own_key_and_the_page_has_no_error_box():
    at = _fresh_app()
    assert not at.error and len(at.get("plotly_chart")) >= 8
