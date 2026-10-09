"""Dashboard Dash + Plotly : Landes de Gascogne vs Alpes-Maritimes face aux incendies.

Lancement (depuis le dossier projet/) : python app_dash/app.py  puis http://127.0.0.1:8050
"""
import sys
from pathlib import Path

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dash_table, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from common import (ANNEE_MAX, ANNEE_MIN, COULEUR_DEP, COULEUR_STATION, COULEUR_STATUT,  # noqa: E402
                    COULEUR_TERRITOIRE, DIVERGENTE, GRID, INK, INK_2, LIMITES, MUTED, PROBLEMATIQUE,
                    PUBLIC, SOURCES, TERRITOIRES, TITRE, kpis, load, pct, recommandations, tuiles)

D = load()
K = kpis(D)
CENTRES = {"Landes de Gascogne": dict(lat=44.45, lon=-0.75, zoom=6.9),
           "Alpes-Maritimes": dict(lat=43.95, lon=7.15, zoom=8.1)}
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def style(fig, height=340, legend=True, unified=True):
    """Habillage commun : grille discrète, pas de bruit, légende en haut."""
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=40, b=28), font=dict(family=FONT, color=INK_2, size=13),
        plot_bgcolor="white", paper_bgcolor="white", separators=", ",
        hovermode="x unified" if unified else "closest", showlegend=legend,
        legend=dict(orientation="h", y=1.14, x=0, title=None), hoverlabel=dict(font_family=FONT))
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont_color=MUTED, title_font_color=MUTED)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont_color=MUTED, title_font_color=MUTED)
    return fig


def fond_carte(fig, territoire, height=460):
    c = CENTRES[territoire]
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=c["lat"], lon=c["lon"]), zoom=c["zoom"]),
                      height=height, margin=dict(l=0, r=0, t=0, b=0), font=dict(family=FONT),
                      legend=dict(orientation="h", y=.01, x=.01, bgcolor="rgba(255,255,255,.9)", title=None))
    return fig


# ---------- 1. Climat ----------

def fig_j30():
    c = D["climat"].dropna(subset=["j30"])
    fig = go.Figure()
    for st, col in COULEUR_STATION.items():
        s = c[c.station == st]
        fig.add_scatter(x=s.annee, y=s.j30, mode="markers", marker=dict(color=col, size=5, opacity=.35),
                        name=st, legendgroup=st, showlegend=False,
                        hovertemplate=f"{st} : %{{y:.0f}} j<extra></extra>")
        fig.add_scatter(x=s.annee, y=s.j30_moy10, mode="lines", line=dict(color=col, width=2.5),
                        name=st, legendgroup=st,
                        hovertemplate=f"{st}, moyenne 10 ans : %{{y:.1f}} j<extra></extra>")
    fig.add_vrect(x0=1961, x1=1990, fillcolor="#f0efec", opacity=.6, line_width=0,
                  annotation_text="Normale 1961-1990", annotation_position="top left",
                  annotation_font_color=MUTED)
    fig.update_yaxes(title="Jours ≥ 30 °C (juin-août)")
    return style(fig)


def fig_stripes():
    c = D["climat"].dropna(subset=["anomalie"])
    piv = c.pivot(index="station", columns="annee", values="anomalie").reindex(list(COULEUR_STATION))
    fig = go.Figure(go.Heatmap(
        z=piv.values, x=piv.columns, y=piv.index, zmid=0, zmin=-2.5, zmax=2.5, ygap=3,
        colorscale=[[i / 6, h] for i, h in enumerate(DIVERGENTE)],
        colorbar=dict(title="Écart (°C)", thickness=10, len=.9),
        hovertemplate="%{y}, %{x} : %{z:+.1f} °C vs 1961-1990<extra></extra>"))
    fig.update_yaxes(autorange="reversed", gridcolor="white")
    return style(fig, height=210, legend=False, unified=False)


# ---------- 2. Incendies ----------

