"""Kennzahlen, Verdikt-Logik (reine Funktionen: (Art, Text)) und Lader der festen Messreihen.

Jedes Verdikt der App ist eine Funktion `verdict_*(...) -> (Art, Text)`; die App ruft `getattr(st, Art)(Text)`, `tests/test_verdicts.py` prüft Schwellen und jede Zahl
im Text an handgesetzten Werten. Die Analysen (`analyse_*`) rechnen mit dem Kern und geben einfache Daten zurück (für `st.cache_data`)."""

import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import pdp_algorithm as A
import pdp_colgen as G
import pdp_constants as C
from pdp_master import loese_master
from pdp_scenario import Instanz, handbeispiel, einzelfahrt_preise, instanz_aus_seed

DATA = Path(__file__).resolve().parent / "data"
NBSP = " "


# --- Zahlenformat (deutsch) ---------------------------------------------------------------------------------------------------------------

def zahl(x, stellen: int = 0) -> str:
    """Deutsche Schreibweise: Dezimalkomma, geschütztes Leerzeichen als Tausendertrenner; ganze Zahlen ohne Nachkommastellen; „-0“ wird zu „0“."""
    if stellen == 0:
        if isinstance(x, float) and x.is_integer():
            x = int(x)
        text = f"{x:,}"
    else:
        text = f"{round(x, stellen) + 0.0:,.{stellen}f}"
    return text.replace(",", NBSP).replace(".", ",")


def zahl_kurz(x: float) -> str:
    """Eine Zahl ohne überflüssige Nachkommastellen: ganze Werte ohne, sonst bis zu zwei Stellen (Dualpreise, Kosten im Handbeispiel)."""
    if abs(x - round(x)) < 1e-9:
        return zahl(int(round(x)))
    return zahl(x, 2)


def prozent(x: float) -> str:
    return zahl(round(x, 1), 1) + " %"


def weg_text(weg) -> str:
    return "-".join(str(v) for v in weg) if weg else "leer"


def alpha_text(alpha_pct: int) -> str:
    """α als Dezimalzahl mit Komma: 50 wird „0,5“, 0 wird „0“."""
    return "0" if alpha_pct == 0 else zahl(alpha_pct / 100, 1 if alpha_pct % 10 == 0 else 2)


def statistik(werte) -> dict:
    """Mittel, Median, Minimum, Maximum und Zahl der Werte einer Liste."""
    w = list(werte)
    return {"n": len(w), "mittel": statistics.mean(w), "median": statistics.median(w), "min": min(w), "max": max(w)}


def lade_baender(name: str) -> dict:
    """Lädt eine feste Messreihe aus data/ (JSON, jede Zeile mit Quelle)."""
    return json.loads((DATA / f"baender_{name}.json").read_text(encoding="utf-8"))


# --- Einstellungen und Analysen -----------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    n: int = C.DEFAULT_N
    breite: int = C.DEFAULT_BREITE
    seed: int = C.DEFAULT_SEED
    alpha: int = C.DEFAULT_ALPHA       # Glättung in Prozent
    partition: bool = False            # Master: Partitionierung statt Überdeckung

    @property
    def art(self) -> str:
        return "partition" if self.partition else "ueberdeckung"


@dataclass(frozen=True)
class HandAnalyse:
    inst: Instanz
    lauf: G.Lauf                 # Spaltenerzeugung am Handbeispiel, eine neue Spalte je Runde
    wege: tuple                  # alle zulässigen elementaren Wege (Aufzählung)
    gegen_wert: float            # Master über alle diese Wege als Spalten
    negativ_erste: int           # Wege mit negativen reduzierten Kosten unter den Dualpreisen der ersten Runde
    negativ_letzte: int          # ... unter den Dualpreisen der letzten Runde (Zertifikat: keiner)
    fehler: str | None


def pruefe_lauf(inst: Instanz, lauf: G.Lauf, elementar: bool = True) -> str | None:
    """Unabhängige Prüfung eines Laufs: jede angehängte Spalte zulässig und mit richtig bewerteten reduzierten Kosten, Master-Werte fallen nie. None = in Ordnung."""
    letzter = None
    for r in lauf.runden:
        if letzter is not None and r.master_wert > letzter + 1e-6:
            return f"Master-Wert steigt in Runde {r.nr}"
        letzter = r.master_wert
        for spalte in r.neue:
            ok, text = A.pruefe_route(inst, spalte, elementar)
            if not ok:
                return f"Spalte {weg_text(spalte)} in Runde {r.nr}: {text}"
        if r.neue and abs(A.reduzierte_kosten(inst, r.pi, r.neue[0]) - r.beste_rc) > 1e-6:
            return f"Reduzierte Kosten der besten Spalte in Runde {r.nr} stimmen nicht"
    return None


