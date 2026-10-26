"""Dashboard « Le massif landais devient-il méditerranéen ? » (écran unique).

Deux pages : le diagnostic (/) et les solutions cartographiées (/solutions).
Lancement : python app/app.py  →  http://127.0.0.1:8050
"""
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

import donnees as d
import figures as fx

PANNEAUX = [
    ("koppen", "1 · Climat", "Classification de Köppen", fx.panneau_koppen),
    ("gaussen", "2 · Été sec", "Diagramme de Gaussen", fx.panneau_gaussen),
    ("tendance", "3 · Évolution", "Mois secs par an depuis 1950", fx.panneau_tendance),
    ("feux", "4 · Feux de forêt", "Surface brûlée par département", fx.panneau_feux),
]
ICONES = {"oui": "●", "partiel": "◐", "non": "○"}
CONFIG_GRAPHE = {"displayModeBar": False, "responsive": True}


def options(postes: list[str]) -> list[dict]:
    return [{"label": d.nom(p), "value": p} for p in postes]


def panneau(cle: str, numero: str, sous_titre: str) -> html.Div:
    return html.Section(className="panneau", children=[
        html.Div(className="panneau-haut", children=[
            html.Span([html.B(numero), f" — {sous_titre}"], className="panneau-numero"),
            html.Span(id=f"{cle}-statut", className="statut"),
        ]),
        html.H2(id=f"{cle}-titre", className="panneau-titre"),
        html.P(id=f"{cle}-chiffres", className="panneau-chiffres"),
        dcc.Graph(id=f"{cle}-graphe", className="graphe", config=CONFIG_GRAPHE),
    ])


def panneau_carte(numero: str, sous_titre: str, carte) -> html.Section:
    fig, v = carte()
    return html.Section(className="panneau", children=[
        html.Div(className="panneau-haut", children=[
            html.Span([html.B(numero), f" — {sous_titre}"], className="panneau-numero"),
        ]),
        html.H2(v.titre, className="panneau-titre"),
        html.P(v.chiffres, className="panneau-chiffres"),
        dcc.Graph(figure=fig, className="graphe", config={**CONFIG_GRAPHE, "scrollZoom": True}),
    ])


app = Dash(__name__, title="Le massif landais devient-il méditerranéen ?",
           suppress_callback_exceptions=True)

PAGE_DIAGNOSTIC = [
    html.Header(className="entete", children=[
        html.Div(className="entete-texte", children=[
            html.H1("Le massif landais devient-il méditerranéen ?"),
            html.P(className="reponse", children=[
                html.B("Pas encore. "),
                "Son climat reste océanique, mais ses étés s'assèchent et il connaît "
                "désormais des feux dignes de la Méditerranée.",
            ]),
        ]),
        html.Div(className="controles", children=[
            html.Label("Comparer", htmlFor="choix-landes"),
            dcc.Dropdown(id="choix-landes", options=options(d.STATIONS_LANDES),
                         value="40192001", clearable=False, searchable=False,
                         className="choix choix-landes"),
            html.Label("avec", htmlFor="choix-med"),
            dcc.Dropdown(id="choix-med", options=options(d.STATIONS_MED),
                         value="66136001", clearable=False, searchable=False,
                         className="choix choix-med"),
            html.Button("Sources & méthode", id="ouvrir-methode", className="bouton-lien"),
            dcc.Link("Solutions →", href="/solutions", className="bouton-nav"),
        ]),
    ]),
    html.Main(className="grille", children=[panneau(c, n, s) for c, n, s, _ in PANNEAUX]),
]

PAGE_SOLUTIONS = [
    html.Header(className="entete", children=[
        html.Div(className="entete-texte", children=[
            html.H1("Où placer les secours pour éviter les mégafeux ?"),
            html.P(className="reponse", children=[
                html.B("Au cœur de la forêt. "),
                "Des pans entiers du massif sont à plus de 10 km d'une caserne, et les "
                "Canadair décollent de Nîmes, à plus d'une heure de vol.",
            ]),
        ]),
        html.Div(className="controles", children=[
            dcc.Link("← Diagnostic", href="/", className="bouton-nav"),
            html.Button("Sources & méthode", id="ouvrir-methode", className="bouton-lien"),
        ]),
    ]),
    html.Main(className="grille grille-cartes", children=[
        panneau_carte("Aujourd'hui", "Casernes et feux 2006–2025", fx.carte_actuelle),
        panneau_carte("Proposition", "Casernes, gardes forestiers et aire Canadair", fx.carte_solution),
    ]),
]