def fig_surface(an_min, an_max, log):
    f = D["feux_an"][D["feux_an"].annee.between(an_min, an_max)]
    fig = px.bar(f, x="annee", y="surface_ha", color="territoire", barmode="group",
                 color_discrete_map=COULEUR_TERRITOIRE, category_orders={"territoire": TERRITOIRES},
                 custom_data=["nb_feux", "grands_feux", "plus_gros_feu_ha"],
                 labels={"annee": "", "surface_ha": "Surface brûlée (ha)"}, log_y=log)
    fig.update_traces(marker_line_width=0, hovertemplate=(
        "%{fullData.name} : %{y:,.0f} ha · %{customdata[0]} feux · %{customdata[1]} ≥ 100 ha · "
        "plus gros : %{customdata[2]:,.0f} ha<extra></extra>"))
    fig.update_layout(bargap=.25, bargroupgap=.08)
    if an_min <= 2022 <= an_max and not log:
        fig.add_annotation(x=2022, y=K["ha_lg_2022"], text="2022 : Landiras, La Teste-de-Buch",
                           showarrow=True, arrowcolor=MUTED, ax=-110, ay=10, font_color=INK)
    return style(fig)


def fig_nature(col, titre, hors_2022):
    n = D["nature"][D["nature"].variante == ("hors 2022" if hors_2022 else "toutes années")]
    fig = px.bar(n, x="periode", y=col, color="territoire", barmode="group", text_auto=".1f",
                 color_discrete_map=COULEUR_TERRITOIRE, category_orders={"territoire": TERRITOIRES},
                 labels={"periode": "", col: titre})
    fig.update_traces(marker_line_width=0, textposition="outside", textfont_color=INK_2, cliponaxis=False,
                      hovertemplate="%{fullData.name}, %{x} : %{y:.1f}<extra></extra>")
    fig.update_layout(bargap=.35)
    fig.update_yaxes(title=None, range=[0, n[col].max() * 1.18])
    return style(fig, height=300, unified=False)


def fig_carte_feux(territoire, an_min, an_max, couches):
    f = D["feux"]
    f = f[(f.territoire == territoire) & f.annee.between(an_min, an_max)].dropna(subset=["lat"])
    com = f.groupby(["commune", "lat", "lon"]).agg(surface_ha=("surface_ha", "sum"),
                                                   nb=("surface_ha", "size")).reset_index()
    fig = go.Figure()
    fig.add_scattermap(
        lat=com.lat, lon=com.lon, mode="markers", name="Surface brûlée par commune",
        marker=dict(size=np.clip(np.sqrt(com.surface_ha) * 1.2, 4, 45), color=COULEUR_TERRITOIRE[territoire],
                    opacity=.55),
        customdata=np.stack([com.commune, com.surface_ha, com.nb], axis=-1),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:,.0f} ha, %{customdata[2]} feux<extra></extra>")
    if "casernes" in couches:
        c = D["casernes"][D["casernes"].territoire == territoire]
        fig.add_scattermap(lat=c.lat, lon=c.lon, mode="markers", name="Centre de secours (OSM)",
                           marker=dict(size=6, color=INK), text=c.nom,
                           hovertemplate="%{text}<extra>Centre de secours</extra>")
    return fond_carte(fig, territoire)


def fig_correlation():
    c = D["climat"]
    ete = pd.concat([
        c[c.station == "Nice"].assign(territoire="Alpes-Maritimes"),
        c[c.station.isin(["Bordeaux-Mérignac", "Mont-de-Marsan"])].assign(territoire="Landes de Gascogne"),
    ]).groupby(["territoire", "annee"]).j30.mean().reset_index()
    j = D["feux_an"].merge(ete, on=["territoire", "annee"])
    fig = px.scatter(j, x="j30", y="surface_ha", color="territoire", log_y=True, text="annee",
                     color_discrete_map=COULEUR_TERRITOIRE, category_orders={"territoire": TERRITOIRES},
                     labels={"j30": "Jours ≥ 30 °C dans l'été", "surface_ha": "Surface brûlée (ha, échelle log)"})
    fig.update_traces(marker=dict(size=10, line=dict(color="white", width=2)), textposition="top center",
                      textfont=dict(size=10, color=MUTED),
                      hovertemplate="%{text} : %{x:.0f} j ≥ 30 °C, %{y:,.0f} ha<extra>%{fullData.name}</extra>")
    return style(fig, height=420, unified=False)


# ---------- 3. Prévention ----------

