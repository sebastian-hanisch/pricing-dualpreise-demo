"""Kern der Demo (Standardbibliothek): Labeling mit Dualpreisen, Dijkstra-Vorführung und die Aufzählungen für die Gegenproben.

Das **Pricing** der Spaltenerzeugung sucht einen Weg Depot, Kunden, Depot mit den kleinsten **reduzierten Kosten**: Entfernungen minus die Dualpreise der besuchten
Kunden. Ein **Label** steht für einen Teilweg bis zu einem Kunden: Zeit (Beginn der Bedienung), reduzierte Kosten, Last und ein Gedächtnis (welche Kunden der
Weg nicht noch einmal besuchen darf). Ein Label **dominiert** ein anderes am selben Kunden, wenn es in allen Größen höchstens so groß ist (beim Gedächtnis: eine
Teilmenge) und deshalb auf jeder Fortsetzung nie schlechter ist.

Aufbau nach DEMO-PLAYBOOK §1b: jede Regel ist eine Funktion mit expliziten Ein- und Ausgaben, es gibt keinen versteckten Zustand; `labeling` ruft die Regeln
nur der Reihe nach auf. Die Spaltenerzeugung (Schleife über Master und Pricing) steht in `pdp_colgen.py`, der Master in `pdp_master.py`.

Gezählt werden erzeugte Labels (die Messgröße, hardwareunabhängig), nie Sekunden."""

import heapq
from dataclasses import dataclass
from functools import lru_cache

import pdp_constants as C
from pdp_scenario import Instanz

EPS = 1e-9


# --- Einheiten des Labelings ---------------------------------------------------------------------------------------------------------------

class Label:
    """Teilweg bis zum Kunden `knoten`: Zeit (Beginn der Bedienung), reduzierte Kosten, Last, Gedächtnis (Bitmaske), Vorgänger-Label und Marke, ob es verworfen oder verdrängt wurde.

    `tot` ist 0 (lebt), 1 (sofort verworfen: neu und von einem lebenden Label dominiert) oder 2 (später verdrängt: von einem neuen Label dominiert); `von` nennt dann die Nummer des Dominierers."""

    __slots__ = ("knoten", "zeit", "kosten", "last", "mem", "eltern", "tot", "von")

    def __init__(self, knoten, zeit, kosten, last, mem, eltern):
        self.knoten, self.zeit, self.kosten, self.last, self.mem, self.eltern = knoten, zeit, kosten, last, mem, eltern
        self.tot = 0
        self.von = -1


def dominiert(a: Label, b: Label, mit_gedaechtnis: bool = True) -> bool:
    """a dominiert b (am selben Kunden): Kosten, Zeit und Last von a sind höchstens so groß wie die von b, und das Gedächtnis von a ist eine Teilmenge des Gedächtnisses von b.

    Gleiche Werte dominieren sich gegenseitig: das früher eingefügte Label bleibt. Ohne den Gedächtnis-Vergleich (`mit_gedaechtnis=False`, nur für Tests) ist die Regel falsch,
    sobald das Gedächtnis den Weg weiter einschränkt."""
    if not (a.kosten <= b.kosten + EPS and a.zeit <= b.zeit + EPS and a.last <= b.last):
        return False
    return (not mit_gedaechtnis) or (a.mem & ~b.mem) == 0


def verlaengerung(inst: Instanz, i: int, zeit: float, last: float, j: int):
    """Fahrt von Knoten i (Bedienung beginnt zur Zeit `zeit`, Last `last`) zu Kunde j: Rückgabe (neue Zeit, neue Last), oder None, wenn Last oder Fenster verletzt sind.

    Die Last darf die Kapazität nicht übersteigen; die Ankunft darf nicht nach dem Fensterende liegen, bei früherer Ankunft wartet das Fahrzeug bis zum Fensterbeginn.
    Von einem Kunden aus kommt die Bedienzeit dazu (am Depot gibt es keine)."""
    last2 = last + inst.dem[j]
    if last2 > inst.Q:
        return None
    ank = zeit + (inst.svc if i != 0 else 0) + inst.d[i][j]
    if ank > inst.due[j] + EPS:
        return None
    return (ank if ank > inst.ready[j] else inst.ready[j]), last2


