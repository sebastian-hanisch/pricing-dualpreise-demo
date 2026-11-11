# Pricing aus Dualpreisen – warum Dijkstra nicht mehr reicht – Streamlit-Demo

Demo der Reihe „Ressourcenwege und Spaltenerzeugung“ in der „Konzepte“-Reihe der Website „Sebastian Hanisch – Operations Research und Machine Learning“. Sie zeigt, was am **Pricing** der Spaltenerzeugung neu ist: Die Bogenlängen entstehen aus **Dualpreisen** (Entfernung minus Dualpreis des Zielkunden), viele von ihnen sind negativ, und das übliche Dijkstra-Verfahren findet den kürzesten Weg dann nicht mehr verlässlich (im Handbeispiel verfehlt es ihn). Das Labeling mit Last, Zeitfenstern und Dominanz aus den früheren Demos der Reihe findet den besten fahrbaren Weg (im Handbeispiel −10; der kürzeste Weg ohne Grenzen, −28, ist nicht fahrbar): Es verlängert die Teilwege nach wachsender Zeit statt nach Kosten, und die Grenzen machen die Wege endlich. Das Vehikel ist ein Handbeispiel mit 7 Kunden, das sich von Hand nachrechnen lässt, und selbst erzeugte Kundeninstanzen im Stil der Solomon-Benchmarks (nicht die Originalinstanzen). Solche Wegsuchen sind das Pricing in der Tourenplanung, etwa in [crew-pairing-demo](https://github.com/sebastian-hanisch/crew-pairing-demo); diese Demo erklärt die Schleife dahinter.

## Kernfrage

Die Spaltenerzeugung löst einen **Master** (ein LP über die bisher bekannten Touren) und fragt mit seinen **Dualpreisen** nach einer neuen Tour, deren Entfernungen weniger kosten, als ihre Kunden an Dualpreisen einbringen. Als Weg im Kundennetz hat der Bogen von i nach j die Länge d(i, j) − π(j). Findet Dijkstra auf diesen Längen den besten Weg, und wenn nicht, was findet den besten fahrbaren Weg? Wie viele Runden braucht die Spaltenerzeugung, und spart die Glättung der Dualpreise Runden?

## Befunde und Korrekturen gegenüber dem Plan

- **Neu gerechnete Messreihen mit den Instanzen dieser Demo.** Der Plan nannte Zahlen einer früheren Messreihe, deren Instanzen mit Pythons `random.Random` erzeugt wurden. Diese Demo erzeugt ihre Instanzen mit SplitMix64 (plattformunabhängig) und rechnet **jede Messreihe, die sie als Band zeigt, mit ihrem eigenen Kern neu**. Die Zahlen weichen deshalb ab (Tabelle „Vergleich mit der früheren Messreihe“ unten); die früheren Zahlen stehen dort nur aus der Rohdatei und sind nicht neu gerechnet.
- **Kern gegen die frühere Implementierung geprüft.** Auf den 6 früheren Instanzen (30 Kunden, Breite 100, `random.Random`, k = 5) liefert der Kern dieser Demo in allen 6 Instanzen dieselbe Schranke wie die frühere Messreihe (auf 4 Stellen). Die frühere Messreihe nimmt aus den besten 15 Routen des Pricings (unter den Preisen des Pricings) diejenigen, die auch unter den echten Dualpreisen negative reduzierte Kosten haben, und sucht nicht tiefer in der Liste; der Kern der Demo macht es ebenso (`tests/test_algorithm.py`).
- **Master im Handbeispiel.** Die Folge der Master-Werte 50, 40, 32, 32, 32, 30, 30 aus der Vorrechnung gilt für einen exakten Master mit Brüchen (nur in den Tests). Die App rechnet den Master mit HiGHS; bei entarteten Dualpreisen wählt HiGHS andere Dualpreise, die Spalten und die Rundenzahl können sich dann unterscheiden (die Schranke 30 nicht). Die App zeigt die Runden ihres HiGHS-Laufs.
- **Gegenprobe immer gerechnet.** Statt eines Knopfes „alle 79 Wege als Spalten“ steht die Gegenprobe immer da; sie rechnet in Millisekunden.
- **Regler für die Fensterbreite** von 40 bis 100 in Schritten von 20, nicht nur 40 und 100.
- **Überdeckung gegen Partitionierung neu gerechnet mit 45 Paaren** (drei Instanztypen mal drei Gedächtnisse mal 5 Instanzen). Die frühere Reihe hatte 47 Paare, darunter elementare Läufe; bei 30 Kunden war die elementare Rechnung dort meist nicht fertig, sie ist hier nicht enthalten.
- Die Orientierungswerte „Median der Labels des elementaren Pricings bei 10, 15, 20, 25 Kunden“ aus der Planung stehen nicht in dieser Demo (sie gehören zu einer späteren Demo der Reihe und sind hier nicht neu gerechnet).

## Modell

- **Handbeispiel:** Depot (0, 0) und 7 Kunden, ganze Zahlen. Entfernung, Fahrzeit und Kosten sind der Manhattan-Abstand, Bedienzeit 2, Kapazität 6, Rückkehr bis 38. Kunde 1 bis 7: Lage (−1, 2), (0, 3), (−3, −2), (−1, −2), (−2, −1), (2, 1), (3, 2); Last 1, 3, 3, 3, 1, 1, 2; Fenster für den Beginn der Bedienung [18, 28], [3, 16], [5, 15], [20, 28], [3, 12], [11, 21], [8, 20]. Früher ankommen heißt warten, später ankommen ist unzulässig.
- **Kundeninstanzen:** Depot in der Mitte eines Quadrats von 100 × 100, Fahrzeit gleich Entfernung, Bedienzeit 10, Horizont 300, Kapazität 70, Last 5 bis 25, Fensterbreite 40 bis 100 (Messreihen bis 200), Zufalls-Seed als Regler. Die Messreihen verwenden zusätzlich gruppierte Kunden und einen langen Horizont (500, Kapazität 120).
- **Master:** Überdeckung (jeder Kunde mindestens einmal) oder Partitionierung (genau einmal), Start mit den Einzelfahrten. Die Dualpreise sind die Schattenpreise der Kunden-Zeilen: Bei der Überdeckung sinkt der Master-Wert höchstens um den Dualpreis π(j), wenn Kunde j nicht bedient werden müsste; nur in der ersten Runde, in der der Master aus den Einzelfahrten besteht, sinkt er genau um π(j).
- **Pricing:** Labeling mit Last, Fenstern, Horizont und Dominanz; live elementar, in den Messreihen mit einem Gedächtnis aus den 5 nächsten Kunden (k = 5); nur der Vergleich von Überdeckung und Partitionierung rechnet mit k = 1, 5 und 8.
- Die Formeln stehen im Expander **📐 Mathematische Formulierung** der App mit Lesehilfe und Symboltabelle; der Expander **💬 In einfachen Worten** fasst das Verfahren ohne Formeln zusammen ([ausführlich erklärt](https://sebastianhanisch.net/pricing-dualpreise-erklaert.html)).

## Methodik

Je Runde: Master lösen, mit den Dualpreisen das Labeling rechnen (das offene Label mit der kleinsten Zeit wird über jeden Kunden verlängert; ein neues Label, das von einem lebenden Label desselben Kunden dominiert wird, wird verworfen, ein neues Label, das lebende dominiert, verdrängt sie), die besten neuen Spalten an den Master anhängen (bei den Kundeninstanzen live und in den Messreihen bis zu 15 je Runde, im Handbeispiel eine). Ende, wenn keine Route mit negativen reduzierten Kosten mehr gefunden wird; der letzte Master-Wert ist die Schranke. Die **Glättung** gibt dem Pricing α · (Preise, mit denen das Pricing der Vorrunde gerechnet hat) + (1 − α) · (aktuelle Dualpreise); findet es damit keine Spalte mit negativen reduzierten Kosten unter den echten Dualpreisen (ein **Fehlgriff**), wird sofort mit den echten Dualpreisen gerechnet. Gezählt werden **Runden, Pricing-Aufrufe und erzeugte Labels**, nicht Sekunden.

Fünf Experimente in der App: (1) von den Dualpreisen zu den Bogenlängen, Dijkstra gegen die Aufzählung aller einfachen Wege, (2) Labeling und Spaltenerzeugung am Handbeispiel mit Gegenprobe, (3) eine ganze Spaltenerzeugung live bis 20 Kunden, (4) Glättung der Dualpreise live und als Messreihe, (5) Bänder: negative Längen, Überdeckung gegen Partitionierung, Runden und Spalten.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen sind Messungen an festen Instanzen. Die Zahl-zu-Test-Tabelle am Ende dieses Abschnitts nennt für jede Zahl den Test.

**Handbeispiel** (7 Kunden, ganze Zahlen):

- Die Einzelfahrten Depot, Kunde, Depot kosten 6, 6, 10, 6, 6, 6, 10 (zwei mal der Abstand zum Depot 3, 3, 5, 3, 3, 3, 5), zusammen 50. Der Master der ersten Runde hat nur diese Spalten; seine Dualpreise sind genau diese Kosten: π = (6, 6, 10, 6, 6, 6, 10), Master-Wert 50.
- Mit den Bogenlängen d(i, j) − π(j) sind alle 7 Bögen vom Depot zu einem Kunden negativ (−3, −3, −5, −3, −3, −3, −5), 27 von 42 Bögen von Kunde zu Kunde (zusammen 34 von 49 Bögen) und 12 von 21 Kundenpaaren haben einen negativen Hin-und-zurück-Kreis i, j, i (am kleinsten bei den Kunden 3 und 4: 2 · 2 − 10 − 6 = −12). Dürfte ein Kunde mehrmals vorkommen und gäbe es keine Last- und Zeitgrenzen, gäbe es keinen kürzesten Weg, denn jede Runde im Kreis macht den Weg kürzer. Die endlosen Runden verhindert aber schon jede der beiden Bedingungen allein: die Regel „jeder Kunde höchstens einmal“ oder die Grenzen (mit ihnen wächst die Zeit bei jedem Halt um mindestens die Bedienzeit, und der Horizont ist begrenzt).
- **Dijkstra mit Entfernung plus Preis** (alle Längen nichtnegativ): Weg 1 mit Länge 12, und die Aufzählung aller 13 699 einfachen Wege (jeder Kunde höchstens einmal, ohne Last und Fenster) gibt denselben Weg und dieselbe Länge; es gehen keine Verbesserungen verloren.
- **Dijkstra mit Entfernung minus Dualpreis:** Kunde 3 wird zuerst mit Abstand −5 abgeschlossen (Gleichstandsregel: bei gleichem Abstand zuerst der Kunde mit der kleineren Nummer; Kunde 7 hat ebenfalls −5), danach gibt der Bogen von Kunde 4 zu Kunde 3 den Abstand −9 + (−8) = −17, aber Kunde 3 ist abgeschlossen und wird nicht mehr geändert. Es gehen 21 solcher Verbesserungen verloren. Dijkstra liefert Weg 3-4-5-1-7-6-2 mit Länge −24; die Aufzählung aller einfachen Wege findet 4-3-5-1-2-7-6 mit Länge −28. Dijkstra trifft den besten Weg also nicht. Beide Wege sind außerdem unzulässig: der von Dijkstra wegen der Last (7 > 6 bei Kunde 5), der beste einfache Weg ohne Grenzen wegen des Fensters (Ankunft 24 > Fensterende 15 bei Kunde 3). Dijkstra kennt Last und Fenster nicht. Die Zahlen −24 und 21 hängen an der Gleichstandsregel: Mit Kunde 7 zuerst fände Dijkstra den Weg 7-6-3-5-4-1-2 mit Länge −22 und 20 verpassten Verbesserungen; auch dann trifft er den besten einfachen Weg (−28) nicht.
- **Labeling** (elementar, mit Last, Fenstern, Dominanz) mit den Dualpreisen der ersten Runde: 56 erzeugte Labels, davon 20 sofort verworfen (neu und von einem lebenden Label dominiert, etwa das Label 0-2-3 vom Label 0-3: Kosten −5 ≤ −5, Zeit 5 ≤ 13, Last 3 ≤ 6, Menge {3} ⊆ {2, 3}), 0 später verdrängt, 36 am Ende übrig. Bester Wert −10, zum Beispiel mit dem Weg 2-7-6 (Fahrt 3 + 4 + 2 + 3 = 12, Dualpreise 6 + 10 + 6 = 22; Ankunft bei Kunde 2 zur Zeit 3, bei Kunde 7 zur Zeit 9, bei Kunde 6 zur Zeit 13, Last 3, 5, 6); zwei weitere Wege, 6-7-1 und 5-6-7-1, haben ebenfalls −10. Die Tiefensuche über alle zulässigen elementaren Wege zählt 79 zulässige Wege; 3 davon haben den besten Wert −10 (2-7-6, 6-7-1 und 5-6-7-1), 58 haben negative reduzierte Kosten. Das Labeling liefert 35 der 79 Wege (die übrigen hängen an dominierten Labels).
- **Spaltenerzeugung mit exaktem Master** (Brüche, Pricing = Labeling, je Runde die beste neue Spalte): 7 Runden, Master-Werte 50, 40, 32, 32, 32, 30, 30, neue Spalten 2-7-6, 5-3-1, 2-1, 3-4, 5-4-1, 6-7-1. **Schranke 30.** Endlösung: 2-7-6 mit Menge 1, 5-3-1, 3-4 und 5-4-1 mit je 1/2; jeder Kunde wird genau einmal überdeckt. Ein Master über alle 79 zulässigen Wege als Spalten gibt ebenfalls 30, und mit den Dualpreisen der letzten Runde hat keiner der 79 Wege negative reduzierte Kosten. Gebraucht wurden 6 neue Spalten zusätzlich zu den 7 Einzelfahrten, im Endmaster stehen also 13 der 79 Wege.
- Mit HiGHS als Master (Überdeckung und Partitionierung) ist die Schranke ebenfalls 30; die Zahl der Runden hängt von den gewählten Dualpreisen ab und steht hier nicht fest.

**Kundeninstanzen, eine ganze Spaltenerzeugung live** (elementares Pricing, Überdeckungs-Master; Schranke und Master-Wert der ersten Runde, die Summe der Einzelfahrten):

| Voreinstellung (Zufalls-Seed) | Master-Wert der ersten Runde | Schranke am Ende |
|---|---|---|
| 12 Kunden, Fensterbreite 100 (7) | 909,75 | 497,87 |
| 20 Kunden, Fensterbreite 40 (7) | 1 612,66 | 710,77 |
| 20 Kunden, Fensterbreite 100 (3) | 1 468,28 | 509,43 |

**Negative Bogenlängen, neu gerechnet** (30 Kunden, Fensterbreite 100, 6 Instanzen mit den Zufalls-Seeds 0 bis 5, Pricing mit Gedächtnis k = 5, Überdeckungs-Master; Mittel über die Instanzen; reine Rechnung an den Dualpreisen):

| Runde | Bögen Depot → Kunde negativ (Mittel) | Bögen Kunde → Kunde negativ (Mittel) | Kundenpaare mit negativem Kreis (Mittel) |
|---|---|---|---|
| erste (nur Einzelfahrten im Master) | 30,0 von 30 | 675,7 von 870 (77,7 %) | 435,0 von 435 |
| letzte (Ende der Spaltenerzeugung) | 4,8 von 30 | 149,2 von 870 (17,1 %) | 69,5 von 435 |

In der ersten Runde sind in allen 6 Instanzen alle 30 Bögen vom Depot und alle 435 Kundenpaare negativ.

**Runden und Spalten einer ganzen Spaltenerzeugung** (30 Kunden, Pricing mit Gedächtnis k = 5, Überdeckungs-Master, 6 Instanzen je Fensterbreite, Zufalls-Seeds 0 bis 5; die Spalten schließen die 30 Einzelfahrten vom Start ein):

| Fensterbreite | Runden (Median) | Runden (Minimum) | Runden (Maximum) | Spalten am Ende (Median) | Labels (Median) |
|---|---|---|---|---|---|
| 40 | 18,0 | 11 | 31 | 239,0 | 29 470,5 |
| 100 | 20,0 | 15 | 29 | 282,5 | 102 175 |
| 200 | 23,5 | 23 | 35 | 338,5 | 348 765,5 |

Der Median der Runden steigt von Breite 40 über 100 auf 200 von Stufe zu Stufe. Die Spanne innerhalb einer Zelle ist groß: bei Breite 40 reichen die Runden von 11 bis 31 bei einem Median von 18,0, bei Breite 100 von 15 bis 29 bei einem Median von 20,0; eine einzelne Instanz kann also deutlich vom Median abweichen. Ein Median aus 6 Instanzen ist das Mittel der beiden mittleren Werte, deshalb die Nachkommastelle. Wie viele zulässige Wege es bei 30 Kunden insgesamt gibt, ist nicht gezählt; die Aussage „nur ein Bruchteil der Wege wird gebraucht“ ist hier nur für das Handbeispiel belegt (6 neue Spalten zusätzlich zu den 7 Einzelfahrten, zusammen 13 von 79 Wegen).

**Glättung der Dualpreise** (einfache Glättung zur Vorrunde, Pricing mit Gedächtnis k = 5, Fensterbreite 100, Überdeckungs-Master, Zufalls-Seeds ab 0; dieselbe Schranke in allen Instanzen und allen α):

20 Kunden, 12 Instanzen:

| α | Runden (Mittel) | Runden (Median) | Runden (Maximum) | Pricing-Aufrufe (Mittel) | Fehlgriffe (Mittel) | weniger / gleich / mehr Runden als α = 0 |
|---|---|---|---|---|---|---|
| 0 | 13,7 | 14,0 | 17 | 13,7 | 0,0 | 0 / 12 / 0 |
| 0,5 | 13,7 | 13,5 | 22 | 17,5 | 3,8 | 5 / 2 / 5 |
| 0,8 | 18,4 | 18,0 | 28 | 23,6 | 5,2 | 1 / 0 / 11 |
| 0,9 | 23,2 | 24,0 | 30 | 32,2 | 9,0 | 0 / 1 / 11 |

30 Kunden, 6 Instanzen:

| α | Runden (Mittel) | Runden (Median) | Runden (Maximum) | Pricing-Aufrufe (Mittel) | Fehlgriffe (Mittel) | weniger / gleich / mehr Runden als α = 0 |
|---|---|---|---|---|---|---|
| 0 | 20,5 | 20,0 | 29 | 20,5 | 0,0 | 0 / 6 / 0 |
| 0,5 | 19,8 | 20,0 | 28 | 22,8 | 3,0 | 3 / 0 / 3 |
| 0,8 | 24,3 | 22,5 | 34 | 29,7 | 5,3 | 0 / 0 / 6 |
| 0,9 | 34,2 | 32,0 | 50 | 43,2 | 9,0 | 0 / 0 / 6 |

Bei α = 0,5 sind die mittleren Runden etwa gleich wie ohne Glättung (innerhalb von 10 %: 13,7 gegen 13,7 bei 20 Kunden, 19,8 gegen 20,5 bei 30 Kunden), die Pricing-Aufrufe sind im Mittel mehr (17,5 gegen 13,7 und 22,8 gegen 20,5). Bei α = 0,8 und bei α = 0,9 braucht die Glättung bei 20 Kunden in 11 von 12 Instanzen mehr Runden als ohne Glättung, bei 30 Kunden in 6 von 6 Instanzen. Gemessen ist nur diese einfache Glättung zur Vorrunde, nicht die Verfahren von Wentges oder du Merle u. a.; die Aussage gilt für diese Regel, diese Instanzen und diesen Master.

**Überdeckung gegen Partitionierung, neu gerechnet** (30 Kunden, je 5 Instanzen mit den Zufalls-Seeds 0 bis 4, Pricing mit Gedächtnis k = 1, 5, 8, Schranke der Spaltenerzeugung mit beiden Mastern):

| Instanztyp | Gedächtnis k | Paare | größte Abweichung der Schranke | Schranke Überdeckung (Mittel) |
|---|---|---|---|---|
| zufällig verteilt, Horizont 300, Kapazität 70, Breite 100 | 1 | 5 | 0,000000 | 760,61 |
| zufällig verteilt, Horizont 300, Kapazität 70, Breite 100 | 5 | 5 | 0,000000 | 786,13 |
| zufällig verteilt, Horizont 300, Kapazität 70, Breite 100 | 8 | 5 | 0,000000 | 787,17 |
| gruppiert um fünf Zentren, Horizont 300, Kapazität 70, Breite 100 | 1 | 5 | 0,000000 | 462,80 |
| gruppiert um fünf Zentren, Horizont 300, Kapazität 70, Breite 100 | 5 | 5 | 0,000000 | 473,01 |
| gruppiert um fünf Zentren, Horizont 300, Kapazität 70, Breite 100 | 8 | 5 | 0,000000 | 473,90 |
| zufällig verteilt, Horizont 500, Kapazität 120, Breite 100 | 1 | 5 | 0,000000 | 695,49 |
| zufällig verteilt, Horizont 500, Kapazität 120, Breite 100 | 5 | 5 | 0,000000 | 726,12 |
| zufällig verteilt, Horizont 500, Kapazität 120, Breite 100 | 8 | 5 | 0,000000 | 726,68 |

In allen 45 Paaren ist die Schranke mit Überdeckung und mit Partitionierung gleich (größte Abweichung unter 0,000001). Das gilt für **metrische Kosten** (Entfernungen); mit Festkosten je Fahrzeug oder Kosten ohne Dreiecksungleichung ist es nicht gemessen. Als mögliche Erklärung (Deutung, nicht gemessen): Bei metrischen Kosten macht das Auslassen eines Kunden aus einer Tour sie nicht teurer, und sie bleibt zulässig, deshalb hilft das Überdecken bei den gemessenen Instanzen nicht. Im Handbeispiel gilt dieselbe Schranke 30 mit beiden Mastern. Ein Test prüft außerdem an 30 kleinen Instanzen mit 6 Kunden, dass das LP über alle zulässigen Wege bei Überdeckung und Partitionierung denselben Wert gibt.

**Gegenprobe mit einer unabhängigen zweiten Implementierung.** Das Labeling gibt auf 180 Fällen (60 Instanzen mit 7 Kunden und je 3 Fensterbreiten, zufällige Dualpreise) denselben besten Wert wie die Tiefensuche über alle zulässigen elementaren Wege und liefert nur Routen, die auch die Tiefensuche findet (keine Abweichung; gibt es keinen zulässigen Weg, liefert auch das Labeling keinen); eine zweite Implementierung mit Mengen und Brüchen zählt auf 40 weiteren Instanzen und im Handbeispiel dieselben erzeugten und dominierten Labels.

### Vergleich mit der früheren Messreihe

Die frühere Messreihe der Planung benutzte andere Instanzen (Pythons `random.Random`, Zufalls-Seeds 0 bis 5 bzw. 0 bis 11) und einen anderen Kern. Ihre Zahlen stehen in `data/fruehere_messreihe.json` **aus den Rohdateien übernommen und nicht neu gerechnet**; die Spalte „diese Demo“ ist neu gerechnet.

| Größe | frühere Messreihe | diese Demo |
|---|---|---|
| Negative Bögen Kunde → Kunde, erste Runde (Mittel von 870, 30 Kunden) | 664,7 | 675,7 |
| Negative Bögen Kunde → Kunde, letzte Runde (Mittel von 870, 30 Kunden) | 159,7 | 149,2 |
| Runden, Median, Breite 40 / 100 / 200 (30 Kunden, k = 5) | 15,0 / 19,5 / 23,0 | 18,0 / 20,0 / 23,5 |
| Spalten am Ende, Median, Breite 40 / 100 / 200 | 227,5 / 279,5 / 342,0 | 239,0 / 282,5 / 338,5 |
| Glättung, Runden im Mittel, α = 0 / 0,5 / 0,8 / 0,9 (30 Kunden) | 19,2 / 19,2 / 22,2 / 30,0 | 20,5 / 19,8 / 24,3 / 34,2 |
| Glättung, Pricing-Aufrufe im Mittel, α = 0 / 0,5 / 0,8 / 0,9 (30 Kunden) | 19,2 / 23,0 / 28,0 / 38,5 | 20,5 / 22,8 / 29,7 / 43,2 |
| Glättung, Runden im Mittel, α = 0 / 0,5 / 0,8 / 0,9 (20 Kunden) | 14,3 / 13,8 / 18,5 / 21,0 | 13,7 / 13,7 / 18,4 / 23,2 |
| Glättung, Pricing-Aufrufe im Mittel, α = 0 / 0,5 / 0,8 / 0,9 (20 Kunden) | 14,3 / 16,5 / 23,5 / 30,2 | 13,7 / 17,5 / 23,6 / 32,2 |

Die Richtung der Befunde ist in beiden Reihen gleich (negative Bögen überwiegend in der ersten Runde, bei α = 0,5 etwa gleich viele Runden und mehr Pricing-Aufrufe, bei α ≥ 0,8 mehr Runden); die Zahlen unterscheiden sich um einige Prozent bis einige Runden, weil die Instanzen und die Wahl der Dualpreise im Master verschieden sind.

| Zahl | Test |
|---|---|
| Handbeispiel: Dualpreise, Master-Wert 50, negative Bögen (7 von 7, 27 von 42, zusammen 34 von 49) und Kreise | `tests/test_claims.py::test_hand_example_prices_and_negative_arcs`, `tests/test_algorithm.py` |
| Dijkstra mit Entfernung plus Preis, Aufzählung der 13 699 einfachen Wege | `tests/test_claims.py::test_hand_example_dijkstra`, `tests/test_oracle_pricing_dualpreise.py` |
| Dijkstra mit Entfernung minus Preis (−24, −28, 21 verpasste, Zulässigkeit; Gleichstandsregel: mit Kunde 7 zuerst −22 und 20 verpasste) | `tests/test_claims.py::test_hand_example_dijkstra`, `tests/test_algorithm.py` |
| Labeling: 56, 20, 0, 36, bester Weg −10, 79 Wege (3 davon mit −10), 35 geliefert, 58 negative | `tests/test_claims.py::test_hand_example_labeling`, `tests/test_oracle_pricing_dualpreise.py` (Tiefensuche, zweite Implementierung) |
| Spaltenerzeugung mit exaktem Master: 7 Runden, Master-Werte, Spalten, Schranke 30, Endlösung, 6 neue Spalten und 13 von 79 Wegen | `tests/test_oracle_pricing_dualpreise.py::test_exact_column_generation_at_the_hand_example_line_by_line` |
| Schranke 30 mit HiGHS, Überdeckung und Partitionierung | `tests/test_claims.py::test_hand_example_highs_bound` |
| Voreinstellungen der Kundeninstanzen (Master-Wert der ersten Runde, Schranke) | `tests/test_claims.py::test_live_presets_numbers` |
| Alle Messtabellen (negative Bögen, Runden, Glättung, Master) | `tests/test_claims.py::test_readme_tables_are_generated_from_the_data`, `tests/test_baender.py` (Zusammenfassung aus den Einzelwerten, Stichproben neu gerechnet) |
| Aussagen über die Messreihen („in allen 6 Instanzen“, „von Stufe zu Stufe“, Spanne der Runden 11 bis 31 bei Breite 40 und 15 bis 29 bei Breite 100, α = 0,5 und α ≥ 0,8, 45 Paare) | `tests/test_claims.py::test_statements_about_the_bands` |
| Bis zu 15 neue Spalten je Runde bei den Kundeninstanzen, eine im Handbeispiel; 12 Instanzen bei der Glättung mit 20 Kunden, 6 bei 30 Kunden | `tests/test_claims.py::test_columns_per_round_and_instance_counts_are_stated_as_measured` |
| Gedächtnis k der Messreihen: k = 5, nur der Vergleich der Master mit k = 1, 5 und 8 | `tests/test_claims.py::test_memory_k_of_the_bands_is_stated_as_measured` |
| Endlose Runden verhindert jede der Bedingungen allein (Grenzen oder „höchstens einmal“) | `tests/test_claims.py::test_endless_rounds_are_prevented_by_either_condition_alone` |
| Dualpreis = Einsparung nur in der ersten Runde, sonst höchstens π(j) | `tests/test_claims.py::test_dual_price_is_the_saving_only_in_the_first_round` |
| Glättung: Zentrum = Preise der letzten Suche der Vorrunde | `tests/test_claims.py::test_smoothing_centre_is_the_price_vector_of_the_last_search_of_the_previous_round` |
| 30 Instanzen mit 6 Kunden: Überdeckung gleich Partitionierung, 180 Fälle, zweite Implementierung | `tests/test_oracle_pricing_dualpreise.py` |
| Vergleichstabelle mit der früheren Messreihe | `tests/test_claims.py::test_comparison_table_follows_from_the_data` (die früheren Zahlen nur aus der Datei, nicht neu gerechnet) |
| Gleiche Schranke wie die frühere Implementierung auf den 6 früheren Instanzen | `tests/test_claims.py::test_cross_check_with_the_earlier_implementation` |

## Ehrliche Grenzen

Annahmen, Grenzen und bekannte Probleme (derselbe Wortlaut wie im Expander **⚠️ Annahmen, Grenzen und bekannte Probleme** der App):

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

## Literatur

Prüfstand für alle Einträge: nur Abstract oder Suchtreffer gesehen, **kein Volltext gelesen**; keine Zahl dieser Demo stammt aus der Literatur.

- Dantzig, Wolfe (1960): *Decomposition Principle for Linear Programs*, Operations Research 8(1), S. 101–111 (Spaltenerzeugung am LP).
- Gilmore, Gomory (1961): Operations Research 9(6), S. 849–859 (erste Anwendung am Cutting Stock; Pricing = Rucksack).
- Desrochers, Soumis (1988): *A generalized permanent labelling algorithm for the shortest path problem with time windows*, INFOR 26, S. 191–212 (Seitenzahl in den Quellen uneinheitlich; Label-Setting mit Zeitfenstern).
- Lübbecke, Desrosiers (2005): *Selected Topics in Column Generation*, Operations Research 53(6), S. 1007–1023 (duale Sicht, Entartung, Stabilisierung).
- du Merle, Villeneuve, Desrosiers, Hansen (1999): Discrete Mathematics 194(1–3), S. 229–237 (stabilisierte Spaltenerzeugung, Strafen im Dualraum).
- Irnich, Desaulniers (2005): *Shortest Path Problems with Resource Constraints*, in: Column Generation, Springer, S. 33–65 (Standardreferenz; nur das Zitat gesehen, der Inhalt ist nicht geprüft).
- Die einfache Glättung (nach Neame) und das Verfahren von Wentges sind aus dem Gedächtnis genannt und **nicht geprüft**.

## Abgrenzung zu anderen Demos

- [column-generation-demo](https://github.com/sebastian-hanisch/column-generation-demo) erklärt Master, Dualpreise und die Rundungslücke am Cutting Stock mit einem Rucksack als Pricing; hier steht nur, was am Pricing mit Last und Zeitfenstern neu ist.
- [mcf-column-generation-demo](https://github.com/sebastian-hanisch/mcf-column-generation-demo) formuliert das Pricing als Dijkstra mit nichtnegativen Längen (Kosten plus Preis) im Netzwerkfluss; hier sind die Längen Entfernung minus Dualpreis, und Dijkstra reicht nicht mehr.
- [weg-mit-grenzen-demo](https://github.com/sebastian-hanisch/weg-mit-grenzen-demo), [dominanz-labels-demo](https://github.com/sebastian-hanisch/dominanz-labels-demo), [zeitfenster-labeling-demo](https://github.com/sebastian-hanisch/zeitfenster-labeling-demo) und [mehrere-grenzen-demo](https://github.com/sebastian-hanisch/mehrere-grenzen-demo) erklären das Labeling mit Grenze, Dominanz, Zeitfenstern und mehreren Grenzen; diese Demo wendet es auf Dualpreise an.
- [crew-pairing-demo](https://github.com/sebastian-hanisch/crew-pairing-demo) verwendet ein solches Pricing in einer Fall-Demo; Zahlen von dort werden nicht übernommen.
- [hub-labeling-demo](https://github.com/sebastian-hanisch/hub-labeling-demo) meint mit „Label“ etwas anderes: Einträge in Listen, die für schnelle Abfragen kürzester Wege zusammengeführt werden. Hier ist ein Label ein Teilweg mit Zeit, reduzierten Kosten, Last und Gedächtnis.

## Tests

200 Tests (`pytest --collect-only -q tests`), alle im Ordner `tests/`:

- **Handrechnung:** `tests/conftest.py` enthält das Handbeispiel von Hand aus der Tabelle der Aufgabe; die erwarteten Werte stehen als Rechnung da (`tests/test_algorithm.py`), je Einheit des Labelings (Verlängerung, Rückkehr, Dominanz, Gedächtnis), Dijkstra, Master und Spaltenerzeugung.
- **Orakel** (`tests/test_oracle_pricing_dualpreise.py`): Labeling gegen die Tiefensuche über alle zulässigen elementaren Wege (180 Fälle) und, für ein Gedächtnis kleiner als die Kundenzahl, gegen die Tiefensuche mit der Gedächtnisregel auf dem ganzen Weg; zweite Implementierung des Labelings mit Mengen und Brüchen (`tests/referenz.py`); Master gegen einen exakten Master mit Brüchen und die Aufzählung aller Wege als Spalten (Dualitätszertifikat); exakte Spaltenerzeugung Zeile für Zeile; Dijkstra gegen networkx und die Aufzählung aller einfachen Wege.
- **Eigenschaften** (`tests/test_eigenschaften_pricing_dualpreise.py`): Master-Wert fällt nie, alle Spalten zulässig, mehr Spalten, breitere Fenster und größere Kapazität verschlechtern die Schranke nie, größeres Gedächtnis gibt höhere oder gleiche Schranke, Umnummerieren und Glättung ändern die Schranke nicht, gleicher Zufalls-Seed gleiche Ausgabe auch in einem zweiten Prozess mit anderem Hash-Seed.
- **Randfälle** (`tests/test_edge_cases.py`): ein und zwei Kunden, alle Dualpreise null, Kunden, die sich nicht kombinieren lassen, Kapazität unter fast jeder Last, zwei Kunden am selben Ort, Grenzen inklusive.
- **Aussagen** (`tests/test_claims.py`, `tests/test_baender.py`, `tests/test_verdicts.py`): jede Zahl dieser README, die Messreihen (Zusammenfassungen aus den Einzelwerten, Stichproben neu gerechnet), jedes Verdikt mit seinen Schwellen, je Voreinstellung die erwartete Verdikt-Zeile.
- **Oberfläche:** AppTest für Standard, jeden Knopf, jeden Regler am Minimum und Maximum (einzeln und alle zugleich), jede Voreinstellung, Permalink, die Rundenregler und den Längentyp; Layout, Footer und Laufzeit-Importe.
- Ein Test am Regler-Maximum (20 Kunden, Fensterbreite 100) hat nur eine Label-Obergrenze als Schutz, keine Zeit-Assertion.

Die Laufzeit der Suite hängt von der Auslastung der Maschine ab und steht deshalb hier nicht fest. Runden und Pricing-Aufrufe hängen vom LP-Löser ab; die Tests prüfen deshalb Schranken exakt und Runden nur mit Toleranz.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App: Kopf, Erklärung, Ergebnis, fünf Experimente, Grenzen, Formeln |
| `data/baender_negativ.json`, `data/baender_runden.json`, `data/baender_glaettung.json`, `data/baender_master.json` | feste Messreihen, neu gerechnet mit dem Kern der Demo (Einzelwerte je Instanz, Quelle je Zeile, Python- und scipy-Version) |
| `data/fruehere_messreihe.json` | Zahlen der früheren Messreihe aus den Rohdateien (nicht neu gerechnet) |
| `pdp_algorithm.py` | Kern: Verlängerung, Dominanz, Labeling, Dijkstra-Vorführung, Aufzählungen, Prüfer |
| `pdp_colgen.py` | Spaltenerzeugung mit optionaler Glättung der Dualpreise |
| `pdp_constants.py` | Regler-Grenzen, feste Annahmen, Farben, Voreinstellungen |
| `pdp_evaluation.py` | Analysen, Verdikte als reine Funktionen, Tabellenzeilen, Lader der Messreihen |
| `pdp_layout.py` | Fester Kopf (Stylesheet) |
| `pdp_master.py` | Master (LP mit scipy/HiGHS): Überdeckung und Partitionierung, Dualpreise |
| `pdp_presets.py` | Permalink (Begrenzen, Einrasten), Schnellstart in der Seitenleiste, aktive Voreinstellung hervorgehoben, Zufalls-Seed-Knopf |
| `pdp_rng.py` | SplitMix64 (plattformunabhängiger Zufall) |
| `pdp_scenario.py` | Handbeispiel und Instanzgenerator der Kundeninstanzen |
| `pdp_texts.py` | Annahmen-Text (App und README zeigen denselben Wortlaut) |
| `pdp_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `requirements.txt`, `requirements-dev.txt` | Laufzeit-Bibliotheken (ungepinnt); Entwicklung mit pytest und networkx |
| `tools/messreihen.py` | erzeugt die vier Messreihen-Dateien mit dem Kern der Demo |
| `tools/readme_tabellen.py` | druckt die Tabellen der README aus den Messreihen |
| `tests/` | siehe Abschnitt Tests |

## Bewusst nicht umgesetzt

- **Elementarität und Kreise im Pricing:** Die Live-Rechnung ist elementar, die Messreihen verwenden ein Gedächtnis aus 5 Kunden (beim Vergleich der Master auch 1 und 8); was die Elementarität kostet und wie Kreise verhindert werden, zeigt diese Demo nicht.
- **Stabilisierung nach Wentges oder du Merle**, Branch-and-Price und das Auffinden ganzzahliger Lösungen: nur die einfache Glättung zur Vorrunde und die LP-Schranke.
- **Festkosten je Fahrzeug und Kosten ohne Dreiecksungleichung** beim Vergleich von Überdeckung und Partitionierung; **mehrere begrenzte Größen** über Zeit und Last hinaus.
- **Mehr als 20 Kunden live**, **Sekunden als Messgröße** und **ein PDF-Export** fehlen. Keine Aussagen über öffentliche Benchmarks.

## Lokal ausführen

Die Streamlit-Cloud-Einstellung für die Python-Version ist im Betrieb zu prüfen; die CI testet mit Python 3.12, lokal gemessen wurde mit 3.14. <!-- lint-ok: dezimalpunkt -->

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, pandas, numpy und scipy.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Ressourcenwege: von der Grenze zur Verfahrenswahl](https://sebastianhanisch.net/konzepte-ressourcenwege.html).