def fig_prevention_barres():
    p = D["prevention"]
    p = p[p.statut != "Non classée à risque"].assign(departement=lambda x: x.dep.map(
        {"06": "Alpes-Maritimes", "33": "Gironde", "40": "Landes"}))
    n = p.groupby(["departement", "statut"]).size().reset_index(name="communes")
    ordre = [s for s in COULEUR_STATUT if s != "Non classée à risque"]
    fig = px.bar(n, y="departement", x="communes", color="statut", orientation="h",
                 color_discrete_map=COULEUR_STATUT,
                 category_orders={"statut": ordre, "departement": ["Landes", "Gironde", "Alpes-Maritimes"]},
                 labels={"departement": "", "communes": "Communes à risque feu de forêt"})
    fig.update_traces(marker_line_color="white", marker_line_width=2,
                      hovertemplate="%{y} : %{x} communes<extra>%{fullData.name}</extra>")
    return style(fig, height=330, unified=False).update_layout(
        legend=dict(orientation="h", y=-0.28, x=0, yanchor="top"), margin=dict(t=10, b=10))


def fig_carte_prevention(territoire):
    p = D["prevention"][D["prevention"].territoire == territoire]
    fig = go.Figure()
    for statut, col in COULEUR_STATUT.items():
        s = p[p.statut == statut]
        if s.empty:
            continue
        fig.add_scattermap(
            lat=s.lat, lon=s.lon, mode="markers", name=statut,
            marker=dict(size=np.clip(4 + np.sqrt(s.surface_brulee_ha) * .9, 4, 40), color=col,
                        opacity=.85 if statut != "Non classée à risque" else .5),
            customdata=np.stack([s.commune, s.surface_brulee_ha], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b><br>" + statut +
                          "<br>Surface brûlée 2006-2025 : %{customdata[1]:,.0f} ha<extra></extra>")
    return fond_carte(fig, territoire, height=480)


# ---------- 4. Moyens ----------

def fig_budget(col, titre, annot=True):
    b = D["budget"]
    fig = px.line(b, x="annee", y=col, color="departement", markers=True,
                  color_discrete_map=COULEUR_DEP, labels={"annee": "", col: "€ par habitant"})
    fig.update_traces(line_width=2.5, marker_size=7,
                      hovertemplate="%{fullData.name} : %{y:.1f} €/hab<extra></extra>")
    fig.add_vline(x=2022, line_color=MUTED, line_width=1)
    if annot:
        fig.add_annotation(x=2022, y=1.0, yref="paper", text=" 2022", showarrow=False,
                           font_color=MUTED, xanchor="left", yanchor="top")
    return style(fig, height=320)


def fig_pompiers():
    p = D["pompiers"]
    fig = px.bar(p, x="departement", y="pompiers_1000km2", color="departement", text_auto=".0f",
                 color_discrete_map=COULEUR_DEP,
                 category_orders={"departement": ["Landes", "Gironde", "Alpes-Maritimes"]},
                 custom_data=["pompiers", "pompiers_100k_hab", "part_volontaires"],
                 labels={"departement": "", "pompiers_1000km2": "Sapeurs-pompiers pour 1 000 km²"})
    fig.update_traces(marker_line_width=0, textposition="outside", textfont_color=INK_2, cliponaxis=False,
                      hovertemplate=(
                          "<b>%{x}</b> : %{y:.0f} pour 1 000 km²<br>%{customdata[0]:,} pompiers · "
                          "%{customdata[1]:.0f} pour 100 000 hab. · %{customdata[2]:.0%} volontaires<extra></extra>"))
    fig.update_layout(bargap=.45)
    return style(fig, height=320, legend=False, unified=False)


# ---------- Mise en page ----------

def tuile(titre, valeur, detail):
    return dbc.Card(dbc.CardBody([
        html.Div(titre, className="small", style={"color": INK_2, "minHeight": "2.6em"}),
        html.Div(valeur, style={"fontSize": "1.8rem", "fontWeight": 600, "color": INK, "lineHeight": 1.2}),
        html.Div(detail, className="small mt-1", style={"color": MUTED})]), className="h-100 shadow-sm border-0")


def section(num, titre, message, *contenu):
    return html.Section([
        html.H2([html.Span(f"{num}. ", style={"color": MUTED}), titre], className="h4 mt-5 pt-2"),
        html.P(message, className="mb-3", style={"color": INK_2, "maxWidth": "75ch"}), *contenu])


def graph(fig=None, **k):
    return dcc.Graph(figure=fig, config=CONFIG, **k) if fig is not None else dcc.Graph(config=CONFIG, **k)


filtres = dbc.Card(dbc.CardBody(dbc.Row([
    dbc.Col([html.Label("Période des incendies", className="small text-muted"),
             dcc.RangeSlider(ANNEE_MIN, ANNEE_MAX, 1, value=[ANNEE_MIN, ANNEE_MAX], id="periode",
                             marks={a: str(a) for a in range(ANNEE_MIN, ANNEE_MAX + 1, 3)},
                             tooltip={"placement": "bottom"})], lg=6),
    dbc.Col([html.Label("Territoire des cartes", className="small text-muted"),
             dbc.RadioItems(TERRITOIRES, TERRITOIRES[0], id="territoire", inline=True)], lg=3),
    dbc.Col([html.Label("Échelle des surfaces", className="small text-muted"),
             dbc.RadioItems([{"label": "Linéaire", "value": "lin"}, {"label": "Logarithmique", "value": "log"}],
                            "lin", id="echelle", inline=True)], lg=3),
], className="g-2")), className="border-0 shadow-sm mb-2")

recos = dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([
    html.H3(titre, className="h6"), html.P(constat, className="small mb-2", style={"color": INK_2}),
    html.P([html.B("Action : "), action], className="small mb-0")]), className="h-100 shadow-sm border-0"),
    lg=4, md=6) for titre, constat, action in recommandations(K)], className="g-3")

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], title="Incendies : Landes vs Côte d'Azur")
app.layout = dbc.Container([
    html.Header([
        html.H1(TITRE, className="h2 mt-4 mb-1"),
        html.P(PROBLEMATIQUE, className="mb-1", style={"color": INK_2, "maxWidth": "80ch"}),
        html.P(f"Public : {PUBLIC}. Comparaison avec les Alpes-Maritimes, territoire méditerranéen habitué aux feux.",
               className="small text-muted"),
    ]),
    dbc.Row([dbc.Col(tuile(*t), lg=True, md=4, sm=6) for t in tuiles(K)], className="g-3 mb-4"),
    filtres,

    section(1, "Le climat : des étés landais plus chauds que ceux de Nice",
            "Courbes = moyenne glissante sur 10 ans, points = chaque été. Depuis les années 2000, "
            "Bordeaux et Mont-de-Marsan dépassent Nice en jours de forte chaleur.",
            graph(fig_j30()),
            html.H3("Écart de température annuelle à la normale 1961-1990", className="h6 mt-3"),
            graph(fig_stripes())),

    section(2, "Les incendies : moins de départs, mais des feux plus grands",
            "Les Landes de Gascogne brûlent régulièrement plus que les Alpes-Maritimes, et 2022 change d'échelle. "
            "Passez en échelle logarithmique pour comparer les autres années.",
            graph(id="g-surface"),
            dbc.Checklist([{"label": "Exclure 2022 (année exceptionnelle)", "value": "hors"}], [], id="hors2022",
                          switch=True, className="small mt-3"),
            dbc.Row([dbc.Col([html.H3("Nombre de feux par an", className="h6"), graph(id="g-nb")], md=6),
                     dbc.Col([html.H3("Surface moyenne par feu (ha)", className="h6"), graph(id="g-moy")], md=6)],
                    className="g-3 mt-1"),
            html.P("Même sans 2022, la surface moyenne par feu augmente dans les deux territoires (+56 % dans les "
                   "Landes de Gascogne, +75 % dans les Alpes-Maritimes), alors que le nombre de départs baisse : "
                   "les feux deviennent plus difficiles à contenir partout.", className="small text-muted"),
            dbc.Row([
                dbc.Col([html.H3("Où brûle-t-on ?", className="h6"),
                         dbc.Checklist([{"label": "Afficher les centres de secours", "value": "casernes"}],
                                       ["casernes"], id="couches", switch=True, className="small mb-2"),
                         graph(id="g-carte-feux")], lg=7),
                dbc.Col([html.H3("Chaleur de l'été et surface brûlée", className="h6"),
                         html.P("Un point par année et par territoire. Le lien existe dans les Landes (r ≈ 0,4) "
                                "mais reste modéré : la chaleur ne suffit pas, il faut un départ de feu. Aucun lien "
                                "visible dans les Alpes-Maritimes avec la station littorale de Nice.",
                                className="small text-muted"),
                         graph(fig_correlation())], lg=5),
            ], className="g-4 mt-2"),
            dbc.Accordion([dbc.AccordionItem(dash_table.DataTable(
                id="table-feux", page_size=10, sort_action="native",
                style_cell={"fontFamily": FONT, "fontSize": 13}, style_header={"fontWeight": 600}),
                title="Voir les données annuelles (tableau)")], start_collapsed=True, className="mt-3")),

    section(3, "La prévention : des plans quasi absents du massif landais",
            f"Communes classées à risque feu de forêt et état de leur plan de prévention des risques d'incendie "
            f"(PPRIF). Dans les Landes, {K['plan_landes']} commune sur {K['risque_landes']} en a un. "
            f"Le plan de La Teste-de-Buch, prescrit en 2007, n'était toujours pas approuvé lors des feux de 2022.",
            dbc.Row([
                dbc.Col([graph(fig_prevention_barres()),
                         html.P(f"{pct(K['part_brule_sans_plan_lg'])} de la surface brûlée des Landes de Gascogne "
                                "depuis 2006 l'a été dans des communes sans plan approuvé. Attention : presque aucune "
                                "commune n'en a, ce chiffre ne prouve donc pas que les plans sont efficaces.",
                                className="small text-muted")], lg=5),
                dbc.Col([html.P("Taille des points = surface brûlée 2006-2025.", className="small text-muted mb-1"),
                         graph(id="g-carte-prev")], lg=7),
            ], className="g-4")),

    section(4, "Les moyens : un territoire immense pour peu de pompiers",
            "Les Landes ont beaucoup de pompiers par habitant, mais très peu par km² de territoire à défendre, "
            "et surtout des volontaires. Le budget rattrape son retard depuis 2022.",
            dbc.Row([
                dbc.Col([html.H3("Sapeurs-pompiers pour 1 000 km² (2024)", className="h6"), graph(fig_pompiers())],
                        lg=4),
                dbc.Col([html.H3("Dépenses totales du SDIS par habitant", className="h6"),
                         graph(fig_budget("depenses_totales", ""))], lg=4),
                dbc.Col([html.H3("Achats de véhicules par habitant", className="h6"),
                         graph(fig_budget("vehicules", "", annot=False))], lg=4),
            ], className="g-3"),
            html.H3("Moyens aériens", className="h6 mt-3"),
            html.Ul([html.Li([html.B(r.base), f" : {r.moyens} ({r.statut.lower()})"], className="small")
                     for r in D["aerien"].itertuples()])),

    section(5, "Recommandations", "Chaque action découle d'un constat chiffré du tableau de bord.", recos),

    section(6, "Limites et sources", "Ce que ces données ne permettent pas de conclure.",
            html.Ul([html.Li(lim, className="small") for lim in LIMITES]),
            html.P([html.Span("Sources : ", className="fw-semibold")] + sum(
                [[html.A(n, href=u, target="_blank"), " · "] for n, u in SOURCES], [])[:-1],
                className="small text-muted mb-5")),
], fluid="lg", style={"fontFamily": FONT, "color": INK})