def ablehngrund(inst: Instanz, i: int, zeit: float, last: float, j: int) -> str:
    """Der Text zur Ablehnung einer Verlängerung (für die Protokolle); leer, wenn sie zulässig ist."""
    last2 = last + inst.dem[j]
    if last2 > inst.Q:
        return f"Last {zahl_text(last2)} > {zahl_text(inst.Q)}"
    ank = zeit + (inst.svc if i != 0 else 0) + inst.d[i][j]
    if ank > inst.due[j] + EPS:
        return f"Ankunft {zahl_text(ank)} > Fensterende {zahl_text(inst.due[j])}"
    return ""


def zahl_text(x) -> str:
    """Zahl für Protokolltexte: ganze Werte ohne Nachkommastelle, sonst zwei Stellen mit Dezimalkomma."""
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.2f}".replace(".", ",")


def rueckkehr_moeglich(inst: Instanz, i: int, zeit: float) -> bool:
    """Kann das Fahrzeug nach der Bedienung bei Kunde i (Beginn zur Zeit `zeit`) bis zum Horizont H ins Depot zurück?"""
    return zeit + inst.svc + inst.d[i][0] <= inst.H + EPS


@lru_cache(maxsize=256)
def ng_masken(inst: Instanz, k: int) -> tuple:
    """Gedächtnis-Maske je Kunde j: die k nächsten Kunden einschließlich j selbst (Bitmaske, Bit i = Kunde i). Bei k = n ist jede Wiederholung verboten (elementar)."""
    masken = [0] * (inst.n + 1)
    for j in range(1, inst.n + 1):
        nah = sorted(range(1, inst.n + 1), key=lambda i: (inst.d[j][i], i))[:k]
        m = 1 << j
        for i in nah:
            m |= 1 << i
        masken[j] = m
    return tuple(masken)


def einfuegen(labels: list, lebend: list, neu: int, mit_gedaechtnis: bool = True):
    """Dominanzprüfung für das neue Label `labels[neu]` gegen die lebenden Labels (Indizes) seines Kunden.

    Rückgabe (Dominierer, Verdrängte): Wird das neue Label von einem lebenden dominiert, ist der erste Index der Dominierer und es gibt keine Verdrängten. Sonst ist der
    Dominierer None, und Verdrängte sind die lebenden Labels, die das neue dominiert. Es wird nichts verändert; der Aufrufer markiert und bereinigt."""
    n = labels[neu]
    for o in lebend:
        if dominiert(labels[o], n, mit_gedaechtnis):
            return o, []
    return None, [o for o in lebend if dominiert(n, labels[o], mit_gedaechtnis)]


def weg_von(labels: list, idx: int) -> tuple:
    """Kundenfolge vom Depot bis zum Label `idx` (ohne das Depot), über die Vorgänger-Verweise."""
    weg = []
    x = idx
    while x != -1:
        weg.append(labels[x].knoten)
        x = labels[x].eltern
    return tuple(reversed(weg))[1:]


def route_kosten(inst: Instanz, route) -> float:
    """Kosten der Fahrt Depot, route, Depot: die Summe der Entfernungen."""
    folge = (0,) + tuple(route) + (0,)
    return sum(inst.d[a][b] for a, b in zip(folge, folge[1:]))


def reduzierte_kosten(inst: Instanz, pi, route) -> float:
    """Reduzierte Kosten einer Route: Entfernungen minus die Dualpreise der besuchten Kunden (ein doppelt besuchter Kunde zählt doppelt)."""
    return route_kosten(inst, route) - sum(pi[j] for j in route)


