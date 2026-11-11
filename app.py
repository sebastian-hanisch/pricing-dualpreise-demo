"""Pricing aus Dualpreisen – warum Dijkstra nicht mehr reicht: interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Zeigt an einem Handbeispiel mit 7 Kunden und an Kundeninstanzen, wie in der Spaltenerzeugung die Bogenlängen des Pricings aus Dualpreisen entstehen, warum viele von ihnen
negativ sind, warum Dijkstra daran scheitert und das Labeling aus den früheren Demos der Linie den Weg findet. Aufbau nach DEMO-PLAYBOOK §2.

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import pdp_constants as C
import pdp_evaluation as ev
import pdp_visualization as V
from pdp_layout import dunkles_design, kopf_css
from pdp_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)
from pdp_texts import ASSUMPTIONS_MARKDOWN

st.set_page_config(page_title="Pricing aus Dualpreisen – Sebastian Hanisch", layout="wide")

TYPEN = {"Entfernung − Dualpreis (die Längen des Pricings)": "minus", "Entfernung + Dualpreis (nie negativ)": "plus"}


@st.cache_data(show_spinner=False)
def _hand(partition):
    return ev.analyse_hand(partition)


@st.cache_data(show_spinner=False)
def _bogen(pi, typ):
    return ev.analyse_bogen(pi, typ)


@st.cache_data(show_spinner=False)
def _labeling(pi):
    return ev.analyse_labeling(pi)


@st.cache_data(show_spinner=False)
def _gross(settings):
    return ev.analyse_gross(settings)


@st.cache_data(show_spinner=False)
def _glaettung(partition, alpha):
    return ev.analyse_glaettung_hand(partition, alpha)


@st.cache_data(show_spinner=False)
def _baender(name):
    return ev.lade_baender(name)


def _tabelle_preise(pi, n):
    return pd.DataFrame([{f"Kunde {j}": ev.zahl_kurz(pi[j]) for j in range(1, n + 1)}])


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in pdp_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("💶 Pricing aus Dualpreisen – warum Dijkstra nicht mehr reicht")
st.markdown(
    """
Bei der **Spaltenerzeugung** (etwa in der Tourenplanung) löst ein kleines Modell, der **Master**, die Aufgabe nur mit den bisher bekannten Touren und nennt zu jedem Kunden einen
**Dualpreis**: wie viel es dem Master wert ist, diesen Kunden zu bedienen. Das **Pricing** sucht danach eine neue Tour, die weniger kostet, als ihre Kunden an Dualpreisen einbringen.
Das ist ein Weg im Kundennetz, dessen Bögen die Länge **Entfernung minus Dualpreis des Zielkunden** haben. Viele dieser Längen sind negativ; das übliche **Dijkstra**-Verfahren (jeder
Knoten wird einmal abgeschlossen) findet dann den kürzesten Weg im Allgemeinen nicht mehr (im Handbeispiel verfehlt er ihn). Das **Labeling** mit Last, Zeitfenstern und Dominanz aus den früheren Demos der Reihe findet den besten **fahrbaren** Weg
(im Handbeispiel −10; der kürzeste Weg ohne Grenzen, −28, ist nicht fahrbar): Es verlängert die Teilwege nach wachsender Zeit statt nach Kosten, und die Grenzen machen die Wege endlich. Diese Demo rechnet das an einem Handbeispiel mit 7 Kunden Zeile für Zeile und misst es an Kundeninstanzen. Hier steht das Pricing in einer
laufenden Spaltenerzeugung.

Weiter unten: der Expander **💬 In einfachen Worten**, fünf Experimente (🔬), der Abschnitt **🚧 Wo die Annahmen enden** und die Expander **📐 Mathematische Formulierung** und **⚠️ Annahmen, Grenzen und bekannte Probleme**.
"""
)

# erklaerseite:einfach:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/pricing-dualpreise-erklaert.json, nicht von Hand ändern)
with st.expander("💬 In einfachen Worten"):
    st.markdown(
        """
Bei der **Spaltenerzeugung** löst ein Hauptplan, der **Master**, die Aufgabe nur mit den Touren, die er schon kennt, und rechnet jedem Kunden einen Wert zu, den **Dualpreis**. Das **Pricing** sucht danach eine neue Tour, die weniger kostet, als ihre Kunden an Wert einbringen. Das ist eine Wegsuche, bei der jede Fahrt ihre Strecke kostet und den Wert des Zielkunden gutschreibt. Viele dieser Längen liegen unter null. Das übliche Verfahren für kürzeste Wege, **Dijkstra**, kann dann einen Kunden zu früh abhaken und den besten Weg verfehlen; im Handbeispiel tut es das. Das **Labeling** findet den besten fahrbaren Weg, weil Last, Zeitfenster und die Regel „jeder Kunde höchstens einmal“ die Wege begrenzen. Die Demo rechnet das an einem Handbeispiel von Hand nach und fragt zuletzt, ob das Glätten der Dualpreise Runden spart.