def analyse_hand(partition: bool) -> HandAnalyse:
    inst = handbeispiel()
    lauf = G.spaltenerzeugung(inst, None, "partition" if partition else "ueberdeckung", 0.0, spalten_je_runde=1)
    wege = tuple(A.alle_zulaessigen_wege(inst))
    art = "partition" if partition else "ueberdeckung"
    gegen = loese_master(inst, list(wege), art).wert
    pi1 = einzelfahrt_preise(inst)
    pil = lauf.runden[-1].pi
    neg1 = sum(1 for w in wege if A.reduzierte_kosten(inst, pi1, w) < -1e-7)
    negl = sum(1 for w in wege if A.reduzierte_kosten(inst, pil, w) < -1e-7)
    fehler = pruefe_lauf(inst, lauf)
    if fehler is None and abs(lauf.schranke - gegen) > 1e-6:
        fehler = f"Schranke {lauf.schranke} weicht vom Master über alle Wege ab ({gegen})"
    return HandAnalyse(inst, lauf, wege, gegen, neg1, negl, fehler)


@dataclass(frozen=True)
class BogenAnalyse:
    laengen: tuple               # je Zeile (von 0 bis n) die Längen nach Kunde 1 bis n; None auf der Diagonalen
    zaehlung: A.NegativZaehlung
    dijkstra: A.DijkstraErgebnis
    einfach: tuple               # (Zahl der einfachen Wege, kleinste Länge, ein Weg dieser Länge)
    dijkstra_zulaessig: tuple    # (ok, Text) des Dijkstra-Wegs
    einfach_zulaessig: tuple     # (ok, Text) des besten einfachen Wegs
    fahrplan_dijkstra: tuple


def analyse_bogen(pi: tuple, typ: str) -> BogenAnalyse:
    """Die Bogenlängen des Handbeispiels zu den Dualpreisen `pi` (Typ „minus“ = Entfernung - Dualpreis, „plus“ = Entfernung + Dualpreis), Dijkstra und die Aufzählung aller einfachen Wege."""
    inst = handbeispiel()
    n = inst.n
    laengen = tuple(tuple(None if i == j else A.bogenlaenge(inst, pi, i, j, typ) for j in range(1, n + 1)) for i in range(0, n + 1))
    dij = A.dijkstra(inst, pi, typ)
    einfach = A.beste_einfache_wege(inst, pi, typ)
    return BogenAnalyse(laengen, A.negativ_zaehlung(inst, pi, typ), dij, einfach, A.pruefe_route(inst, dij.weg) if dij.weg else (False, "kein Weg"), A.pruefe_route(inst, einfach[2]),
                        tuple(A.fahrplan(inst, pi, dij.weg)))


@dataclass(frozen=True)
class LabelingAnalyse:
    erzeugt: int
    verworfen: int
    verdraengt: int
    lebend: int
    abgelehnt_last: int
    abgelehnt_fenster: int
    verboten: int
    tabelle: tuple               # je Knoten 1 bis n: ((Nr, Weg, Zeit, Kosten, Last), ...) der lebenden Labels
    dominanz: tuple              # ((Art, Weg des neuen/verdrängten Labels, Weg des Dominierers, Text), ...)
    beste: tuple | None          # (reduzierte Kosten, Weg) der besten Route, None ohne Route
    zahl_wege: int               # Routen, die ins Depot zurückkehren
    zahl_negativ: int            # davon mit negativen reduzierten Kosten
    aufzaehlung_beste: float | None   # kleinste reduzierte Kosten über alle zulässigen elementaren Wege (Aufzählung)
    fahrplan: tuple


def _label_werte(L) -> str:
    return f"Kosten {zahl_kurz(L.kosten)}, Zeit {zahl_kurz(L.zeit)}, Last {zahl_kurz(L.last)}"


def dominanz_grund(a, b, mem_a: str, mem_b: str) -> str:
    """Der Text zur Dominanz: jede der vier Vergleiche mit den Zahlen."""
    return (f"Kosten {zahl_kurz(a.kosten)} ≤ {zahl_kurz(b.kosten)}, Zeit {zahl_kurz(a.zeit)} ≤ {zahl_kurz(b.zeit)}, Last {zahl_kurz(a.last)} ≤ {zahl_kurz(b.last)}, "
            f"Menge {{{mem_a}}} ⊆ {{{mem_b}}}")


