"""Konstanten: Regler-Grenzen, feste Annahmen, Farben und Voreinstellungen."""

# --- Annahmen der Kundeninstanzen (Solomon-artig, selbst erzeugt) -----------------------------------------------------------------------------
HORIZONT, KAPAZITAET, BEDIENZEIT = 300, 70, 10   # Rückkehr zum Depot bis 300, Kapazität 70, Bedienzeit 10 je Kunde
GRID = 100.0                                     # Kantenlänge des Quadrats

# --- Regler ---------------------------------------------------------------------------------------------------------------------------------
# Komplexität am Regler-Maximum: Das elementare Pricing (Gedächtnis = alle Kunden) erzeugt bei n = 20 und Breite 100 je Pricing-Aufruf einige 10 000 Labels;
# eine Spaltenerzeugung ruft es etwa 15- bis 25-mal auf. Deshalb gilt LABEL_CAP (Summe der Labels einer ganzen Rechnung).
N_MIN, N_MAX, DEFAULT_N = 5, 20, 12                 # Zahl der Kunden (Live-Rechnung nur bis 20; 30 Kunden sind feste Messreihen)
BREITE_MIN, BREITE_MAX, BREITE_STEP, DEFAULT_BREITE = 40, 100, 20, 100   # Fensterbreite
SEED_MAX, DEFAULT_SEED = 999999, 7
ALPHA_OPTIONEN = (0, 50, 80, 90)                    # Glättung α in Prozent (0 = aus)
DEFAULT_ALPHA = 0
LABEL_CAP = 3_000_000                               # Abbruch einer Rechnung nach so vielen erzeugten Labels (Schutz vor Hängern)
MAX_RUNDEN = 400                                    # Sicherung der Schleife
SPALTEN_JE_RUNDE = 15                               # neue Spalten je Runde bei den Kundeninstanzen (wie in den Messreihen)

# --- feste Messreihen -----------------------------------------------------------------------------------------------------------------------
SWEEP_SEEDS = tuple(range(12))                      # Zufalls-Seeds 0 bis 11 (n = 20); die Reihen mit n = 30 nehmen die Seeds 0 bis 5
BAND_N30 = 30
BAND_K = 5                                          # Gedächtnis der Messreihen (ng-Routen, k = 5)
BAND_BREITEN = (40, 100, 200)
SCHWELLE_GLEICH = 0.10                              # Verdikt „etwa gleich viele Runden“: mittlere Rundenzahl höchstens 10 % von der ohne Glättung entfernt

# --- Darstellung ----------------------------------------------------------------------------------------------------------------------------
COLOR_BEST = "#2F6B65"
COLOR_BAD = "#c0392b"
COLOR_DIJKSTRA = "#d98a2b"
COLOR_NODE = "#4c78a8"
COLOR_OTHER = "rgba(150,150,150,0.55)"
COLOR_LINE = "#4c78a8"

# --- Voreinstellungen (Schnellstart) -----------------------------------------------------------------------------------------------------
# Jede Voreinstellung nennt alle Regler: n, Fensterbreite, Zufalls-Seed der Kundeninstanz, Glättung α in Prozent, Partitionierungs-Master (sonst Überdeckung).
PRESETS = {
    "Standard: Handbeispiel und 12 Kunden": {"n": DEFAULT_N, "breite": DEFAULT_BREITE, "seed": DEFAULT_SEED, "alpha": 0, "partition": False},
    "Handbeispiel mit Glättung α = 0,8": {"n": DEFAULT_N, "breite": DEFAULT_BREITE, "seed": DEFAULT_SEED, "alpha": 80, "partition": False},
    "Partitionierungs-Master, 15 Kunden": {"n": 15, "breite": DEFAULT_BREITE, "seed": DEFAULT_SEED, "alpha": 0, "partition": True},
    "20 Kunden, enge Fenster (40)": {"n": 20, "breite": 40, "seed": DEFAULT_SEED, "alpha": 0, "partition": False},
    "20 Kunden, weite Fenster (100)": {"n": 20, "breite": 100, "seed": 3, "alpha": 0, "partition": False},
}
PRESET_HELP = {
    "Standard: Handbeispiel und 12 Kunden": "Das Handbeispiel mit 7 Kunden (feste Zahlen, von Hand nachrechenbar) und eine Kundeninstanz mit 12 Kunden und Fensterbreite 100; Master: Überdeckung, keine Glättung.",
    "Handbeispiel mit Glättung α = 0,8": "Dasselbe, aber das Pricing bekommt geglättete Dualpreise (80 % der Vorrunde, 20 % der aktuellen Dualpreise): Experiment 4 vergleicht die Läufe mit und ohne Glättung.",
    "Partitionierungs-Master, 15 Kunden": "Der Master verlangt, dass jeder Kunde genau einmal bedient wird, statt mindestens einmal (Überdeckung); Kundeninstanz mit 15 Kunden.",
    "20 Kunden, enge Fenster (40)": "Die größte Kundeninstanz der Live-Rechnung mit engen Zeitfenstern (Breite 40).",
    "20 Kunden, weite Fenster (100)": "Dieselbe Kundenzahl mit weiten Zeitfenstern (Breite 100) und einem anderen Zufalls-Seed: Das Pricing hat mehr zulässige Wege zu prüfen als bei engen Fenstern.",
}