app.layout = html.Div(className="page", children=[
    dcc.Location(id="url"),
    html.Div(id="contenu", className="contenu"),
    html.Div(id="methode", className="modale cachee", children=[
        html.Div(className="modale-contenu", children=[
            html.H2("Sources & méthode"),
            html.H3("Données (open data)"),
            html.Ul([
                html.Li(["Climat : Météo-France, ",
                         html.A("données climatologiques mensuelles",
                                href="https://www.data.gouv.fr/datasets/donnees-climatologiques-de-base-mensuelles",
                                target="_blank"),
                         " (data.gouv.fr), 1950–2025, 7 stations aux séries complètes."]),
                html.Li(["Feux : ",
                         html.A("BDIFF",
                                href="https://www.data.gouv.fr/datasets/base-de-donnees-sur-les-incendies-de-forets-en-france-bdiff",
                                target="_blank"),
                         " (IGN / ministère de l'Agriculture), 2006–2025, 42 230 feux."]),
            ]),
            html.H3("Critères"),
            html.Ul([
                html.Li("Köppen (Peel et al., 2007) : climat méditerranéen (Cs) si le mois d'été le plus sec "
                        "reçoit moins de 40 mm et moins d'un tiers du mois d'hiver le plus humide. "
                        "Calculé sur des moyennes de 30 ans, comme l'exige la définition."),
                html.Li("Gaussen : un mois est sec si la pluie (mm) est inférieure ou égale à 2 × la température (°C)."),
                html.Li("Feux : chaque station est rattachée à son département."),
            ]),
            html.H3("Limites"),
            html.Ul([
                html.Li("Sept stations seulement : une station ne représente pas tout un massif."),
                html.Li("Feux : 20 ans de données seulement, et une année (2022) domine tout ; "
                        "la zone méditerranéenne recense davantage de petits feux."),
                html.Li("Surfaces brûlées non rapportées à la surface forestière de chaque département."),
                html.Li("Pas de projections futures : le dashboard décrit le climat observé."),
            ]),
            html.H3("Page Solutions"),
            html.Ul([
                html.Li(["Casernes : ",
                         html.A("OpenStreetMap", href="https://www.openstreetmap.org/copyright",
                                target="_blank"),
                         " (amenity=fire_station, licence ODbL). Contours des communes : ",
                         html.A("geo.api.gouv.fr", href="https://geo.api.gouv.fr/decoupage-administratif",
                                target="_blank"),
                         ". Massif = triangle landais (Soulac, Hossegor, Nérac) en Gironde et "
                         "dans les Landes, découpé en carrés de 2 km."]),
                html.Li("Casernes proposées : ajoutées une à une là où elles couvrent (10 km) le plus "
                        "de zone aujourd'hui à plus de 10 km d'une caserne ; les n° 3, 6 et 7 sont placées "
                        "par le groupe à l'est de Bordeaux et au sud du bassin d'Arcachon, au point "
                        "le plus loin de toute caserne. Postes de gardes "
                        "forestiers : même méthode avec un rayon de 5 km."),
                html.Li("Aire Canadair : le point de la forêt qui, avec Mérignac, rapproche le plus "
                        "chaque carré du massif d'une base. Cercles : 50 km, soit environ 10 min de "
                        "vol à 300 km/h. Nîmes-Garons est la base actuelle des Canadair ; Mérignac "
                        "accueille un pélicandrome depuis 2023 et des avions l'été."),
                html.Li("Limites : distances à vol d'oiseau, pas de temps de trajet par la route ; "
                        "les casernes OSM peuvent être incomplètes ; une aire Canadair demande aussi "
                        "une piste et un plan d'eau pour écoper, non vérifiés ici."),
            ]),
            html.Button("Fermer", id="fermer-methode", className="bouton"),
        ]),
    ]),
])


@app.callback(Output("contenu", "children"), Input("url", "pathname"))
def afficher_page(chemin: str):
    return PAGE_SOLUTIONS if chemin == "/solutions" else PAGE_DIAGNOSTIC


@app.callback(
    [Output(f"{c}-{s}", p) for c, *_ in PANNEAUX
     for s, p in (("graphe", "figure"), ("titre", "children"), ("chiffres", "children"),
                  ("statut", "children"), ("statut", "className"))],
    Input("choix-landes", "value"),
    Input("choix-med", "value"),
)
def mettre_a_jour(landes: str, med: str):
    sorties = []
    for _, _, _, construire in PANNEAUX:
        fig, v = construire(landes, med)
        sorties += [fig, v.titre, v.chiffres, f"{ICONES[v.statut]} {v.libelle}", f"statut statut-{v.statut}"]
    return sorties


@app.callback(
    Output("methode", "className"),
    Input("ouvrir-methode", "n_clicks"),
    Input("fermer-methode", "n_clicks"),
    State("methode", "className"),
    prevent_initial_call=True,
)
def basculer_methode(_ouvrir, _fermer, classe: str) -> str:
    # Le bouton « ouvrir » est recréé à chaque changement de page : sans clic, on ne fait rien.
    if not ctx.triggered[0]["value"]:
        return no_update
    return "modale" if "cachee" in classe else "modale cachee"


if __name__ == "__main__":
    app.run(debug=False)