def _menge(mem: int) -> str:
    return ", ".join(str(i) for i in range(1, mem.bit_length()) if (mem >> i) & 1)


def analyse_labeling(pi: tuple, max_zeilen: int = 40) -> LabelingAnalyse:
    """Ein Pricing-Aufruf am Handbeispiel (elementar) mit allen Labels: Tabelle der lebenden Labels je Knoten und die Dominanzentscheidungen mit Begründung."""
    inst = handbeispiel()
    erg = A.labeling(inst, pi, None, behalte_labels=True)
    labels = erg.labels
    wege = [A.weg_von(list(labels), i) for i in range(len(labels))]
    tabelle = tuple(
        tuple((i, wege[i], labels[i].zeit, labels[i].kosten, labels[i].last) for i, L in enumerate(labels) if L.knoten == j and not L.tot)
        for j in range(1, inst.n + 1)
    )
    dom = []
    for i, L in enumerate(labels):
        if L.tot:
            o = labels[L.von]          # der Dominierer: bei „verworfen“ ein lebendes Label, bei „verdrängt“ das neue Label, das L verdrängt hat
            dom.append(("verworfen" if L.tot == 1 else "verdrängt", wege[i], wege[L.von], dominanz_grund(o, L, _menge(o.mem), _menge(L.mem)), L.von, i))
    beste = erg.wege[0] if erg.wege else None
    alle = A.alle_zulaessigen_wege(inst)
    aufz = min(A.reduzierte_kosten(inst, pi, w) for w in alle) if alle else None
    return LabelingAnalyse(erg.erzeugt, erg.verworfen, erg.verdraengt, erg.lebend, erg.abgelehnt_last, erg.abgelehnt_fenster, erg.verboten, tabelle, tuple(dom[:max_zeilen]),
                           beste, len(erg.wege), sum(1 for rc, _ in erg.wege if rc < -1e-7), aufz, tuple(A.fahrplan(inst, pi, beste[1])) if beste else ())


@dataclass(frozen=True)
class GrossAnalyse:
    inst: Instanz
    lauf: G.Lauf
    fehler: str | None
    sekunden: float              # nur zur Information, nie festgeschrieben


def analyse_gross(s: Settings) -> GrossAnalyse:
    """Spaltenerzeugung live an einer Kundeninstanz (elementares Pricing, Zufalls-Seed aus den Einstellungen)."""
    inst = instanz_aus_seed(s.n, s.seed, s.breite)
    t0 = time.perf_counter()
    lauf = G.spaltenerzeugung(inst, None, s.art, s.alpha / 100)
    sek = time.perf_counter() - t0
    fehler = None if lauf.abgebrochen else pruefe_lauf(inst, lauf)
    return GrossAnalyse(inst, lauf, fehler, sek)


@dataclass(frozen=True)
class GlaettungHand:
    ohne: G.Lauf
    mit: G.Lauf
    fehler: str | None


def analyse_glaettung_hand(partition: bool, alpha: int) -> GlaettungHand:
    """Das Handbeispiel einmal ohne und einmal mit Glättung α (eine neue Spalte je Runde)."""
    inst = handbeispiel()
    art = "partition" if partition else "ueberdeckung"
    ohne = G.spaltenerzeugung(inst, None, art, 0.0, spalten_je_runde=1)
    mit = ohne if alpha == 0 else G.spaltenerzeugung(inst, None, art, alpha / 100, spalten_je_runde=1)
    fehler = pruefe_lauf(inst, mit)
    if fehler is None and abs(ohne.schranke - mit.schranke) > 1e-6:
        fehler = "Die Schranke ändert sich mit der Glättung"
    return GlaettungHand(ohne, mit, fehler)


# --- Zusammenfassungen der festen Messreihen ---------------------------------------------------------------------------------------------

def zeile_negativ(z: dict) -> dict:
    """Zusammenfassung einer Zeile aus baender_negativ.json: Mittel und Minimum je Zählung."""
    inst = z["instanzen"]
    return {"depot": statistik(i["depot"] for i in inst), "kunde": statistik(i["kunde"] for i in inst), "paare": statistik(i["paare"] for i in inst),
            "n": len(inst), "depot_gesamt": z["depot_gesamt"], "kunde_gesamt": z["kunde_gesamt"], "paare_gesamt": z["paare_gesamt"]}


