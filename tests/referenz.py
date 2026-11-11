"""Zweite, unabhängige Implementierung der Rechenschritte für die Orakel- und Eigenschaftstests (nicht der Rechenweg der Demo).

* `master_exakt`: Überdeckungs-Master als LP mit Brüchen (`fractions`), gelöst über das Duale mit dem Simplex-Verfahren nach der Regel von Bland: Dualpreise, Wert, Mengen. Kein scipy.
* `labeling_ref`: Labeling mit Mengen (`frozenset`) und exakter Bruchrechnung, Dominanz durch doppelte Schleife; zählt erzeugte und dominierte Labels wie die Demo.
* `wege_dfs`: Tiefensuche über alle zulässigen elementaren Wege; `einfache_wege`: alle einfachen Wege ohne Grenzen.
Alles nur Standardbibliothek; Zeitfenster, Last und Horizont stehen hier noch einmal in eigener Schreibweise."""

import heapq
from fractions import Fraction as Fr


def kosten(inst, route):
    folge = (0,) + tuple(route) + (0,)
    return sum(inst.d[a][b] for a, b in zip(folge, folge[1:]))


def wege_dfs(inst):
    """Alle zulässigen elementaren Wege als Tupel; Zeit = Beginn der Bedienung, Last, Rückkehr bis H (inklusive)."""
    n = inst.n
    out = []

    def rec(weg, zeit, last):
        i = weg[-1] if weg else 0
        if weg and zeit + inst.svc + inst.d[i][0] <= inst.H + 1e-9:
            out.append(tuple(weg))
        for j in range(1, n + 1):
            if j in weg:
                continue
            if last + inst.dem[j] > inst.Q:
                continue
            ankunft = zeit + (inst.svc if i != 0 else 0) + inst.d[i][j]
            if ankunft > inst.due[j] + 1e-9:
                continue
            weg.append(j)
            rec(weg, max(ankunft, inst.ready[j]), last + inst.dem[j])
            weg.pop()

    rec([], 0, 0)
    return out


def einfache_wege(n):
    """Alle Folgen verschiedener Kunden (mindestens einer): die einfachen Wege ohne Grenzen."""
    out = []

    def rec(weg):
        if weg:
            out.append(tuple(weg))
        for j in range(1, n + 1):
            if j not in weg:
                weg.append(j)
                rec(weg)
                weg.pop()

    rec([])
    return out


def master_exakt(inst, spalten):
    """Überdeckungs-Master `min c x, A x >= 1, x >= 0` mit Brüchen. Gelöst wird das Duale `max sum(pi), A^T pi <= c, pi >= 0` im Tableau (Regel von Bland);
    Rückgabe (Dualpreise mit Index 0 = Depot, Wert, Mengen x je Spalte). Nur für ganzzahlige Entfernungen (Handbeispiel und Instanzen mit ganzen Zahlen)."""
    n, m = inst.n, len(spalten)
    T = []
    for r, w in enumerate(spalten):
        zeile = [Fr(0)] * (n + m)
        for j in w:
            zeile[j - 1] += 1
        zeile[n + r] = Fr(1)
        T.append(zeile + [Fr(kosten(inst, w))])
    ziel = [Fr(1)] * n + [Fr(0)] * m + [Fr(0)]
    basis = [n + r for r in range(m)]
    while True:
        e = next((j for j in range(n + m) if ziel[j] > 0), None)
        if e is None:
            break
        best = None
        for r in range(m):
            if T[r][e] > 0:
                key = (T[r][-1] / T[r][e], basis[r])
                if best is None or key < best[0]:
                    best = (key, r)
        r = best[1]
        piv = T[r][e]
        T[r] = [x / piv for x in T[r]]
        for i in range(m):
            if i != r and T[i][e] != 0:
                f = T[i][e]
                T[i] = [a - f * b for a, b in zip(T[i], T[r])]
        f = ziel[e]
        ziel = [a - f * b for a, b in zip(ziel, T[r])]
        basis[r] = e
    pi = [Fr(0)] * (n + 1)
    for r, b in enumerate(basis):
        if b < n:
            pi[b + 1] = T[r][-1]
    x = [-ziel[n + r] for r in range(m)]
    return pi, -ziel[-1], x


