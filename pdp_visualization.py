"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben.

Beschriftungen im Netz sind `add_annotation`-Aufrufe (mit Hintergrund), keine Text-Spuren (DEMO-PLAYBOOK §3)."""

import plotly.graph_objects as go

import pdp_constants as C
from pdp_scenario import Instanz

HINTERGRUND = "rgba(255,255,255,0.88)"


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=360, legend=True):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)", showlegend=legend, legend=dict(orientation="h", y=-0.25))
    return lock_axes(fig)


def _zahl(x) -> str:
    return str(int(round(x))) if abs(x - round(x)) < 1e-9 else f"{x:.1f}".replace(".", ",")


def build_handnetz(inst: Instanz, weg_dijkstra=(), weg_bester=()):
    """Das Handbeispiel als Lageplan: Depot (Raute) und Kunden mit Last und Zeitfenster. Orange gestrichelt: der Weg von Dijkstra, grün: der beste Weg des Labelings.

    Die Verbindungen sind Luftlinien zwischen den Orten; gerechnet wird mit dem Manhattan-Abstand."""
    fig = go.Figure()
    for weg, farbe, strich, name in ((weg_dijkstra, C.COLOR_DIJKSTRA, "dash", "Weg von Dijkstra"), (weg_bester, C.COLOR_BEST, "solid", "bester Weg des Labelings")):
        if not weg:
            continue
        folge = (0,) + tuple(weg) + (0,)
        fig.add_trace(go.Scatter(x=[inst.pts[i][0] for i in folge], y=[inst.pts[i][1] for i in folge], mode="lines", line=dict(color=farbe, width=6 if strich == "dash" else 3, dash=strich),
                                 name=name, hoverinfo="skip"))
    xs = [inst.pts[i][0] for i in range(1, inst.n + 1)]
    ys = [inst.pts[i][1] for i in range(1, inst.n + 1)]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text", text=[str(i) for i in range(1, inst.n + 1)], textfont=dict(color="white", size=13), marker=dict(size=26, color=C.COLOR_NODE,
                             line=dict(color="white", width=2)), showlegend=False, hovertemplate="Kunde %{text}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[inst.pts[0][0]], y=[inst.pts[0][1]], mode="markers+text", text=["D"], textfont=dict(color="white", size=13), marker=dict(size=30, color="#444", symbol="diamond",
                             line=dict(color="white", width=2)), showlegend=False, hovertemplate="Depot<extra></extra>"))
    for i in range(1, inst.n + 1):
        fig.add_annotation(x=inst.pts[i][0], y=inst.pts[i][1], text=f"Last {_zahl(inst.dem[i])}<br>[{_zahl(inst.ready[i])}, {_zahl(inst.due[i])}]", showarrow=False, yshift=-30, font=dict(size=10),
                           bgcolor=HINTERGRUND, borderpad=1)
    xs_all = [p[0] for p in inst.pts]
    ys_all = [p[1] for p in inst.pts]
    fig.update_xaxes(range=[min(xs_all) - 1.5, max(xs_all) + 1.5], showgrid=False, zeroline=False, showticklabels=False)
    fig.update_yaxes(range=[min(ys_all) - 1.8, max(ys_all) + 1.2], showgrid=False, zeroline=False, showticklabels=False)
    return _base(fig, height=420)


def build_bogenlaengen(laengen, n: int):
    """Tabelle der Bogenlängen als Wärmekarte: Zeile = von (0 = Depot), Spalte = nach (Kunde). Negative Längen rot, positive grün, Null weiß; die Diagonale bleibt leer."""
    z = [[float("nan") if v is None else v for v in zeile] for zeile in laengen]
    text = [["" if v is None else _zahl(v) for v in zeile] for zeile in laengen]
    grenze = max(1.0, max(abs(v) for zeile in laengen for v in zeile if v is not None))
    fig = go.Figure(go.Heatmap(z=z, x=[f"nach {j}" for j in range(1, n + 1)], y=["von Depot"] + [f"von {i}" for i in range(1, n + 1)], text=text, texttemplate="%{text}", zmid=0, zmin=-grenze, zmax=grenze,
                               colorscale=[[0, C.COLOR_BAD], [0.5, "#ffffff"], [1, C.COLOR_BEST]], showscale=False, xgap=2, ygap=2, hovertemplate="%{y} %{x}: Länge %{text}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(side="top")
    return _base(fig, height=380, legend=False)


def build_kurve(serien, titel_y="Master-Wert"):
    """Linien über die Runden: `serien` = Liste (Name, Werte je Runde ab Runde 1)."""
    fig = go.Figure()
    farben = [C.COLOR_LINE, C.COLOR_DIJKSTRA, C.COLOR_BEST]
    for idx, (name, werte) in enumerate(serien):
        fig.add_trace(go.Scatter(x=list(range(1, len(werte) + 1)), y=list(werte), mode="lines+markers", name=name, line=dict(color=farben[idx % 3], width=3), marker=dict(size=7)))
    fig.update_xaxes(title="Runde", dtick=1 if max(len(w) for _, w in serien) <= 12 else None)
    fig.update_yaxes(title=titel_y)
    return _base(fig, height=320, legend=len(serien) > 1)


def build_balken(kategorien, serien, titel_y="", titel_x="", stapel=False):
    """Gruppierte (oder gestapelte) Balken: `serien` = Liste (Name, Werte je Kategorie)."""
    fig = go.Figure()
    farben = [C.COLOR_LINE, C.COLOR_DIJKSTRA, C.COLOR_BEST, C.COLOR_BAD]
    for idx, (name, werte) in enumerate(serien):
        fig.add_trace(go.Bar(x=[str(k) for k in kategorien], y=list(werte), name=name, marker_color=farben[idx % 4]))
    fig.update_layout(barmode="stack" if stapel else "group")
    fig.update_xaxes(title=titel_x, type="category")
    fig.update_yaxes(title=titel_y)
    return _base(fig, height=320, legend=len(serien) > 1)