def zeile_runden(z: dict) -> dict:
    inst = z["instanzen"]
    return {"breite": z["breite"], "n_kunden": z["n"], "runden": statistik(i["runden"] for i in inst), "spalten": statistik(i["spalten"] for i in inst), "labels": statistik(i["labels"] for i in inst), "n": len(inst)}


def zeilen_glaettung(daten: dict, n: int) -> list:
    """Je α eine Zeile mit Runden, Aufrufen, Fehlgriffen und dem Vergleich mit α = 0 (weniger / gleich / mehr Runden in wie vielen Instanzen)."""
    zeilen = [z for z in daten["zeilen"] if z["n"] == n]
    basis = next(z for z in zeilen if z["alpha"] == 0)
    out = []
    for z in zeilen:
        paare = list(zip(z["instanzen"], basis["instanzen"]))
        out.append({
            "alpha": z["alpha"], "n": n, "instanzen": len(z["instanzen"]), "runden": statistik(i["runden"] for i in z["instanzen"]), "aufrufe": statistik(i["aufrufe"] for i in z["instanzen"]),
            "fehlgriffe": statistik(i["fehlgriffe"] for i in z["instanzen"]),
            "weniger": sum(1 for a, b in paare if a["runden"] < b["runden"]), "gleich": sum(1 for a, b in paare if a["runden"] == b["runden"]),
            "mehr": sum(1 for a, b in paare if a["runden"] > b["runden"]),
            "schranke_gleich": all(abs(a["schranke"] - b["schranke"]) < 1e-5 for a, b in paare),
            "quelle": z["quelle"],
        })
    return out


def paare_master(daten: dict) -> list:
    """Alle Paare (Überdeckung, Partitionierung) der Messreihe als Liste von (Typ, k, Seed, Überdeckung, Partitionierung)."""
    return [(z["typ"], z["k"], i["seed"], i["ueberdeckung"], i["partition"]) for z in daten["zeilen"] for i in z["instanzen"]]


# --- Verdikte -----------------------------------------------------------------------------------------------------------------------------

def verdict_dijkstra(b: BogenAnalyse) -> tuple:
    """Trifft Dijkstra den besten einfachen Weg? „Nicht“ nur, wenn mindestens ein Bogen negativ ist und die Aufzählung einen anderen Wert gibt; Zusatz, wenn ein Weg Last oder Fenster verletzt."""
    z = b.zaehlung
    neg = z.depot_negativ + z.kunde_negativ
    dij, einfach = b.dijkstra, b.einfach
    gleich = dij.laenge is not None and abs(dij.laenge - einfach[1]) < 1e-9
    zus = ""
    if not b.dijkstra_zulaessig[0]:
        zus = f" Der Weg von Dijkstra ist außerdem {b.dijkstra_zulaessig[1]}; Dijkstra kennt Last und Fenster nicht."
    if neg == 0:
        return ("success" if gleich else "error"), (f"Alle Bogenlängen sind nicht negativ ({'gleich' if gleich else 'ABWEICHUNG'}): Dijkstra findet Weg {weg_text(dij.weg)} mit Länge {zahl_kurz(dij.laenge)}; "
                                                    f"die Aufzählung aller {zahl(einfach[0])} einfachen Wege gibt Länge {zahl_kurz(einfach[1])} (Weg {weg_text(einfach[2])}).{zus}")
    if not gleich:
        return "warning", (f"Dijkstra trifft den besten Weg nicht: sein Weg {weg_text(dij.weg)} hat die Länge {zahl_kurz(dij.laenge)}, die Aufzählung aller {zahl(einfach[0])} einfachen Wege "
                           f"findet Weg {weg_text(einfach[2])} mit Länge {zahl_kurz(einfach[1])}. {zahl(neg)} Bögen sind negativ, {zahl(dij.verpasst)} Verbesserungen an schon abgeschlossenen "
                           f"Knoten gingen verloren.{zus}")
    return "info", (f"Obwohl {zahl(neg)} Bögen negativ sind, trifft Dijkstra hier den besten einfachen Weg {weg_text(dij.weg)} mit Länge {zahl_kurz(dij.laenge)} "
                    f"({zahl(dij.verpasst)} verpasste Verbesserungen).{zus}")