[Ausführlich und verständlich erklärt, mit Fachteil](https://sebastianhanisch.net/pricing-dualpreise-erklaert.html)
        """
    )
# erklaerseite:einfach:end

with st.expander("So funktioniert das Pricing in der Spaltenerzeugung", expanded=True):
    st.markdown(
        """
1. **Master:** Ein LP wählt aus den bekannten Touren („Spalten“) die billigste Kombination, die jeden Kunden **mindestens einmal** (Überdeckung) oder **genau einmal** (Partitionierung) bedient.
   Zu Beginn sind es nur die Einzelfahrten Depot, Kunde, Depot. Die **Dualpreise** π sind die Schattenpreise der Kunden: um wie viel der Master-Wert bei der Überdeckung höchstens sinkt, wenn ein Kunde nicht bedient werden müsste; nur in der ersten Runde, in der der Master aus den Einzelfahrten besteht, sinkt er genau um π(j).
2. **Reduzierte Kosten:** Eine neue Tour lohnt sich, wenn ihre **Entfernungen minus die Dualpreise ihrer Kunden** kleiner als null sind. Als Weg im Netz: der Bogen von i nach j hat die Länge d(i, j) − π(j).
3. **Negative Längen:** In der ersten Runde ist π(j) die Hin-und-zurück-Fahrt zum Kunden, also doppelt so groß wie der Abstand des Kunden vom Depot. Alle Bögen vom Depot und viele Bögen zwischen Kunden sind negativ (im Handbeispiel 34 von 49 Bögen;
   in den Zufallsinstanzen der Messreihe sind es 77,7 % der Bögen zwischen Kunden), und Paare von Kunden bilden negative Hin-und-zurück-Kreise (im Handbeispiel 12 von 21 Paaren, in den
   Zufallsinstanzen der Messreihe alle 435 Paare). Dürfte ein Kunde mehrmals vorkommen und gäbe es keine Grenzen für Last und Zeit, gäbe es keinen kürzesten Weg, denn jede Runde im Kreis macht den Weg kürzer. Die endlosen Runden verhindert aber schon jede der beiden Bedingungen allein: die Regel „jeder Kunde höchstens einmal“ oder die Grenzen (mit ihnen wächst die Zeit bei jedem Halt um mindestens die Bedienzeit, und der Horizont ist begrenzt).
4. **Dijkstra scheitert:** Das Verfahren schließt jeden Knoten einmal ab und ändert ihn nie wieder. Das ist gesichert, wenn ein späterer Umweg den Abstand nie verkürzen kann, etwa bei nichtnegativen Längen.
   Mit negativen Längen kann er es, und Dijkstra verpasst diese Verbesserungen; ob er den besten Weg trotzdem trifft, hängt von der Instanz ab (im Handbeispiel trifft er ihn nicht). Außerdem kennt Dijkstra weder Last noch Zeitfenster.
   Die Zahlen des Handbeispiels (Länge −24, 21 verpasste Verbesserungen) gelten für die Regel „bei gleichem Abstand zuerst der Kunde mit der kleineren Nummer“: Kunde 3 und Kunde 7 haben in der ersten Runde beide den Abstand −5, und mit Kunde 7 zuerst wäre Dijkstras Länge −22 (20 verpasste Verbesserungen).
5. **Labeling:** Ein Label steht für einen Teilweg (Zeit, reduzierte Kosten, Last, Menge der besuchten Kunden). Ein Label dominiert ein anderes am selben Kunden, wenn es in allen Größen höchstens so groß ist
   und höchstens dieselben Kunden gesperrt hat. Das Labeling verlängert die Labels nach wachsender Zeit statt nach Kosten; Last, Fenster und Horizont machen die Wege endlich und die negativen Längen unschädlich.
6. **Schleife:** Die besten neuen Touren werden als Spalten an den Master angehängt (bei den Kundeninstanzen bis zu 15 je Runde, im Handbeispiel eine), der Master neu gelöst, mit neuen Dualpreisen weiter gesucht. Findet das Pricing keine Tour mit negativen reduzierten Kosten mehr, ist der
   Master-Wert die **Schranke** (bei elementarem Pricing der Wert des LP über alle zulässigen Touren).

Was „Master“, „Dualpreise“ und die Rundungslücke genau bedeuten, zeigt [column-generation-demo](https://github.com/sebastian-hanisch/column-generation-demo); die Wegformulierung im Netzwerkfluss mit
nichtnegativen Preisen [mcf-column-generation-demo](https://github.com/sebastian-hanisch/mcf-column-generation-demo). Hier steht nur, was am Pricing neu ist.
        """
    )

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Kundeninstanz (Experiment 3)**")
    n = st.slider("Kunden n", *bounds("n_slider"), key="n_slider", help="Zahl der Kunden der Live-Rechnung; das Depot liegt in der Mitte des Quadrats. Mehr als 20 Kunden sind feste Messreihen.")
    breite = st.slider("Fensterbreite", *bounds("breite_slider"), step=C.BREITE_STEP, key="breite_slider",
                       help="Breite der Zeitfenster der Kunden: je enger, desto weniger Wege sind zulässig.")
    seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)
    st.markdown("**Master und Glättung (Experimente 2 bis 4)**")
    partition = st.toggle("Partitionierung statt Überdeckung", key="partition",
                          help="Aus: jeder Kunde wird mindestens einmal bedient (Überdeckung). An: genau einmal (Partitionierung). Wirkt auf die Experimente 2, 3 und 4.")
    alpha = st.select_slider("Glättung α der Dualpreise in Prozent", options=list(C.ALPHA_OPTIONEN), key="alpha_pct",
                             help="0: keine Glättung. Sonst bekommt das Pricing α Prozent der Preise, mit denen das Pricing der Vorrunde gerechnet hat, und den Rest von den aktuellen Dualpreisen. Wirkt auf die Experimente 3 und 4.")

sync_query_params({"n_slider": int(n), "breite_slider": int(breite), "seed_input": int(seed), "alpha_pct": int(alpha), "partition": bool(partition)})

settings = ev.Settings(int(n), int(breite), int(seed), int(alpha), bool(partition))
h = _hand(settings.partition)
inst = h.inst
nn = inst.n
rs = h.lauf.runden
if h.fehler:
    st.error(f"Prüfung des Ergebnisses fehlgeschlagen: {h.fehler}")
pi1 = rs[0].pi
b1 = _bogen(pi1, "minus")
l1 = _labeling(pi1)

# --- Ergebnis ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ergebnis: das Handbeispiel in der ersten Runde")
m1, m2, m3 = st.columns(3)
m1.metric("Dijkstra mit den Längen des Pricings", f"Länge {ev.zahl_kurz(b1.dijkstra.laenge)}", delta=f"bester einfacher Weg: {ev.zahl_kurz(b1.einfach[1])}", delta_color="off")
m2.metric("Bester zulässiger Weg (Labeling)", f"reduzierte Kosten {ev.zahl_kurz(l1.beste[0])}", delta=f"Weg {ev.weg_text(l1.beste[1])}", delta_color="off")
m3.metric("Schranke der Spaltenerzeugung", ev.zahl_kurz(h.lauf.schranke), delta=f"nach {h.lauf.anzahl_runden} Runden", delta_color="off")
st.plotly_chart(V.build_handnetz(inst, b1.dijkstra.weg, l1.beste[1]), width="stretch", key="hand_chart")
st.caption("Depot (Raute) und 7 Kunden mit Last und Zeitfenster. Orange gestrichelt: der Weg, den Dijkstra mit den Längen des Pricings in der ersten Runde findet. Grün: der beste zulässige Weg des Labelings. "
           "Die Linien sind Luftlinien; gerechnet wird mit dem Manhattan-Abstand.")

# --- Kernfrage -----------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage: Findet Dijkstra den besten Weg, wenn die Längen aus Dualpreisen kommen?")
kind, text = ev.verdict_dijkstra(b1)
getattr(st, kind)(text)

st.markdown("---")

# --- Experiment 1: Bogenlängen ---------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 1: Von den Dualpreisen zu den Bogenlängen")
st.markdown(
    "Die Runde wählt, welche Dualpreise des Handbeispiels gelten (Runde 1: nur die Einzelfahrten im Master, der Dualpreis eines Kunden ist die Hin-und-zurück-Fahrt zu ihm; "
    "spätere Runden: Master mit den bisher erzeugten Spalten, gelöst mit HiGHS). Der Längentyp wählt, wie die Bogenlängen entstehen. Die Tabelle zeigt jede Länge, rot sind die negativen."
)
st.session_state["runde_hand"] = max(1, min(int(st.session_state.get("runde_hand", 1)), len(rs)))
c1, c2 = st.columns(2)
if len(rs) > 1:
    runde = c1.slider("Runde der Spaltenerzeugung", 1, len(rs), key="runde_hand", help="Welche Dualpreise gelten: die des Masters dieser Runde.")
else:
    runde = 1
typ_name = c2.radio("Länge der Bögen", list(TYPEN), key="laengentyp", horizontal=False)
typ = TYPEN[typ_name]
r_sel = rs[int(runde) - 1]
st.caption(f"Das Handbeispiel hat in dieser Rechnung {len(rs)} Runden (Master: {'Partitionierung' if settings.partition else 'Überdeckung'}). Dualpreise der Runde {int(runde)}:")
st.dataframe(_tabelle_preise(r_sel.pi, nn), hide_index=True, width="stretch")
b = _bogen(r_sel.pi, typ)
z = b.zaehlung
k1, k2, k3 = st.columns(3)
k1.metric("Negative Bögen Depot → Kunde", f"{z.depot_negativ} von {z.depot_gesamt}")
k2.metric("Negative Bögen Kunde → Kunde", f"{z.kunde_negativ} von {z.kunde_gesamt}")
k3.metric("Kundenpaare mit negativem Hin-und-zurück-Kreis", f"{z.paare_negativ} von {z.paare_gesamt}",
          delta=None if z.kleinstes_paar is None else f"kleinster Kreis {ev.zahl_kurz(z.kleinster_kreis)} bei ({z.kleinstes_paar[0]}, {z.kleinstes_paar[1]})", delta_color="off")
st.plotly_chart(V.build_bogenlaengen(b.laengen, nn), width="stretch", key="arcs_chart")
st.caption("Zeile = von (Depot oder Kunde), Spalte = nach (Kunde). Rot negativ, grün positiv. Ein Kreis i, j, i hat die Länge 2 d(i, j) − π(i) − π(j); ist sie negativ, macht jede Runde im Kreis den Weg kürzer.")
st.markdown(f"**Dijkstra** (Lehrbuchform, jeder Knoten wird einmal abgeschlossen) auf diesen Längen, danach die **Aufzählung aller {ev.zahl(b.einfach[0])} einfachen Wege** (jeder Kunde höchstens einmal) ohne Last und Fenster:")
d1, d2 = st.columns(2)
d1.metric("Weg von Dijkstra", ev.weg_text(b.dijkstra.weg), delta=f"Länge {ev.zahl_kurz(b.dijkstra.laenge)}", delta_color="off")
d2.metric("Bester einfacher Weg (Aufzählung)", ev.weg_text(b.einfach[2]), delta=f"Länge {ev.zahl_kurz(b.einfach[1])}", delta_color="off")
with st.expander("Die Schritte von Dijkstra"):
    st.markdown("\n".join(f"{i}. {ev.dijkstra_text(s, nn)}" for i, s in enumerate(b.dijkstra.schritte, 1)))
    st.caption(f"Verpasste Verbesserungen an schon abgeschlossenen Knoten: {b.dijkstra.verpasst}. Dijkstra zählt sie nicht als Fehler, er sieht sie nicht. Bei gleichem Abstand schließt Dijkstra hier den Kunden mit der kleineren Nummer zuerst ab; die Zahlen hängen an dieser Regel.")
with st.expander("Fahrplan des Dijkstra-Wegs und Zulässigkeit"):
    st.markdown(f"Weg von Dijkstra {ev.weg_text(b.dijkstra.weg)}: **{b.dijkstra_zulaessig[1]}**. Bester einfacher Weg {ev.weg_text(b.einfach[2])}: **{b.einfach_zulaessig[1]}**.")
    st.markdown("\n".join(f"- {ev.fahrplan_text(x)}" for x in b.fahrplan_dijkstra))
kind, text = ev.verdict_dijkstra(b)
getattr(st, kind)(text)

st.markdown("---")

# --- Experiment 2: Labeling und Spaltenerzeugung -------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 2: Labeling im Ressourcennetz und Spaltenerzeugung am Handbeispiel")
st.markdown(
    f"Je Runde ein Pricing-Aufruf: Das **Labeling** (elementar, mit Last, Fenstern und Dominanz) liefert die beste Route, sie wird als neue Spalte angehängt, der Master ({'Partitionierung' if settings.partition else 'Überdeckung'}) "
    "wird neu gelöst. Gewählt ist wieder die Runde; die Tabelle zeigt die Labels, die am Ende des Aufrufs übrig sind, und die Dominanzentscheidungen mit Begründung."
)
st.session_state["runde_labeling"] = max(1, min(int(st.session_state.get("runde_labeling", 1)), len(rs)))
if len(rs) > 1:
    runde2 = st.slider("Runde", 1, len(rs), key="runde_labeling", help="Welche Runde der Spaltenerzeugung gezeigt wird.")
else:
    runde2 = 1
r2 = rs[int(runde2) - 1]
la = _labeling(r2.pi_pricing)
q1, q2, q3, q4 = st.columns(4)
q1.metric("Erzeugte Labels", la.erzeugt)
q2.metric("Sofort verworfen (dominiert)", la.verworfen)
q3.metric("Später verdrängt", la.verdraengt)
q4.metric("Am Ende übrig", la.lebend)
st.caption(f"Abgelehnte Verlängerungen: {la.abgelehnt_last} wegen der Last, {la.abgelehnt_fenster} wegen des Fensterendes, {la.verboten} weil der Kunde schon besucht ist (elementar).")
tab_zeilen = [{"Kunde": j + 1, "Label": f"L{nr}", "Weg": ev.weg_text(w), "Zeit": ev.zahl_kurz(t), "reduzierte Kosten": ev.zahl_kurz(c), "Last": ev.zahl_kurz(q)}
              for j, liste in enumerate(la.tabelle) for (nr, w, t, c, q) in liste]
with st.expander(f"Labels am Ende von Runde {int(runde2)} (je Kunde)", expanded=True):
    st.dataframe(pd.DataFrame(tab_zeilen), hide_index=True, width="stretch")
with st.expander("Dominanzentscheidungen mit Begründung"):
    if la.dominanz:
        st.dataframe(pd.DataFrame([{"Art": a, "Label (Weg)": ev.weg_text(w1), "dominiert von (Weg)": ev.weg_text(w2), "Begründung": text} for a, w1, w2, text, _, _ in la.dominanz]), hide_index=True, width="stretch")
    else:
        st.markdown("In diesem Aufruf wurde kein Label dominiert.")
    st.caption("Ein Label dominiert ein anderes am selben Kunden, wenn Kosten, Zeit und Last höchstens so groß sind und die Menge der besuchten Kunden eine Teilmenge ist. Gleiche Werte: das früher erzeugte Label bleibt.")
kind, text = ev.verdict_labeling(la, len(h.wege))
getattr(st, kind)(text)
if r2.neue:
    st.markdown(f"**Neue Spalte dieser Runde:** Route {ev.weg_text(r2.neue[0])} mit reduzierten Kosten {ev.zahl_kurz(r2.beste_rc)} unter den Dualpreisen der Runde. Fahrplan:")
    st.markdown("\n".join(f"- {ev.fahrplan_text(x)}" for x in la.fahrplan))
else:
    st.markdown("**In dieser Runde findet das Pricing keine Route mit negativen reduzierten Kosten: Die Spaltenerzeugung ist am Ende.**")
st.markdown(f"**Master dieser Runde:** Wert {ev.zahl_kurz(r2.master_wert)}; Spalten mit Menge größer null:")
st.dataframe(pd.DataFrame([{"Route": ev.weg_text(w), "Menge": ev.zahl(m, 2)} for w, m in r2.x]), hide_index=True, width="stretch")
st.markdown("**Alle Runden im Überblick:**")
st.dataframe(pd.DataFrame([{"Runde": r.nr, "Master-Wert": ev.zahl_kurz(r.master_wert), "neue Spalte": ev.weg_text(r.neue[0]) if r.neue else "keine", "reduzierte Kosten der Spalte": ev.zahl_kurz(r.beste_rc) if r.neue else "-",
                            "Labels": r.labels} for r in rs]), hide_index=True, width="stretch")
st.markdown("**Gegenprobe:** alle zulässigen elementaren Wege des Handbeispiels aufgezählt (Tiefensuche, ohne Labeling) und alle als Spalten in einen Master gelegt.")
kind, text = ev.verdict_gegenprobe(h)
getattr(st, kind)(text)
st.caption("Die Dualpreise der späteren Runden hängen vom LP-Löser ab (der Master ist entartet, mehrere Dualpreise sind gleich gut); die Schranke hängt nicht davon ab. "
           "Mit der Einstellung „Partitionierung“ ist die Schranke im Handbeispiel dieselbe (Kosten sind Entfernungen).")

st.markdown("---")

# --- Experiment 3: Größenregler --------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 3: Größe – Kunden, Fensterbreite und eine ganze Spaltenerzeugung")
st.markdown(
    f"Eine Kundeninstanz im Stil der Solomon-Benchmarks (selbst erzeugt, nicht die Originalinstanzen): Depot in der Mitte eines Quadrats von 100 × 100, Fahrzeit gleich Entfernung, Bedienzeit {C.BEDIENZEIT}, "
    f"Horizont {C.HORIZONT}, Kapazität {C.KAPAZITAET}, Last 5 bis 25 je Kunde. Die Spaltenerzeugung läuft hier **live** bis zum Ende, mit elementarem Pricing; nur bis {C.N_MAX} Kunden, größere Fälle sind feste Messreihen."
)
with st.spinner("Die Spaltenerzeugung läuft …"):
    g = _gross(settings)
if g.fehler:
    st.error(f"Prüfung des Ergebnisses fehlgeschlagen: {g.fehler}")
lauf = g.lauf
g1, g2, g3, g4 = st.columns(4)
g1.metric("Runden", ev.zahl(lauf.anzahl_runden))
g2.metric("Spalten am Ende", ev.zahl(len(lauf.spalten)), delta=f"davon {settings.n} Einzelfahrten vom Start", delta_color="off")
g3.metric("Erzeugte Labels", ev.zahl(lauf.labels))
g4.metric("Schranke", ev.zahl(lauf.schranke, 2))
cc1, cc2 = st.columns(2)
cc1.plotly_chart(V.build_kurve([("Master-Wert", [r.master_wert for r in lauf.runden])]), width="stretch", key="curve_chart")
cc2.plotly_chart(V.build_balken([r.nr for r in lauf.runden], [("erzeugte Labels", [r.labels for r in lauf.runden])], titel_y="Labels", titel_x="Runde"), width="stretch", key="labels_chart")
st.caption("Links: der Master-Wert je Runde fällt nie und endet bei der Schranke. Rechts: die erzeugten Labels des Pricings je Runde.")
kind, text = ev.verdict_gross(settings, g)
getattr(st, kind)(text)
x_end = lauf.runden[-1].x
st.markdown("Endlösung des Masters (Spalten mit Menge größer null):")
st.dataframe(pd.DataFrame([{"Route": ev.weg_text(w), "Menge": ev.zahl(m, 2)} for w, m in x_end]), hide_index=True, width="stretch")
st.caption(
    f"Eine Rechnung, ein Zufalls-Seed ({settings.seed}). Rechenzeit dieser Rechnung: {ev.zahl(g.sekunden, 1)} s; Sekunden hängen von der Last der Maschine ab und sind nicht festgeschrieben, gezählt werden Labels. "
    "Runden und Spalten hängen vom LP-Löser ab (entartete Dualpreise, HiGHS-Version), die Schranke nicht."
)

st.markdown("---")

# --- Experiment 4: Glättung ------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 4: Glättung der Dualpreise – einfache Glättung zur Vorrunde, nicht Wentges und nicht du Merle")
st.markdown(
    "Die Dualpreise des Masters springen von Runde zu Runde. Die **Glättung** gibt dem Pricing nicht die aktuellen Dualpreise π, sondern α · (Preise, mit denen das Pricing der Vorrunde gerechnet hat) + (1 − α) · π. Findet das Pricing damit "
    "keine Spalte, die unter den echten Dualpreisen negative reduzierte Kosten hat, ist das ein **Fehlgriff**, und es wird sofort mit den echten Dualpreisen noch einmal gerechnet. "
    "Die Schranke ist in allen gemessenen Instanzen und allen α gleich; gefragt ist, ob die Glättung Runden spart. Gemessen ist nur diese einfache Glättung, nicht die Verfahren von Wentges oder du Merle u. a."
)
gl = _glaettung(settings.partition, settings.alpha)
if gl.fehler:
    st.error(f"Prüfung des Ergebnisses fehlgeschlagen: {gl.fehler}")
st.markdown(f"**Live am Handbeispiel** (α = {ev.alpha_text(settings.alpha)} aus der Seitenleiste, eine neue Spalte je Runde, eine Instanz, kein Befund):")
e1, e2, e3 = st.columns(3)
e1.metric("Runden", gl.mit.anzahl_runden, delta=f"ohne Glättung {gl.ohne.anzahl_runden}", delta_color="off")
e2.metric("Pricing-Aufrufe", gl.mit.aufrufe, delta=f"ohne Glättung {gl.ohne.aufrufe}", delta_color="off")
e3.metric("Fehlgriffe", gl.mit.fehlgriffe)
serien = [("ohne Glättung", [r.master_wert for r in gl.ohne.runden])]
if settings.alpha:
    serien.append((f"α = {ev.alpha_text(settings.alpha)}", [r.master_wert for r in gl.mit.runden]))
st.plotly_chart(V.build_kurve(serien), width="stretch", key="smooth_curve_chart")
kind, text = ev.verdict_glaettung_live(settings.alpha, gl)
getattr(st, kind)(text)
gb = _baender("glaettung")
for nn_band in (20, 30):
    zz = ev.zeilen_glaettung(gb, nn_band)
    st.markdown(f"**Feste Messreihe, {nn_band} Kunden** ({zz[0]['instanzen']} Instanzen, Fensterbreite 100, Pricing mit Gedächtnis k = 5, Überdeckungs-Master, Zufalls-Seeds der Demo):")
    st.dataframe(pd.DataFrame(ev.tabelle_glaettung(zz)), hide_index=True, width="stretch")
    st.plotly_chart(V.build_balken([ev.alpha_text(z["alpha"]) for z in zz], [("Runden (Mittel)", [z["runden"]["mittel"] for z in zz]), ("Pricing-Aufrufe (Mittel)", [z["aufrufe"]["mittel"] for z in zz])],
                                   titel_y="Mittel über die Instanzen", titel_x="Glättung α"), width="stretch", key=f"smooth_band_chart_{nn_band}")
    kind, text = ev.verdict_glaettung_band(zz)
    getattr(st, kind)(text)
st.caption("Hinweise: einfache Glättung zur Vorrunde (nicht Wentges, nicht du Merle u. a.); bei 20 Kunden 12, bei 30 Kunden 6 Instanzen, kein Konfidenzmaß; Runden und Aufrufe hängen vom LP-Löser ab, die Schranke nicht.")

st.markdown("---")

# --- Experiment 5: Bänder -----------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 5: Bänder – negative Längen, Master und Runden aus festen Messreihen")
neg = _baender("negativ")
zn = {z["runde"]: ev.zeile_negativ(z) for z in neg["zeilen"]}
st.markdown(f"**Wie viele Bogenlängen sind negativ?** {neg['beschreibung']} {zn['erste']['n']} Instanzen mit 30 Kunden, Fensterbreite 100.")
st.dataframe(pd.DataFrame(ev.tabelle_negativ(zn)), hide_index=True, width="stretch")
st.plotly_chart(V.build_balken(["Bögen Depot → Kunde", "Bögen Kunde → Kunde", "Kundenpaare mit negativem Kreis"],
                               [(("erste Runde" if name == "erste" else "letzte Runde"), [100 * z["depot"]["mittel"] / z["depot_gesamt"], 100 * z["kunde"]["mittel"] / z["kunde_gesamt"], 100 * z["paare"]["mittel"] / z["paare_gesamt"]])
                                for name, z in zn.items()], titel_y="negativ in Prozent (Mittel)"), width="stretch", key="neg_chart")
kind, text = ev.verdict_negativ(zn)
getattr(st, kind)(text)

ma = _baender("master")
paare = ev.paare_master(ma)
st.markdown(f"**Überdeckung gegen Partitionierung.** {ma['beschreibung']} 30 Kunden, drei Instanztypen (zufällig verteilt, gruppiert, langer Horizont) mit je 5 Instanzen und Pricing-Gedächtnis k = 1, 5, 8.")
st.dataframe(pd.DataFrame(ev.tabelle_master(ma)), hide_index=True, width="stretch")
kind, text = ev.verdict_master(paare)
getattr(st, kind)(text)

ru = _baender("runden")
zr = [ev.zeile_runden(z) for z in ru["zeilen"]]
st.markdown(f"**Runden und Spalten einer ganzen Spaltenerzeugung.** {ru['beschreibung']} 30 Kunden, Pricing mit Gedächtnis k = 5, Überdeckungs-Master, 6 Instanzen je Fensterbreite.")
st.dataframe(pd.DataFrame(ev.tabelle_runden(zr)), hide_index=True, width="stretch")
st.plotly_chart(V.build_balken([z["breite"] for z in zr], [("Runden (Median)", [z["runden"]["median"] for z in zr]), ("Runden (Maximum)", [z["runden"]["max"] for z in zr])],
                               titel_y="Runden", titel_x="Fensterbreite"), width="stretch", key="rounds_chart")
kind, text = ev.verdict_runden(zr)
getattr(st, kind)(text)
st.caption(
    "Hinweise: nur 6 Instanzen je Zelle (beim Vergleich der Master 5 je Typ und Gedächtnis); Runden und Spalten hängen vom LP-Löser ab (entartete Dualpreise, HiGHS-Version), die Schranke nicht; "
    f"die Reihen sind mit {neg['umgebung']} gerechnet; n ≤ {C.N_MAX} wird live gerechnet, n = 30 sind feste Messreihen."
)
with st.expander("Quellen der Zeilen"):
    for z in neg["zeilen"] + ru["zeilen"] + gb["zeilen"] + ma["zeilen"]:
        st.markdown(f"- {z['quelle']}")

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Was zeigt es |
|---|---|---|
| **Die Bogenlängen sind nichtnegativ.** | Dijkstra schließt jeden Knoten einmal ab. Mit negativen Längen (Entfernung minus Dualpreis) kann ein späterer Umweg einen abgeschlossenen Knoten verbessern, und Dijkstra übernimmt das nicht. | Experiment 1 |
| **Last und Zeitfenster sind kein Teil des Netzes.** | Dijkstra kennt sie nicht; sein Weg kann Last oder Fenster verletzen, und der kürzeste Weg ohne Grenzen kann zu lang oder zu spät sein. Das Labeling führt beide Größen als Teil des Labels. | Experimente 1 und 2 |
| **Das Pricing ist elementar.** | Die Live-Rechnung erlaubt jeden Kunden höchstens einmal. Die Messreihen rechnen mit einem Gedächtnis aus 5 Kunden (k = 5; beim Vergleich der Master auch k = 1 und 8), das Kreise nicht ganz ausschließt; was die Elementarität kostet, zeigt diese Demo nicht. | Experimente 3 bis 5 |
| **Überdeckung und Partitionierung geben dieselbe Schranke.** | Gemessen nur mit metrischen Kosten (Entfernungen). Mit Festkosten je Fahrzeug oder Kosten, die die Dreiecksungleichung brechen, ist die gleiche Schranke nicht belegt. | Experiment 5 |
| **Die Glättung ist die einfache zur Vorrunde.** | Wentges (Zentrum = bestes bisheriges Dual) und du Merle u. a. (Strafen im Dualraum) sind nicht gebaut; über „Stabilisierung“ im Allgemeinen sagen die Zahlen nichts. | Experiment 4 |
| **Gemessen wird an 5, 6 bzw. 12 Instanzen je Zelle** (30 Kunden: 5 oder 6, Glättung mit 20 Kunden: 12). | Die Spanne innerhalb einer Zelle ist groß: bei Fensterbreite 40 reichen die Runden von 11 bis 31 bei einem Median von 18,0, eine einzelne Instanz kann also deutlich vom Median abweichen. | Experimente 4 und 5 |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    # erklaerseite:lesehilfe:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/pricing-dualpreise-erklaert.json, nicht von Hand ändern)
    st.markdown(
        r"""
**Lesehilfe.** Gegeben sind ein Depot, $n$ Kunden mit Last, Zeitfenster und Entfernungen (Entfernung = Fahrzeit = Kosten) und eine Menge $R$ bekannter Touren (Spalten). Gesucht sind die billigste Kombination der Touren, die jeden Kunden bedient (Master), und in jeder Runde eine neue Tour mit negativen reduzierten Kosten (Pricing). Verfahren: Spaltenerzeugung mit Labeling.

| Symbol | Bedeutung |
|---|---|
| $d_{ij}$ | Entfernung (= Fahrzeit = Kosten) von $i$ nach $j$; 0 ist das Depot, $1,\dots,n$ sind die Kunden |
| $\sigma,\ q_j,\ Q$ | Bedienzeit, Last von Kunde $j$, Kapazität |
| $[a_j, b_j],\ H$ | Zeitfenster für den Beginn der Bedienung bei Kunde $j$, Horizont für die Rückkehr |
| $R,\ c_r,\ A_{jr}$ | Menge der Touren (Spalten), Kosten der Tour $r$, wie oft $r$ den Kunden $j$ besucht |
| $x_r$ | Menge der Tour $r$ im Master |
| $\pi_j$ | Dualpreis von Kunde $j$ ($\pi_0 = 0$) |
| $\ell_{ij}$ | Länge des Bogens $i \to j$ im Pricing |
| $\bar c$ | reduzierte Kosten einer Tour: ihre Kosten minus die Dualpreise ihrer Kunden |
| $(t, c, q, M)$ | Label: Zeit, reduzierte Kosten, Last, Menge $M$ der gesperrten Kunden |
| $N_k(j)$ | die $k$ nächsten Kunden von $j$ einschließlich $j$ (Gedächtnis; $k = n$: elementar) |
| $\alpha,\ \tilde\pi$ | Glättung und die geglätteten Preise, mit denen das Pricing rechnet |

[Schritt für Schritt erklärt, mit Herleitung und Literatur](https://sebastianhanisch.net/pricing-dualpreise-erklaert.html#fachleute)
        """
    )
    # erklaerseite:lesehilfe:end
    st.markdown(
        r"""
**Master (Überdeckung)** und sein duales Problem:

$$\min \sum_{r \in R} c_r x_r \quad \text{unter} \quad \sum_{r \in R} A_{jr}\, x_r \ge 1 \;\; (j = 1,\dots,n), \quad x \ge 0 .$$

$$\max \sum_{j=1}^{n} \pi_j \quad \text{unter} \quad \sum_{j=1}^{n} A_{jr}\, \pi_j \le c_r \;\; (r \in R), \quad \pi \ge 0 .$$

Bei der Partitionierung steht $=1$ statt $\ge 1$, und $\pi$ ist nicht vorzeichenbeschränkt.

**Reduzierte Kosten und Bogenlängen.** Eine Tour $0 \to j_1 \to \dots \to j_m \to 0$ hat die reduzierten Kosten

$$\bar c = \sum_{i=0}^{m} d_{j_i j_{i+1}} - \sum_{i=1}^{m} \pi_{j_i} = \sum_{i=0}^{m-1} \ell_{j_i j_{i+1}} + d_{j_m 0}, \qquad \ell_{ij} = d_{ij} - \pi_j \quad (j_0 = j_{m+1} = 0).$$

Sie ist eine neue Spalte, wenn $\bar c < 0$. Ein Hin-und-zurück-Kreis $i \to j \to i$ hat die Länge

$$\ell_{ij} + \ell_{ji} = 2\,d_{ij} - \pi_i - \pi_j .$$

**Dijkstra** setzt für jeden Knoten $v$ den Abstand einmal fest. Das ist gesichert, wenn $\ell_{ij} \ge 0$ für alle Bögen gilt: dann kann ein späterer Weg zu $v$ nie kürzer werden als der abgeschlossene. Die Bedingung ist hinreichend, nicht notwendig; mit negativen Bögen kann Dijkstra den besten Weg verfehlen, muss es aber nicht.

**Verlängerung.** Aus einem Label $(t, c, q, M)$ am Knoten $i$ entsteht über den Kunden $j$ mit $j \notin M$ das Label

$$t' = \max\bigl(t + \sigma_i + d_{ij},\; a_j\bigr), \quad c' = c + d_{ij} - \pi_j, \quad q' = q + q_j, \quad M' = (M \cap N_k(j)) \cup \{j\},$$

nur falls $t + \sigma_i + d_{ij} \le b_j$ und $q' \le Q$ ($\sigma_i = \sigma$ für einen Kunden, $0$ am Depot). Die Tour darf ins Depot zurück, wenn $t + \sigma + d_{j0} \le H$.

**Dominanz.** $(t, c, q, M)$ dominiert $(t', c', q', M')$ am selben Kunden, wenn

$$c \le c', \quad t \le t', \quad q \le q', \quad M \subseteq M' .$$

**Glättung.** Das Pricing rechnet mit $\tilde\pi = \alpha\,\pi^{\text{Vorrunde}} + (1-\alpha)\,\pi$, wobei $\pi^{\text{Vorrunde}}$ die Preise sind, mit denen das Pricing der Vorrunde gerechnet hat. Eine Spalte wird nur angehängt, wenn ihre reduzierten Kosten unter den echten $\pi$ negativ sind;
sonst folgt ein Fehlgriff und eine Rechnung mit $\alpha = 0$.

**Literatur.** Dantzig, Wolfe (1960): *Decomposition Principle for Linear Programs*, Operations Research 8(1), S. 101–111; Gilmore, Gomory (1961): Operations Research 9(6), S. 849–859 (erste Anwendung am Cutting Stock); Desrochers, Soumis (1988):
*A generalized permanent labelling algorithm for the shortest path problem with time windows*, INFOR 26, S. 191–212; Lübbecke, Desrosiers (2005): *Selected Topics in Column Generation*, Operations Research 53(6), S. 1007–1023 (duale Sicht, Entartung, Stabilisierung);
du Merle, Villeneuve, Desrosiers, Hansen (1999): Discrete Mathematics 194(1–3), S. 229–237 (Strafen im Dualraum); Irnich, Desaulniers (2005): *Shortest Path Problems with Resource Constraints*, in: Column Generation, Springer, S. 33–65.
Prüfstand: bei allen nur Abstract oder Suchtreffer gesehen, bei Irnich/Desaulniers nur das Zitat; kein Volltext gelesen. Die einfache Glättung (nach Neame) und das Verfahren von Wentges sind aus dem Gedächtnis genannt und nicht geprüft.
Keine Zahl der Demo stammt aus der Literatur.
        """
    )

with st.expander("⚠️ Annahmen, Grenzen und bekannte Probleme"):
    st.markdown(ASSUMPTIONS_MARKDOWN)

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Ressourcenwege: von der Grenze zur Verfahrenswahl](https://sebastianhanisch.net/konzepte-ressourcenwege.html)."
)