# --- Das Labeling --------------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class PricingErgebnis:
    erzeugt: int                 # erzeugte Labels, mit dem Start-Label und den sofort verworfenen
    verworfen: int               # neu erzeugt und sofort von einem lebenden Label dominiert
    verdraengt: int              # später von einem neuen Label dominiert
    abgelehnt_last: int          # Verlängerungen, die an der Last scheitern
    abgelehnt_fenster: int       # Verlängerungen, die am Fensterende scheitern
    verboten: int                # Verlängerungen, die das Gedächtnis verbietet
    wege: tuple                  # alle Routen, die ins Depot zurückkehren: (reduzierte Kosten, Kundenfolge), aufsteigend
    abgebrochen: bool            # Abbruch bei Überschreiten von max_labels: die Zahlen sind dann untere Schranken, die Wege unvollständig
    labels: tuple = ()           # alle Labels (nur mit behalte_labels), Nummer = Position

    @property
    def dominiert(self) -> int:
        return self.verworfen + self.verdraengt

    @property
    def lebend(self) -> int:
        """Labels, die am Ende nicht dominiert sind (einschließlich des Start-Labels)."""
        return self.erzeugt - self.verworfen - self.verdraengt


def labeling(inst: Instanz, pi, k: int | None = None, max_labels: int = C.LABEL_CAP, dominanz: bool = True, mit_gedaechtnis: bool = True,
             behalte_labels: bool = False) -> PricingErgebnis:
    """Alle nicht dominierten Routen Depot, Kunden, Depot unter Last-, Fenster- und Horizontgrenze, bewertet mit den Dualpreisen `pi` (pi[0] = 0).

    Label-Setting nach Zeit: das offene Label mit der kleinsten Zeit wird über jeden Kunden verlängert (`verlaengerung`), das Gedächtnis (`ng_masken`) verbietet
    Wiederholungen: k = None ist elementar (jeder Kunde höchstens einmal), kleineres k erlaubt Kreise. Dominanz: `einfuegen`. Es zählen die erzeugten Labels.
    `dominanz=False` und `mit_gedaechtnis=False` schalten die Regel ab (nur für Tests und die Vorführung)."""
    n, d, svc = inst.n, inst.d, inst.svc
    ng = ng_masken(inst, n if k is None else k)
    labels = [Label(0, 0, 0.0, 0, 0, -1)]
    am_knoten = [[] for _ in range(n + 1)]
    heap = [(0, 0)]
    erzeugt, verworfen, verdraengt = 1, 0, 0
    a_last = a_fenster = verboten = 0
    ende: list = []
    abgebrochen = False
    while heap:
        _, li = heapq.heappop(heap)
        L = labels[li]
        if L.tot:
            continue
        if erzeugt > max_labels:
            abgebrochen = True
            break
        i = L.knoten
        if i != 0 and rueckkehr_moeglich(inst, i, L.zeit):
            ende.append((L.kosten + d[i][0], li))
        for j in range(1, n + 1):
            if j == i:
                continue
            if (L.mem >> j) & 1:
                verboten += 1
                continue
            neu = verlaengerung(inst, i, L.zeit, L.last, j)
            if neu is None:
                if L.last + inst.dem[j] > inst.Q:
                    a_last += 1
                else:
                    a_fenster += 1
                continue
            labels.append(Label(j, neu[0], L.kosten + d[i][j] - pi[j], neu[1], (L.mem & ng[j]) | (1 << j), li))
            nid = len(labels) - 1
            erzeugt += 1
            if dominanz:
                dominierer, verdraengte = einfuegen(labels, am_knoten[j], nid, mit_gedaechtnis)
                if dominierer is not None:
                    labels[nid].tot, labels[nid].von = 1, dominierer
                    verworfen += 1
                    continue
                for o in verdraengte:
                    labels[o].tot, labels[o].von = 2, nid
                    verdraengt += 1
                if verdraengte:
                    am_knoten[j] = [o for o in am_knoten[j] if not labels[o].tot]
            am_knoten[j].append(nid)
            heapq.heappush(heap, (neu[0], nid))
    gefunden: dict = {}
    for rc, li in ende:
        gefunden.setdefault(weg_von(labels, li), rc)
    wege = tuple(sorted((rc, r) for r, rc in gefunden.items()))
    return PricingErgebnis(erzeugt, verworfen, verdraengt, a_last, a_fenster, verboten, wege, abgebrochen, tuple(labels) if behalte_labels else ())