def verdict_labeling(a: LabelingAnalyse, anzahl_wege: int) -> tuple:
    """Das Labeling liefert den besten zulässigen Weg; er stimmt mit der Aufzählung aller zulässigen elementaren Wege überein."""
    if a.beste is None or a.aufzaehlung_beste is None:
        return "info", f"Kein zulässiger Weg kehrt ins Depot zurück; erzeugt wurden {zahl(a.erzeugt)} Labels."
    gleich = abs(a.beste[0] - a.aufzaehlung_beste) < 1e-9
    kopf = (f"Das Labeling liefert einen besten Weg {weg_text(a.beste[1])} mit reduzierten Kosten {zahl_kurz(a.beste[0])}; die Aufzählung aller {zahl(anzahl_wege)} zulässigen "
            f"elementaren Wege gibt {zahl_kurz(a.aufzaehlung_beste)} ({'gleich' if gleich else 'ABWEICHUNG'}). ")
    rest = (f"Es erzeugte {zahl(a.erzeugt)} Labels, davon {zahl(a.verworfen)} sofort verworfen (neu und dominiert), {zahl(a.verdraengt)} später verdrängt, {zahl(a.lebend)} blieben übrig. "
            f"{zahl(a.zahl_wege)} Routen kehren ins Depot zurück, {zahl(a.zahl_negativ)} davon mit negativen reduzierten Kosten.")
    return ("success" if gleich else "error"), kopf + rest


def verdict_gegenprobe(h: HandAnalyse) -> tuple:
    """Schranke der Spaltenerzeugung gegen den Master über alle zulässigen Wege und das Zertifikat der letzten Dualpreise."""
    neue = len(h.lauf.spalten) - h.inst.n
    gleich = abs(h.lauf.schranke - h.gegen_wert) < 1e-6
    text = (f"Die Spaltenerzeugung endet nach {zahl(h.lauf.anzahl_runden)} Runden mit der Schranke {zahl_kurz(h.lauf.schranke)} und {zahl(neue)} neuen Spalten; ein Master über alle "
            f"{zahl(len(h.wege))} zulässigen elementaren Wege als Spalten gibt {zahl_kurz(h.gegen_wert)} ({'gleich' if gleich else 'ABWEICHUNG'}). Mit den Dualpreisen der letzten Runde haben "
            f"{zahl(h.negativ_letzte)} dieser Wege negative reduzierte Kosten (mit denen der ersten Runde {zahl(h.negativ_erste)}).")
    return ("success" if gleich and h.negativ_letzte == 0 else "error"), text


def verdict_gross(s: Settings, g: GrossAnalyse) -> tuple:
    lauf = g.lauf
    if lauf.abgebrochen:
        return "warning", (f"Abgebrochen nach {zahl(lauf.labels)} erzeugten Labels (Obergrenze {zahl(C.LABEL_CAP)}) in Runde {zahl(lauf.anzahl_runden)}: die Zahlen sind untere Schranken, "
                           "die Schranke ist nicht bis zum Ende erzeugt.")
    erste = lauf.runden[0].master_wert
    neue = len(lauf.spalten) - s.n
    return "info", (f"{zahl(s.n)} Kunden, Fensterbreite {zahl(s.breite)}: die Spaltenerzeugung endet nach {zahl(lauf.anzahl_runden)} Runden mit der Schranke {zahl(lauf.schranke, 2)} "
                    f"(Master-Wert der ersten Runde {zahl(erste, 2)}, also {prozent(100 * (erste - lauf.schranke) / erste)} darunter). Sie hängt {zahl(neue)} neue Spalten an die {zahl(s.n)} Einzelfahrten "
                    f"und erzeugt {zahl(lauf.labels)} Labels in {zahl(lauf.aufrufe)} Pricing-Aufrufen.")


def verdict_glaettung_live(alpha: int, g: GlaettungHand) -> tuple:
    if alpha == 0:
        return "info", f"Ohne Glättung: {zahl(g.ohne.anzahl_runden)} Runden und {zahl(g.ohne.aufrufe)} Pricing-Aufrufe, Schranke {zahl_kurz(g.ohne.schranke)}. Wählen Sie α > 0 in der Seitenleiste."
    return "info", (f"Mit α = {alpha_text(alpha)}: {zahl(g.mit.anzahl_runden)} Runden und {zahl(g.mit.aufrufe)} Pricing-Aufrufe (davon {zahl(g.mit.fehlgriffe)} Fehlgriffe) gegen "
                    f"{zahl(g.ohne.anzahl_runden)} Runden und {zahl(g.ohne.aufrufe)} Aufrufe ohne Glättung; Schranke in beiden {zahl_kurz(g.mit.schranke)}. Eine Instanz, kein Befund.")


