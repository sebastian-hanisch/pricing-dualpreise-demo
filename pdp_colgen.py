"""Die Spaltenerzeugung: Schleife über Master (`pdp_master.loese_master`) und Pricing (`pdp_algorithm.labeling`), mit optionaler einfacher Glättung der Dualpreise.

Start: die Einzelfahrten 0-j-0 als Spalten. Je Runde: Master lösen (Dualpreise), Pricing mit den Preisen, die besten neuen Spalten anhängen; Ende, wenn keine Route mit negativen
reduzierten Kosten mehr gefunden wird. Die Schranke ist der letzte Master-Wert (bei elementarem Pricing der Wert des LP über alle zulässigen Routen).

**Glättung** (einfach, Zentrum = der Preisvektor der Vorrunde, nicht das beste bisherige Dual wie bei Wentges und nicht Strafen im Dualraum wie bei du Merle u. a.):
Das Pricing bekommt `a * Vorrunde + (1 - a) * Dual`. Findet es damit keine Spalte, die unter den echten Dualpreisen negative reduzierte Kosten hat (ein **Fehlgriff**),
wird sofort mit den echten Dualpreisen gerechnet (a = 0). Die Schranke ändert die Glättung nie, nur die Zahl der Runden und der Pricing-Aufrufe."""

from dataclasses import dataclass

import pdp_constants as C
from pdp_algorithm import PricingErgebnis, labeling, neue_spalten, pruefe_route, route_kosten
from pdp_master import loese_master
from pdp_scenario import Instanz


@dataclass(frozen=True)
class Runde:
    nr: int
    master_wert: float
    pi: tuple                  # echte Dualpreise dieser Runde
    pi_pricing: tuple          # Preise, mit denen das letzte Pricing der Runde gerechnet hat (bei Glättung verschieden von pi)
    neue: tuple                # angehängte Spalten (Kundenfolgen), die beste zuerst
    beste_rc: float | None     # echte reduzierte Kosten der besten neuen Spalte, None ohne neue Spalte
    labels: int                # in dieser Runde erzeugte Labels (alle Pricing-Aufrufe der Runde)
    aufrufe: int               # Pricing-Aufrufe dieser Runde (mehr als 1 nach einem Fehlgriff)
    fehlgriffe: int
    x: tuple                   # Spalten mit Menge > 0: ((Kundenfolge, Menge), ...)


@dataclass(frozen=True)
class Lauf:
    runden: tuple
    spalten: tuple            # alle Spalten am Ende (Einzelfahrten zuerst)
    schranke: float
    labels: int               # Summe der erzeugten Labels aller Pricing-Aufrufe
    aufrufe: int
    fehlgriffe: int
    abgebrochen: bool         # Abbruch (Label-Obergrenze oder Rundengrenze): die Schranke ist dann nicht bis zum Ende erzeugt

    @property
    def anzahl_runden(self) -> int:
        return len(self.runden)


def einzelfahrten(inst: Instanz) -> list:
    """Startspalten: für jeden Kunden die Fahrt Depot, Kunde, Depot (sie muss zulässig sein: Last, Fenster und Horizont, sonst bricht `spaltenerzeugung` mit ValueError ab)."""
    return [(j,) for j in range(1, inst.n + 1)]


def spaltenerzeugung(inst: Instanz, k: int | None = None, art: str = "ueberdeckung", alpha: float = 0.0, spalten_je_runde: int = C.SPALTEN_JE_RUNDE,
                     max_labels: int = C.LABEL_CAP, max_runden: int = C.MAX_RUNDEN, start=None) -> Lauf:
    """Spaltenerzeugung bis zum Ende. `k`: Gedächtnis des Pricings (None = elementar). `alpha`: Glättung (0 = aus). `spalten_je_runde`: wie viele neue Spalten je Runde angehängt werden."""
    spalten = list(einzelfahrten(inst) if start is None else start)
    if start is None:
        for (j,) in spalten:
            ok, text = pruefe_route(inst, (j,))
            if not ok:
                raise ValueError(f"Die Einzelfahrt zu Kunde {j} ist nicht zulässig ({text}): der Start der Spaltenerzeugung setzt voraus, dass jeder Kunde allein bedient werden kann")
    bekannt = set(spalten)
    runden = []
    zentrum = None
    labels_ges = aufrufe_ges = fehl_ges = 0
    abgebrochen = False
    master = None
    for nr in range(1, max_runden + 1):
        master = loese_master(inst, spalten, art)
        pi = master.pi
        a = alpha if zentrum is not None else 0.0
        aufrufe = fehlgriffe = labels = 0
        while True:
            cur = pi if zentrum is None else tuple(a * s + (1 - a) * p for s, p in zip(zentrum, pi))
            erg: PricingErgebnis = labeling(inst, cur, k, max_labels=max(1, max_labels - labels_ges - labels))
            aufrufe += 1
            labels += erg.erzeugt
            if erg.abgebrochen:
                abgebrochen = True
                frisch = []
                break
            frisch = neue_spalten(erg.wege, pi, inst, bekannt, spalten_je_runde)
            if frisch or a == 0.0:
                break
            fehlgriffe += 1
            a = 0.0
        zentrum = cur
        labels_ges += labels
        aufrufe_ges += aufrufe
        fehl_ges += fehlgriffe
        x = tuple((r, m) for r, m in zip(spalten, master.x) if m > 1e-9)
        runden.append(Runde(nr, master.wert, pi, cur, tuple(r for _, r in frisch), frisch[0][0] if frisch else None, labels, aufrufe, fehlgriffe, x))
        if abgebrochen or not frisch:
            break
        for _, r in frisch:
            spalten.append(r)
            bekannt.add(r)
    else:
        abgebrochen = True
    return Lauf(tuple(runden), tuple(spalten), master.wert, labels_ges, aufrufe_ges, fehl_ges, abgebrochen)


def kosten_der_spalten(inst: Instanz, spalten) -> list:
    """Kosten (Entfernungen) jeder Spalte, in der Reihenfolge der Spalten."""
    return [route_kosten(inst, r) for r in spalten]