@app.callback(Output("g-surface", "figure"), Output("table-feux", "data"), Output("table-feux", "columns"),
              Input("periode", "value"), Input("echelle", "value"))
def maj_surface(periode, echelle):
    a, b = periode
    t = D["feux_an"][D["feux_an"].annee.between(a, b)].pivot(index="annee", columns="territoire",
                                                             values="surface_ha").round(0).reset_index()
    cols = [{"name": "Année" if c == "annee" else f"{c} (ha)", "id": c} for c in t.columns]
    return fig_surface(a, b, echelle == "log"), t.to_dict("records"), cols


@app.callback(Output("g-nb", "figure"), Output("g-moy", "figure"), Input("hors2022", "value"))
def maj_nature(hors):
    h = "hors" in (hors or [])
    return (fig_nature("feux_par_an", "Nombre de feux par an", h),
            fig_nature("surface_moyenne_par_feu_ha", "Surface moyenne par feu (ha)", h))


@app.callback(Output("g-carte-feux", "figure"),
              Input("territoire", "value"), Input("periode", "value"), Input("couches", "value"))
def maj_carte_feux(territoire, periode, couches):
    return fig_carte_feux(territoire, *periode, couches or [])


@app.callback(Output("g-carte-prev", "figure"), Input("territoire", "value"))
def maj_carte_prev(territoire):
    return fig_carte_prevention(territoire)


if __name__ == "__main__":
    app.run(debug=True)