def neue_spalten(wege, pi, inst: Instanz, bekannt, anzahl: int) -> list:
    """Die neuen Spalten aus den Routen des Pricings. `wege` ist nach den reduzierten Kosten unter den Preisen des Pricings sortiert (`PricingErgebnis.wege`).

    Das Pricing liefert seine `anzahl` besten Routen mit negativen reduzierten Kosten unter seinen Preisen; davon werden die genommen, die auch unter den echten Dualpreisen
    `pi` negative reduzierte Kosten haben und noch nicht im Master stehen (`bekannt`). Ohne Glättung sind beide Preise gleich. Rückgabe: Liste (echte reduzierte Kosten, Route)."""
    kandidaten = []
    for rc, r in wege:
        if rc >= -1e-7 or len(kandidaten) >= anzahl:
            break
        kandidaten.append(r)
    frisch = []
    for r in kandidaten:
        if r in bekannt:
            continue
        echt = reduzierte_kosten(inst, pi, r)
        if echt < -1e-7:
            frisch.append((echt, r))
    return frisch


# --- Prüfer und Fahrplan -------------------------------------------------------------------------------------------------------------------

def pruefe_route(inst: Instanz, route, elementar: bool = True):
    """Unabhängiger Prüfer: fährt die Route ab und prüft Last, Fenster und Rückkehr. Rückgabe (zulässig, Text); der Text nennt bei Verletzung die erste verletzte Regel."""
    route = tuple(route)
    if not route:
        return False, "leere Route"
    if any(not (1 <= j <= inst.n) for j in route):
        return False, "Kunde außerhalb von 1 bis n"
    if elementar and len(set(route)) != len(route):
        return False, "ein Kunde kommt mehrfach vor"
    zeit, last, i = 0, 0, 0
    for j in route:
        neu = verlaengerung(inst, i, zeit, last, j)
        if neu is None:
            return False, f"unzulässig bei Kunde {j}: {ablehngrund(inst, i, zeit, last, j)}"
        zeit, last = neu
        i = j
    if not rueckkehr_moeglich(inst, i, zeit):
        return False, f"unzulässig: Rückkehr {zahl_text(zeit)} + {zahl_text(inst.svc)} + {zahl_text(inst.d[i][0])} > {zahl_text(inst.H)}"
    return True, "zulässig (Last, Fenster, Rückkehr)"


def fahrplan(inst: Instanz, pi, route) -> list:
    """Fahrplan einer Route: je Halt (Kunde, Ankunft, Beginn der Bedienung, Last, reduzierte Kosten bis dahin). Bricht bei einer Verletzung mit dem Grund ab (Halt mit Beginn None)."""
    zeit, last, i, kosten = 0, 0, 0, 0.0
    zeilen = []
    for j in route:
        ank = zeit + (inst.svc if i != 0 else 0) + inst.d[i][j]
        neu = verlaengerung(inst, i, zeit, last, j)
        if neu is None:
            zeilen.append((j, ank, None, last + inst.dem[j], ablehngrund(inst, i, zeit, last, j)))
            break
        zeit, last = neu
        kosten += inst.d[i][j] - pi[j]
        zeilen.append((j, ank, zeit, last, kosten))
        i = j
    return zeilen


# --- Aufzählung aller zulässigen elementaren Wege (Gegenprobe, kleine Instanzen) ---------------------------------------------------------------