def klasse_runden(mittel_a: float, mittel_0: float) -> str:
    """Einordnung der mittleren Rundenzahl gegen α = 0: „etwa gleich viele“ innerhalb von 10 %, sonst „mehr“ oder „weniger“."""
    q = mittel_a / mittel_0
    if q > 1 + C.SCHWELLE_GLEICH:
        return "mehr"
    if q < 1 - C.SCHWELLE_GLEICH:
        return "weniger"
    return "etwa gleich viele"


def verdict_glaettung_band(zeilen: list) -> tuple:
    """Verdikt über eine Reihe (ein n): je α > 0 die Zählung gegen α = 0 und die Einordnung der mittleren Rundenzahl und der Pricing-Aufrufe."""
    basis = next(z for z in zeilen if z["alpha"] == 0)
    n, anz = basis["n"], basis["instanzen"]
    teile = []
    for z in zeilen:
        if z["alpha"] == 0:
            continue
        kl = klasse_runden(z["runden"]["mittel"], basis["runden"]["mittel"])
        auf = "mehr" if z["aufrufe"]["mittel"] > basis["aufrufe"]["mittel"] else "nicht mehr"
        teile.append(f"α = {alpha_text(z['alpha'])}: {kl} Runden (im Mittel {zahl(z['runden']['mittel'], 1)} gegen {zahl(basis['runden']['mittel'], 1)}; weniger / gleich / mehr in "
                     f"{z['weniger']} / {z['gleich']} / {z['mehr']} von {anz} Instanzen), {auf} Pricing-Aufrufe (im Mittel {zahl(z['aufrufe']['mittel'], 1)} gegen {zahl(basis['aufrufe']['mittel'], 1)})")
    gleich = all(z["schranke_gleich"] for z in zeilen)
    return "info", (f"{n} Kunden, {anz} Instanzen, einfache Glättung zur Vorrunde: " + "; ".join(teile) + f". Schranke {'in allen Instanzen und allen α gleich' if gleich else 'NICHT in allen gleich'}.")


def verdict_negativ(zeilen: list) -> tuple:
    """Anteil negativer Bögen in der ersten und in der letzten Runde (Zeilen aus `zeile_negativ`, Schlüssel „erste“ und „letzte“)."""
    e, l = zeilen["erste"], zeilen["letzte"]
    alle_depot = e["depot"]["min"] == e["depot_gesamt"]
    alle_paare = e["paare"]["min"] == e["paare_gesamt"]
    text = (f"Erste Runde ({e['n']} Instanzen, {zahl(e['depot_gesamt'])} Kunden): {'in allen Instanzen alle' if alle_depot else 'im Mittel ' + zahl(e['depot']['mittel'], 1) + ' von'} "
            f"{zahl(e['depot_gesamt'])} Bögen Depot-Kunde negativ, im Mittel {zahl(e['kunde']['mittel'], 1)} von {zahl(e['kunde_gesamt'])} Bögen Kunde-Kunde "
            f"({prozent(100 * e['kunde']['mittel'] / e['kunde_gesamt'])}) und {zahl(e['paare']['mittel'], 1)} von {zahl(e['paare_gesamt'])} Kundenpaaren mit negativem Hin-und-zurück-Kreis"
            f"{' (in allen Instanzen alle)' if alle_paare else ''}. Letzte Runde: im Mittel {zahl(l['depot']['mittel'], 1)} von {zahl(l['depot_gesamt'])}, "
            f"{zahl(l['kunde']['mittel'], 1)} von {zahl(l['kunde_gesamt'])} ({prozent(100 * l['kunde']['mittel'] / l['kunde_gesamt'])}) und {zahl(l['paare']['mittel'], 1)} von {zahl(l['paare_gesamt'])} Paaren.")
    return "info", text


def verdict_master(paare: list) -> tuple:
    """Überdeckung gegen Partitionierung: Zahl der Paare und größte Abweichung der Schranke; Hinweis auf die metrischen Kosten."""
    abw = [abs(u - p) for _, _, _, u, p in paare]
    groesste = max(abw)
    mehr = sum(1 for a in abw if a > 1e-6)
    hinweis = " Gilt für metrische Kosten (Entfernungen); mit Festkosten je Fahrzeug oder Kosten ohne Dreiecksungleichung ist es nicht gemessen."
    if mehr == 0:
        return "success", f"In allen {zahl(len(paare))} Paaren ist die Schranke mit Überdeckung und mit Partitionierung gleich (größte Abweichung {zahl(groesste, 6)}).{hinweis}"
    return "warning", f"In {zahl(mehr)} von {zahl(len(paare))} Paaren weichen die Schranken ab (größte Abweichung {zahl(groesste, 6)}).{hinweis}"


