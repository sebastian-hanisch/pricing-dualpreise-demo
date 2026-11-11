"""Erzeugt die festen Messreihen (Bänder) der Demo als JSON unter data/, gerechnet mit demselben Kern wie die App (SplitMix64-Instanzen, HiGHS-Master).

    python tools/messreihen.py negativ     Teil A: negative Bogenlängen in der ersten und in der letzten Runde (n = 30, Breite 100, Zufalls-Seeds 0 bis 5, k = 5)
    python tools/messreihen.py runden      Teil B: Runden, Spalten und Labels einer Spaltenerzeugung (n = 30, Breite 40/100/200, 6 Instanzen, k = 5)
    python tools/messreihen.py glaettung   Teil C und D: Glättung α = 0, 0,5, 0,8, 0,9 (n = 20 mit 12 Instanzen, n = 30 mit 6 Instanzen, Breite 100, k = 5)
    python tools/messreihen.py master      Überdeckung gegen Partitionierung (n = 30, drei Instanztypen mit je 5 Instanzen, k = 1, 5, 8)
    python tools/messreihen.py alle

Gezählt werden Runden, Pricing-Aufrufe und erzeugte Labels, nie Sekunden. Runden und Spalten hängen vom LP-Löser ab (degenerierte Duale); jede Datei nennt die
scipy-Version, mit der sie gerechnet wurde. Jede Zeile nennt ihre Quelle."""

import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scipy  # noqa: E402

import pdp_algorithm as A  # noqa: E402
import pdp_colgen as G  # noqa: E402
import pdp_constants as C  # noqa: E402
import pdp_scenario as S  # noqa: E402

DATA = ROOT / "data"
UMGEBUNG = f"Python {platform.python_version()}, scipy {scipy.__version__}"


def schreibe_json(name: str, daten: dict) -> None:
    """Mit Zeilenende LF auf jeder Plattform."""
    with open(DATA / name, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(daten, ensure_ascii=False, indent=1) + "\n")


def messung_negativ(n: int = C.BAND_N30, breite: int = 100, seeds=range(6), k: int = C.BAND_K) -> dict:
    zeilen = []
    for runde, name in (("erste", "erste Runde: nur Einzelfahrten im Master, Dualpreis = 2 x Entfernung zum Depot"), ("letzte", "letzte Runde der Spaltenerzeugung (Master-Dualpreise, wenn das Pricing nichts mehr findet)")):
        je_inst = []
        for seed in seeds:
            inst = S.instanz_aus_seed(n, seed, breite)
            pi = S.einzelfahrt_preise(inst) if runde == "erste" else G.spaltenerzeugung(inst, k).runden[-1].pi
            z = A.negativ_zaehlung(inst, pi)
            je_inst.append({"seed": seed, "depot": z.depot_negativ, "kunde": z.kunde_negativ, "paare": z.paare_negativ})
        zeilen.append({
            "runde": runde, "beschreibung": name, "n": n, "breite": breite, "k": k, "depot_gesamt": n, "kunde_gesamt": n * (n - 1), "paare_gesamt": n * (n - 1) // 2,
            "instanzen": je_inst,
            "quelle": f"tools/messreihen.py negativ: n = {n}, Breite {breite}, Zufalls-Seeds {seeds[0]} bis {seeds[-1]}, {runde} Runde, Pricing k = {k}, Überdeckungs-Master",
        })
    return {"beschreibung": "Anzahl negativer Bogenlängen d(i, j) − π(j) und negativer Hin-und-zurück-Kreise i, j, i; reine Rechnung an den Dualpreisen, kein Labeling-Ergebnis.", "umgebung": UMGEBUNG, "zeilen": zeilen}


def messung_runden(n: int = C.BAND_N30, k: int = C.BAND_K, seeds=range(6)) -> dict:
    zeilen = []
    for breite in C.BAND_BREITEN:
        je_inst = []
        for seed in seeds:
            lauf = G.spaltenerzeugung(S.instanz_aus_seed(n, seed, breite), k, max_labels=10 ** 9)
            assert not lauf.abgebrochen
            je_inst.append({"seed": seed, "runden": lauf.anzahl_runden, "spalten": len(lauf.spalten), "labels": lauf.labels, "schranke": round(lauf.schranke, 6)})
        zeilen.append({"breite": breite, "n": n, "k": k, "instanzen": je_inst,
                       "quelle": f"tools/messreihen.py runden: n = {n}, Breite {breite}, Zufalls-Seeds {seeds[0]} bis {seeds[-1]}, Pricing k = {k}, Überdeckungs-Master, {C.SPALTEN_JE_RUNDE} neue Spalten je Runde"})
    return {"beschreibung": "Eine ganze Spaltenerzeugung je Instanz bis zur Konvergenz; Spalten einschließlich der n Einzelfahrten vom Start.", "umgebung": UMGEBUNG, "zeilen": zeilen}


