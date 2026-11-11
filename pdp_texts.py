"""Längere Texte der App an einer Stelle: App und README zeigen denselben Wortlaut (`tests/test_claims.py` sucht den Text der App in der README)."""

ASSUMPTIONS_MARKDOWN = """\
**Annahmen**

- **Handbeispiel:** Depot und 7 Kunden, ganze Zahlen; Entfernung, Fahrzeit und Kosten sind der Manhattan-Abstand, Bedienzeit 2, Kapazität 6, Rückkehr bis 38. Das Fenster eines Kunden gilt für den Beginn der Bedienung (früher ankommen heißt warten, später ankommen ist unzulässig).
- **Kundeninstanzen:** selbst erzeugt im Stil der Solomon-Benchmarks (nicht die Originalinstanzen), 5 bis 20 Kunden gleichverteilt im Quadrat 100 × 100 (in den Messreihen auch gruppiert um fünf Zentren), Fahrzeit gleich Entfernung, Bedienzeit 10, Horizont 300, Kapazität 70, Fensterbreite 40 bis 100 (Messreihen bis 200).
- **Master:** Überdeckung (jeder Kunde mindestens einmal) oder Partitionierung (genau einmal), gelöst mit HiGHS über scipy; die Dualpreise sind die Schattenpreise der Kunden-Zeilen. Start: die Einzelfahrten Depot, Kunde, Depot.
- **Pricing:** Labeling mit Last, Fenstern, Horizont und Dominanz. In der Live-Rechnung elementar (jeder Kunde höchstens einmal); die Messreihen rechnen mit einem Gedächtnis aus den 5 nächsten Kunden (k = 5), der Vergleich von Überdeckung und Partitionierung mit k = 1, 5 und 8; ein Gedächtnis kleiner als die Kundenzahl schließt Kreise nicht ganz aus.
- **Messgröße:** Runden, Pricing-Aufrufe und erzeugte Labels. Sekunden stehen nur zur Information da und sind nicht festgeschrieben.

**Grenzen**

- Live gerechnet wird nur bis 20 Kunden. Die Messreihen sind fest: mit 30 Kunden 6 Instanzen je Zelle (beim Vergleich der Master 5 je Instanztyp und Gedächtnis), bei der Glättung mit 20 Kunden 12 Instanzen je Zelle: Mittel, Median und Maximum, keine Aussage über die ganze Verteilung.
- Die Glättung ist die einfache Glättung zur Vorrunde. Die Verfahren von Wentges (Zentrum = bestes bisheriges Dual) und von du Merle u. a. (Strafen im Dualraum) sind nicht gebaut und nicht gemessen; über „Stabilisierung“ im Allgemeinen sagt die Demo nichts.
- Überdeckung und Partitionierung wurden nur mit metrischen Kosten (Entfernungen) verglichen. Mit Festkosten je Fahrzeug oder Kosten ohne Dreiecksungleichung ist die gleiche Schranke nicht belegt.
- Keine Aussage über öffentliche Benchmarks, andere Programmiersprachen, andere LP-Löser oder andere Rechner.

**Bekannte Probleme und Unsicherheiten**

- Runden und Spalten hängen vom LP-Löser ab: Der Master hat oft mehrere gleich gute Dualpreise (Entartung), und HiGHS wählt je nach Version eine davon. Die Schranke hängt nicht davon ab. Die Messreihen nennen die scipy-Version, mit der sie gerechnet wurden.
- Die Messreihen sind mit den Instanzen dieser Demo (Zufalls-Seeds) neu gerechnet; eine frühere Messreihe mit anderen Instanzen gab ähnliche, aber nicht gleiche Zahlen (siehe README).
- Die Ansichten wurden mit Streamlits Testwerkzeug und im Browser (Desktop und Telefonbreite) geprüft: Seite lädt, Voreinstellungen, Master-Schalter und Längentyp wirken, Diagramme werden gezeichnet, kein seitliches Scrollen. Nicht jede Ansicht wurde als Bild durchgesehen und nicht alles auf allen Geräten; beim ersten Laden meldete die Browser-Konsole fünfmal einen Fehler in einer Plotly-Beschriftung („attribute y: Expected length“), der beim erneuten Zeichnen nicht wieder auftrat.
"""
