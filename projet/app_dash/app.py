"""Dashboard Dash + Plotly : Landes de Gascogne vs Alpes-Maritimes face aux incendies.

Lancement (depuis le dossier projet/) : python app_dash/app.py  puis http://127.0.0.1:8050
"""
import sys
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dash_table, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (ANNEE_MAX, ANNEE_MIN, INK, INK_2, LIMITES, MUTED, PROBLEMATIQUE,  # noqa: E402
                    PUBLIC, SOURCES, TERRITOIRES, TITRE, pct, recommandations, tuiles)
from figures import (CONFIG, D, FONT, K, fig_budget, fig_carte_feux, fig_carte_prevention,  # noqa: E402
                     fig_correlation, fig_j30, fig_nature, fig_pompiers, fig_prevention_barres, fig_stripes,
                     fig_surface)


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