def alle_zulaessigen_wege(inst: Instanz) -> list:
    """Alle zulässigen elementaren Routen (Last, Fenster, Rückkehr) durch Tiefensuche, als Kundenfolgen in der Reihenfolge der Suche. Nur für kleine n (7 Kunden: 79 Wege)."""
    wege = []

    def rec(weg, i, zeit, last, besucht):
        if weg and rueckkehr_moeglich(inst, i, zeit):
            wege.append(tuple(weg))
        for j in range(1, inst.n + 1):
            if (besucht >> j) & 1:
                continue
            neu = verlaengerung(inst, i, zeit, last, j)
            if neu is None:
                continue
            weg.append(j)
            rec(weg, j, neu[0], neu[1], besucht | (1 << j))
            weg.pop()

    rec([], 0, 0, 0, 0)
    return wege


# --- Dijkstra und die Aufzählung einfacher Wege (ohne Grenzen) -----------------------------------------------------------------------------

def bogenlaenge(inst: Instanz, pi, u: int, v: int, typ: str) -> float:
    """Länge des Bogens u nach v im Netz Depot, Kunden, Ende: Bögen ins Ende (Knoten n + 1) haben die Länge d(u, 0).

    Typ „minus“ (die Längen des Pricings): Entfernung minus Dualpreis des Zielkunden, kann negativ sein. Typ „plus“: Entfernung plus Preis (nie negativ, wie bei Preisen im Netzwerkfluss)."""
    if v == inst.n + 1:
        return inst.d[u][0]
    return inst.d[u][v] - pi[v] if typ == "minus" else inst.d[u][v] + pi[v]


@dataclass(frozen=True)
class DijkstraErgebnis:
    schritte: tuple         # Ereignisse: ("schliesse", Knoten, Abstand) und ("verpasst", von, nach, Abstand von, Länge, Abstand nach)
    weg: tuple              # Kundenfolge des Dijkstra-Wegs (leer, wenn das Ende nicht erreicht wird)
    laenge: float | None    # Länge des Dijkstra-Wegs bis zum Ende
    verpasst: int           # Verbesserungen an schon abgeschlossenen Knoten, die Dijkstra nicht mehr übernimmt


def dijkstra(inst: Instanz, pi, typ: str, kleinere_nummer_zuerst: bool = True) -> DijkstraErgebnis:
    """Dijkstra in der Lehrbuchform (jeder Knoten wird einmal abgeschlossen, danach nie mehr geändert) auf dem Netz Depot, Kunden, Ende, ohne Last und Fenster.

    Gleichstandsregel: Bei gleichem Abstand wird der Knoten mit der kleineren Nummer zuerst abgeschlossen (`kleinere_nummer_zuerst=False`: der mit der größeren; im Handbeispiel
    ändert das die Zahlen, weil Kunde 3 und Kunde 7 beide den Abstand -5 haben). Kein Bogen vom Depot ins Ende. Bei negativen Längen („minus“) trifft die Annahme nicht zu: Eine spätere Verbesserung eines abgeschlossenen Knotens wird gezählt (`verpasst`) und nicht übernommen."""
    n = inst.n
    ende = n + 1
    dist = {0: 0.0}
    vorher = {}
    fertig = set()
    schritte = []
    verpasst = 0
    heap = [(0.0, 0, 0)]
    while heap:
        dd, _, u = heapq.heappop(heap)
        if u in fertig:
            continue
        fertig.add(u)
        schritte.append(("schliesse", u, dd))
        if u == ende:
            continue
        nachbarn = [j for j in range(1, n + 1) if j != u] + ([ende] if u != 0 else [])
        for v in nachbarn:
            laenge = bogenlaenge(inst, pi, u, v, typ)
            if v in fertig:
                if v != ende and v in dist and dd + laenge < dist[v] - EPS:
                    verpasst += 1
                    schritte.append(("verpasst", u, v, dd, laenge, dist[v]))
                continue
            nd = dd + laenge
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                vorher[v] = u
                heapq.heappush(heap, (nd, v if kleinere_nummer_zuerst else -v, v))
    weg = []
    x = ende
    while x in vorher:
        x = vorher[x]
        weg.append(x)
    weg = tuple(reversed(weg))[1:]
    return DijkstraErgebnis(tuple(schritte), weg, dist.get(ende), verpasst)