def verdict_runden(zeilen: list) -> tuple:
    """Runden und Spalten über die Fensterbreite (Zeilen aus `zeile_runden` mit Schlüssel „breite“)."""
    med = [z["runden"]["median"] for z in zeilen]
    steigt = all(b > a for a, b in zip(med, med[1:]))
    teile = [f"Breite {zahl(z['breite'])}: Runden im Median {zahl(z['runden']['median'], 1)} (Minimum {zahl(z['runden']['min'])}, Maximum {zahl(z['runden']['max'])}), Spalten im Median {zahl(z['spalten']['median'], 1)}"
             for z in zeilen]
    return "info", (f"{zeilen[0]['n_kunden']} Kunden, {zeilen[0]['runden']['n']} Instanzen je Breite: " + "; ".join(teile)
                    + f". Der Median der Runden {'steigt' if steigt else 'steigt nicht'} von Stufe zu Stufe.")


# --- Texte der Vorführungen ---------------------------------------------------------------------------------------------------------------

def knoten_text(u: int, n: int) -> str:
    """Name eines Knotens im Netz Depot, Kunden, Ende."""
    return "das Depot" if u == 0 else "das Ende" if u == n + 1 else f"Kunde {u}"


def dijkstra_text(schritt: tuple, n: int) -> str:
    """Ein Ereignis von `pdp_algorithm.dijkstra` als Satz."""
    if schritt[0] == "schliesse":
        return f"Dijkstra schließt {knoten_text(schritt[1], n)} ab, Abstand {zahl_kurz(schritt[2])}."
    _, u, v, dd, laenge, dist_v = schritt
    return (f"Bogen {u} → {v}: {zahl_kurz(dd)} + ({zahl_kurz(laenge)}) = {zahl_kurz(dd + laenge)} wäre besser als {zahl_kurz(dist_v)}, aber {knoten_text(v, n)} ist schon abgeschlossen "
            f"(Dijkstra ändert ihn nicht mehr).")


def fahrplan_text(zeile: tuple) -> str:
    """Eine Zeile von `pdp_algorithm.fahrplan` als Satz."""
    j, ank, beginn, last, rest = zeile
    if beginn is None:
        return f"Kunde {j}: Ankunft {zahl_kurz(ank)}, {rest}"
    return f"Kunde {j}: Ankunft {zahl_kurz(ank)}, Beginn {zahl_kurz(beginn)}, Last {zahl_kurz(last)}, reduzierte Kosten bis dahin {zahl_kurz(rest)}"


# --- Tabellenzeilen der Messreihen (App und README zeigen dieselben Zeilen; `tests/test_claims.py` sucht die README-Tabellen) -------------------------

def tabelle_negativ(zn: dict) -> list:
    """Zeilen der Tabelle „negative Bogenlängen“ aus `{"erste": zeile_negativ, "letzte": zeile_negativ}`."""
    return [{
        "Runde": "erste (nur Einzelfahrten im Master)" if name == "erste" else "letzte (Ende der Spaltenerzeugung)",
        "Bögen Depot → Kunde negativ (Mittel)": f"{zahl(z['depot']['mittel'], 1)} von {z['depot_gesamt']}",
        "Bögen Kunde → Kunde negativ (Mittel)": f"{zahl(z['kunde']['mittel'], 1)} von {z['kunde_gesamt']} ({prozent(100 * z['kunde']['mittel'] / z['kunde_gesamt'])})",
        "Kundenpaare mit negativem Kreis (Mittel)": f"{zahl(z['paare']['mittel'], 1)} von {z['paare_gesamt']}"} for name, z in zn.items()]


def tabelle_runden(zr: list) -> list:
    return [{"Fensterbreite": z["breite"], "Runden (Median)": zahl(z["runden"]["median"], 1), "Runden (Minimum)": z["runden"]["min"], "Runden (Maximum)": z["runden"]["max"],
             "Spalten am Ende (Median)": zahl(z["spalten"]["median"], 1), "Labels (Median)": zahl(z["labels"]["median"])} for z in zr]


