"""Druckt die Markdown-Tabellen der README aus den festen Messreihen (data/*.json); `tests/test_claims.py` prüft, dass genau diese Tabellen in der README stehen.

    python tools/readme_tabellen.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pdp_evaluation as ev  # noqa: E402


def alle() -> dict:
    neg = ev.lade_baender("negativ")
    zn = {z["runde"]: ev.zeile_negativ(z) for z in neg["zeilen"]}
    zr = [ev.zeile_runden(z) for z in ev.lade_baender("runden")["zeilen"]]
    gl = ev.lade_baender("glaettung")
    g20, g30 = ev.zeilen_glaettung(gl, 20), ev.zeilen_glaettung(gl, 30)
    return {
        "negativ": ev.markdown_tabelle(ev.tabelle_negativ(zn)),
        "runden": ev.markdown_tabelle(ev.tabelle_runden(zr)),
        "glaettung20": ev.markdown_tabelle(ev.tabelle_glaettung(g20)),
        "glaettung30": ev.markdown_tabelle(ev.tabelle_glaettung(g30)),
        "master": ev.markdown_tabelle(ev.tabelle_master(ev.lade_baender("master"))),
        "vergleich": ev.markdown_tabelle(ev.tabelle_vergleich(ev.lade_fruehere_messreihe(), zn, zr, g20, g30)),
    }


if __name__ == "__main__":
    for name, text in alle().items():
        print(f"### {name}\n{text}\n")
