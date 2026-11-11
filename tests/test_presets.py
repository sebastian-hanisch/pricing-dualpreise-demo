"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen; Permalink-Regeln (Begrenzen, Einrasten, Wahrheitswerte)."""

import pytest

import pdp_constants as C
import pdp_evaluation as ev
import pdp_presets as P


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_inside_the_slider_bounds():
    for preset in C.PRESETS.values():
        assert C.N_MIN <= preset["n"] <= C.N_MAX and 0 <= preset["seed"] <= C.SEED_MAX
        assert C.BREITE_MIN <= preset["breite"] <= C.BREITE_MAX and (preset["breite"] - C.BREITE_MIN) % C.BREITE_STEP == 0
        assert preset["alpha"] in C.ALPHA_OPTIONEN and isinstance(preset["partition"], bool)


def test_default_preset_equals_the_default_settings():
    assert ev.Settings(**{k: v for k, v in C.PRESETS["Standard: Handbeispiel und 12 Kunden"].items()}) == ev.Settings()


def test_setting_specs_cover_every_preset_key():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)


def test_the_presets_differ_from_each_other_in_at_least_one_setting():
    werte = [tuple(sorted(p.items())) for p in C.PRESETS.values()]
    assert len(set(werte)) == len(werte)


def test_the_live_computation_stays_inside_its_documented_size():
    assert C.N_MAX == 20 and C.N_MIN >= 2


@pytest.mark.parametrize("text, erwartet", [("1", True), ("true", True), ("True", True), (" TRUE ", True), ("0", False), ("false", False), ("", False), ("ja", False)])
def test_boolean_values_of_the_address_line(text, erwartet):
    assert P.als_bool(text) is erwartet


def test_alpha_options_are_a_zero_and_increasing_percentages():
    assert C.ALPHA_OPTIONEN[0] == 0 and list(C.ALPHA_OPTIONEN) == sorted(set(C.ALPHA_OPTIONEN)) and max(C.ALPHA_OPTIONEN) < 100