def messung_glaettung(konfig=((20, 12), (30, 6)), breite: int = 100, k: int = C.BAND_K) -> dict:
    zeilen = []
    for n, anzahl in konfig:
        for alpha in C.ALPHA_OPTIONEN:
            je_inst = []
            for seed in range(anzahl):
                lauf = G.spaltenerzeugung(S.instanz_aus_seed(n, seed, breite), k, alpha=alpha / 100, max_labels=10 ** 9)
                assert not lauf.abgebrochen
                je_inst.append({"seed": seed, "runden": lauf.anzahl_runden, "aufrufe": lauf.aufrufe, "fehlgriffe": lauf.fehlgriffe, "schranke": round(lauf.schranke, 6)})
            zeilen.append({"n": n, "breite": breite, "k": k, "alpha": alpha, "instanzen": je_inst,
                           "quelle": f"tools/messreihen.py glaettung: n = {n}, Breite {breite}, Zufalls-Seeds 0 bis {anzahl - 1}, Pricing k = {k}, Überdeckungs-Master, α = {alpha} %"})
    return {"beschreibung": "Einfache Glättung zur Vorrunde (nicht Wentges, nicht du Merle); dieselbe Schranke in allen α je Instanz.", "umgebung": UMGEBUNG, "zeilen": zeilen}


MASTER_TYPEN = {
    "zufaellig": dict(typ="zufaellig", H=300, Q=70, breite=100, name="zufällig verteilt, Horizont 300, Kapazität 70, Breite 100"),
    "gruppiert": dict(typ="gruppiert", H=300, Q=70, breite=100, name="gruppiert um fünf Zentren, Horizont 300, Kapazität 70, Breite 100"),
    "lang": dict(typ="zufaellig", H=500, Q=120, breite=100, name="zufällig verteilt, Horizont 500, Kapazität 120, Breite 100"),
}


def messung_master(n: int = C.BAND_N30, seeds=range(5), ks=(1, 5, 8)) -> dict:
    zeilen = []
    for name, p in MASTER_TYPEN.items():
        for k in ks:
            je_inst = []
            for seed in seeds:
                inst = S.instanz_aus_seed(n, seed, p["breite"], p["typ"], p["H"], p["Q"])
                ue = G.spaltenerzeugung(inst, k, "ueberdeckung", max_labels=10 ** 9)
                pa = G.spaltenerzeugung(inst, k, "partition", max_labels=10 ** 9)
                assert not ue.abgebrochen and not pa.abgebrochen
                je_inst.append({"seed": seed, "ueberdeckung": round(ue.schranke, 6), "partition": round(pa.schranke, 6)})
            zeilen.append({"typ": name, "beschreibung": p["name"], "n": n, "k": k, "instanzen": je_inst,
                           "quelle": f"tools/messreihen.py master: n = {n}, Typ {name} ({p['name']}), Zufalls-Seeds {seeds[0]} bis {seeds[-1]}, Pricing k = {k}"})
    return {"beschreibung": "Schranke der Spaltenerzeugung mit Überdeckungs- und mit Partitionierungs-Master, je Instanz beide.", "umgebung": UMGEBUNG, "zeilen": zeilen}


AUFGABEN = {
    "negativ": ("baender_negativ.json", messung_negativ),
    "runden": ("baender_runden.json", messung_runden),
    "glaettung": ("baender_glaettung.json", messung_glaettung),
    "master": ("baender_master.json", messung_master),
}

if __name__ == "__main__":
    wahl = sys.argv[1] if len(sys.argv) > 1 else "alle"
    for name, (datei, fn) in AUFGABEN.items():
        if wahl in (name, "alle"):
            schreibe_json(datei, fn())
            print("geschrieben:", datei, flush=True)