def tabelle_glaettung(zz: list) -> list:
    return [{"α": alpha_text(z["alpha"]), "Runden (Mittel)": zahl(z["runden"]["mittel"], 1), "Runden (Median)": zahl(z["runden"]["median"], 1), "Runden (Maximum)": z["runden"]["max"],
             "Pricing-Aufrufe (Mittel)": zahl(z["aufrufe"]["mittel"], 1), "Fehlgriffe (Mittel)": zahl(z["fehlgriffe"]["mittel"], 1),
             "weniger / gleich / mehr Runden als α = 0": f"{z['weniger']} / {z['gleich']} / {z['mehr']}"} for z in zz]


def tabelle_master(ma: dict) -> list:
    zeilen = []
    for z in ma["zeilen"]:
        abw = [abs(i["ueberdeckung"] - i["partition"]) for i in z["instanzen"]]
        zeilen.append({"Instanztyp": z["beschreibung"], "Gedächtnis k": z["k"], "Paare": len(abw), "größte Abweichung der Schranke": zahl(max(abw), 6),
                       "Schranke Überdeckung (Mittel)": zahl(sum(i["ueberdeckung"] for i in z["instanzen"]) / len(abw), 2)})
    return zeilen


def markdown_tabelle(zeilen: list) -> str:
    """Markdown-Tabelle aus Zeilen (Liste von Wörterbüchern mit gleichen Schlüsseln)."""
    kopf = list(zeilen[0])
    out = ["| " + " | ".join(kopf) + " |", "|" + "---|" * len(kopf)]
    out += ["| " + " | ".join(str(z[k]) for k in kopf) + " |" for z in zeilen]
    return "\n".join(out)


def lade_fruehere_messreihe() -> dict:
    """Zahlen der früheren Messreihe (data/fruehere_messreihe.json), nur übernommen, nicht neu gerechnet."""
    return json.loads((DATA / "fruehere_messreihe.json").read_text(encoding="utf-8"))


def tabelle_vergleich(fr: dict, zn: dict, zr: list, g20: list, g30: list) -> list:
    """Frühere Messreihe (andere Instanzen, nicht neu gerechnet) neben den neu gerechneten Zahlen dieser Demo."""
    def reihe(werte, stellen=1):
        return " / ".join(zahl(w, stellen) for w in werte)
    return [
        {"Größe": "Negative Bögen Kunde → Kunde, erste Runde (Mittel von 870, 30 Kunden)", "frühere Messreihe": zahl(fr["negativ"]["erste"]["kunde"], 1), "diese Demo": zahl(zn["erste"]["kunde"]["mittel"], 1)},
        {"Größe": "Negative Bögen Kunde → Kunde, letzte Runde (Mittel von 870, 30 Kunden)", "frühere Messreihe": zahl(fr["negativ"]["letzte"]["kunde"], 1), "diese Demo": zahl(zn["letzte"]["kunde"]["mittel"], 1)},
        {"Größe": "Runden, Median, Breite 40 / 100 / 200 (30 Kunden, k = 5)", "frühere Messreihe": reihe(fr["runden"]["runden_median"]), "diese Demo": reihe(z["runden"]["median"] for z in zr)},
        {"Größe": "Spalten am Ende, Median, Breite 40 / 100 / 200", "frühere Messreihe": reihe(fr["runden"]["spalten_median"]), "diese Demo": reihe(z["spalten"]["median"] for z in zr)},
        {"Größe": "Glättung, Runden im Mittel, α = 0 / 0,5 / 0,8 / 0,9 (30 Kunden)", "frühere Messreihe": reihe(fr["glaettung"]["n30"]["runden_mittel"]), "diese Demo": reihe(z["runden"]["mittel"] for z in g30)},
        {"Größe": "Glättung, Pricing-Aufrufe im Mittel, α = 0 / 0,5 / 0,8 / 0,9 (30 Kunden)", "frühere Messreihe": reihe(fr["glaettung"]["n30"]["aufrufe_mittel"]), "diese Demo": reihe(z["aufrufe"]["mittel"] for z in g30)},
        {"Größe": "Glättung, Runden im Mittel, α = 0 / 0,5 / 0,8 / 0,9 (20 Kunden)", "frühere Messreihe": reihe(fr["glaettung"]["n20"]["runden_mittel"]), "diese Demo": reihe(z["runden"]["mittel"] for z in g20)},
        {"Größe": "Glättung, Pricing-Aufrufe im Mittel, α = 0 / 0,5 / 0,8 / 0,9 (20 Kunden)", "frühere Messreihe": reihe(fr["glaettung"]["n20"]["aufrufe_mittel"]), "diese Demo": reihe(z["aufrufe"]["mittel"] for z in g20)},
    ]