def weg_laenge(inst: Instanz, pi, weg, typ: str) -> float:
    """Länge einer Kundenfolge im Netz Depot, Kunden, Ende: Summe der Bogenlängen (Depot zum ersten Kunden, ..., letzter Kunde ins Ende)."""
    folge = (0,) + tuple(weg) + (inst.n + 1,)
    return sum(bogenlaenge(inst, pi, a, b, typ) for a, b in zip(folge, folge[1:]))


def beste_einfache_wege(inst: Instanz, pi, typ: str):
    """Aufzählung aller einfachen Wege Depot, Kunden (jeder höchstens einmal, mindestens einer), Ende ohne Last- und Fenstergrenzen: (Zahl der Wege, kleinste Länge, ein Weg dieser Länge).

    Gleichstand: lexikografisch kleinste Kundenfolge. Für 7 Kunden sind es 13 699 Wege; nur für kleine n."""
    anzahl = 0
    bestes = [None, None]

    def rec(weg, i, laenge, besucht):
        nonlocal anzahl
        if weg:
            anzahl += 1
            gesamt = laenge + bogenlaenge(inst, pi, i, inst.n + 1, typ)
            if bestes[0] is None or gesamt < bestes[0] - EPS:
                bestes[0], bestes[1] = gesamt, tuple(weg)
        for j in range(1, inst.n + 1):
            if (besucht >> j) & 1:
                continue
            weg.append(j)
            rec(weg, j, laenge + bogenlaenge(inst, pi, i, j, typ), besucht | (1 << j))
            weg.pop()

    rec([], 0, 0.0, 0)
    return anzahl, bestes[0], bestes[1]


@dataclass(frozen=True)
class NegativZaehlung:
    depot_negativ: int      # Bögen Depot nach Kunde mit negativer Länge d - pi
    depot_gesamt: int
    kunde_negativ: int      # Bögen Kunde nach Kunde mit negativer Länge
    kunde_gesamt: int
    paare_negativ: int      # Kundenpaare {i, j}, deren Hin-und-zurück-Kreis i, j, i negative Länge 2 d(i, j) - pi_i - pi_j hat
    paare_gesamt: int
    kleinster_kreis: float | None
    kleinstes_paar: tuple | None


def negativ_zaehlung(inst: Instanz, pi, typ: str = "minus") -> NegativZaehlung:
    """Zählt die negativen Bogenlängen und die negativen Hin-und-zurück-Kreise. Reine Rechnung an den Dualpreisen, kein Labeling.

    Typ „minus“ (die Längen des Pricings): Bogen d(i, j) - pi_j, Kreis 2 d(i, j) - pi_i - pi_j. Typ „plus“: Bogen d(i, j) + pi_j, Kreis 2 d(i, j) + pi_i + pi_j
    (bei nichtnegativen Dualpreisen nie negativ)."""
    n, d = inst.n, inst.d
    if typ == "minus":
        dep = sum(1 for j in range(1, n + 1) if d[0][j] - pi[j] < -1e-9)
        kk = sum(1 for i in range(1, n + 1) for j in range(1, n + 1) if i != j and d[i][j] - pi[j] < -1e-9)
        kreise = [(2 * d[i][j] - pi[i] - pi[j], i, j) for i in range(1, n + 1) for j in range(i + 1, n + 1)]
    else:
        dep = sum(1 for j in range(1, n + 1) if d[0][j] + pi[j] < -1e-9)
        kk = sum(1 for i in range(1, n + 1) for j in range(1, n + 1) if i != j and d[i][j] + pi[j] < -1e-9)
        kreise = [(2 * d[i][j] + pi[i] + pi[j], i, j) for i in range(1, n + 1) for j in range(i + 1, n + 1)]
    neg = sum(1 for c in kreise if c[0] < -1e-9)
    klein = min(kreise) if kreise else None
    return NegativZaehlung(dep, n, kk, n * (n - 1), neg, len(kreise), None if klein is None else klein[0], None if klein is None else (klein[1], klein[2]))