def spaltenerzeugung_exakt(inst, pricing="labeling"):
    """Spaltenerzeugung mit dem exakten Master. Pricing „labeling“: die beste Route unter den Routen, die `labeling_ref` liefert (nicht dominierte Labels); „dfs“: die beste Route
    unter allen zulässigen (Tiefensuche). Je Runde eine Spalte, Gleichstand: kleinste Folge. Rückgabe: Liste der Runden (Master-Wert, Dualpreise, neue Spalte oder None) und die Spalten."""
    alle = wege_dfs(inst) if pricing == "dfs" else None
    spalten = [(j,) for j in range(1, inst.n + 1)]
    runden = []
    while True:
        pi, wert, x = master_exakt(inst, spalten)
        if pricing == "dfs":
            kandidaten = sorted((kosten(inst, w) - sum(pi[j] for j in w), w) for w in alle if w not in spalten)
        else:
            kandidaten = sorted((rc, w) for w, rc in labeling_ref(inst, pi)[5].items() if w not in spalten)
        neu = kandidaten[0][1] if kandidaten and kandidaten[0][0] < 0 else None
        runden.append((wert, pi, neu))
        if neu is None:
            return runden, spalten
        spalten.append(neu)


def labeling_ref(inst, pi):
    """Elementares Labeling mit Mengen und Brüchen. Rückgabe (erzeugt, dominiert, beste Route, beste reduzierte Kosten, Zahl der Routen, die ins Depot zurückkehren, alle diese Routen mit ihren reduzierten Kosten)."""
    n = inst.n
    labels = [dict(zeit=Fr(0), kosten=Fr(0), last=0, besucht=frozenset(), knoten=0, eltern=-1, tot=False)]
    am_knoten = {j: [] for j in range(1, n + 1)}
    heap = [(Fr(0), 0)]
    erzeugt, dominiert = 1, 0
    ende = {}

    def weg(i):
        w = []
        while i != -1:
            w.append(labels[i]["knoten"])
            i = labels[i]["eltern"]
        return tuple(reversed(w))[1:]

    def dom(a, b):
        return a["kosten"] <= b["kosten"] and a["zeit"] <= b["zeit"] and a["last"] <= b["last"] and a["besucht"] <= b["besucht"]

    while heap:
        _, li = heapq.heappop(heap)
        L = labels[li]
        if L["tot"]:
            continue
        i = L["knoten"]
        if i != 0 and L["zeit"] + inst.svc + inst.d[i][0] <= inst.H:
            ende[weg(li)] = L["kosten"] + inst.d[i][0]
        for j in range(1, n + 1):
            if j == i or j in L["besucht"]:
                continue
            last = L["last"] + inst.dem[j]
            if last > inst.Q:
                continue
            ankunft = L["zeit"] + (inst.svc if i != 0 else 0) + inst.d[i][j]
            if ankunft > inst.due[j]:
                continue
            neu = dict(zeit=Fr(max(ankunft, inst.ready[j])), kosten=L["kosten"] + inst.d[i][j] - Fr(pi[j]), last=last, besucht=L["besucht"] | {j}, knoten=j, eltern=li, tot=False)
            erzeugt += 1
            if any(dom(labels[o], neu) for o in am_knoten[j] if not labels[o]["tot"]):
                dominiert += 1
                continue
            for o in am_knoten[j]:
                if not labels[o]["tot"] and dom(neu, labels[o]):
                    labels[o]["tot"] = True
                    dominiert += 1
            labels.append(neu)
            idx = len(labels) - 1
            am_knoten[j].append(idx)
            heapq.heappush(heap, (neu["zeit"], idx))
    if not ende:
        return erzeugt, dominiert, None, None, 0, ende
    beste = min((rc, w) for w, rc in ende.items())
    return erzeugt, dominiert, beste[1], beste[0], len(ende), ende
