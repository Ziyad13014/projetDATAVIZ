"""Rapport Dash façon Power BI : 5 pages d'un écran qui répondent pas à pas à la problématique.

① Le climat → ② Les incendies → ③ La prévention → ④ Les moyens → ⑤ Verdict

Lancement (depuis le dossier projet/) : python app_dash/ecran.py  puis http://127.0.0.1:8052
"""
import sys
from pathlib import Path
from urllib.parse import parse_qs

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import COULEUR_STATUT, COULEUR_TERRITOIRE, INK, INK_2, TERRITOIRES, TITRE, fmt, pct  # noqa: E402
from figures import (D, FONT, K, fig_budget, fig_carte_prevention, fig_j30, fig_pompiers,  # noqa: E402
                     fig_surface)

CONFIG = {"displaylogo": False, "responsive": True, "displayModeBar": False}
CADRAGE = {"Landes de Gascogne": (44.4, -0.75, 6.5), "Alpes-Maritimes": (43.95, 7.12, 8.0)}
LG, AM = "Landes de Gascogne", "Alpes-Maritimes"
ROUGE, ORANGE, VERT, MARINE = "#c23030", "#b25e00", "#0a7a0a", "#0d366b"
CLAIR, FONCE = "#cde2fb", "#184f95"

# ---------- Chiffres calculés pour le rapport ----------
C = D["climat"]
F = D["feux"].copy()
F["ete"] = F.mois.isin([6, 7, 8, 9])
CAUSES = {"Involontaire (particulier)": "Imprudence", "Involontaire (travaux)": "Imprudence",
          "Accidentelle": "Accident", "Malveillance": "Malveillance", "Naturelle": "Foudre", "Inconnue": "Inconnue"}
F["cause_g"] = F.cause.map(CAUSES).fillna("Inconnue")
COULEUR_CAUSE = {"Imprudence": "#1baf7a", "Malveillance": "#e87ba4", "Accident": "#eda100", "Foudre": "#4a3aa7",
                 "Inconnue": "#d8d7d0"}


def moy(st, a, b, col):
    return C[(C.station == st) & C.annee.between(a, b)][col].mean()


J35_AVANT, J35_APRES = moy("Mont-de-Marsan", 1961, 1990, "j35"), moy("Mont-de-Marsan", 2016, 2025, "j35")
ANOM_MER = moy("Bordeaux-Mérignac", 2016, 2025, "anomalie")
LG_F = F[F.territoire == LG]
HA_TOT = F.groupby("territoire").surface_ha.sum()
GRANDS = F.groupby("territoire").grand_feu.sum()
P_2022 = LG_F[LG_F.annee == 2022].surface_ha.sum() / LG_F[LG_F.annee >= 2016].surface_ha.sum()
P_ETE = F[F.ete].groupby("territoire").surface_ha.sum() / HA_TOT
POMP = D["pompiers"].set_index("departement")
J30_MDM_2022 = C[(C.station == "Mont-de-Marsan") & (C.annee == 2022)].j30.iloc[0]
LIMITES_COURTES = [
    "Hors 2022, la surface brûlée annuelle des Landes n'augmente pas : la tendance repose surtout sur une année.",
    "Une seule station météo par département ; Nice, littorale, sous-estime la chaleur de l'arrière-pays.",
    "La cause est inconnue pour la moitié des feux ; corrélation ne veut pas dire causalité.",
    "Pompiers : une seule année (2024) ; moyens aériens issus de la presse.",
]
TESTE_2022 = F[(F.commune == "La Teste-de-Buch") & (F.annee == 2022)].surface_ha.max()
PREV = D["prevention_dep"].set_index("departement")


def evol(avant, apres):
    return (apres - avant) / avant


# ---------- Briques visuelles ----------

def base(fig, legende=True):
    fig.update_layout(height=None, autosize=True, font=dict(family=FONT, size=12, color=INK_2),
                      margin=dict(l=4, r=8, t=6, b=4), paper_bgcolor="white", plot_bgcolor="white",
                      separators=", ", showlegend=legende,
                      legend=dict(orientation="h", x=0, y=1.0, yanchor="bottom", title=None, font_size=12))
    fig.update_xaxes(title=None, tickfont_size=11)
    fig.update_yaxes(title=None, tickfont_size=11)
    return fig


def donuts(series, titres, couleurs, centres, legende=True, taille=18):
    """Plusieurs anneaux côte à côte : series = liste de dict {libellé: valeur}."""
    n = len(series)
    fig = make_subplots(1, n, specs=[[{"type": "domain"}] * n], subplot_titles=titres, horizontal_spacing=.04)
    for i, s in enumerate(series):
        fig.add_trace(go.Pie(
            labels=list(s), values=list(s.values()), hole=.62, sort=False, direction="clockwise",
            marker=dict(colors=[couleurs[k] for k in s], line=dict(color="white", width=2)),
            textinfo="none", hovertemplate="%{label} : %{value:,.0f} (%{percent})<extra></extra>",
            showlegend=legende and i == 0), 1, i + 1)
        dom = fig.data[-1].domain
        fig.add_annotation(x=sum(dom.x) / 2, y=sum(dom.y) / 2, xref="paper", yref="paper", showarrow=False,
                           text=f"<b>{centres[i]}</b>", font=dict(size=taille, color=INK))
    for a in fig.layout.annotations[:len([t for t in titres if t])]:  # titres des anneaux
        a.update(font=dict(size=12, color=INK_2), y=a.y + .02)
    fig = base(fig, legende)
    return fig.update_layout(legend=dict(orientation="h", x=.5, xanchor="center", y=-.02, yanchor="top"),
                             margin=dict(t=24, b=4, l=4, r=4))


def kpi(lib, valeur, unite, delta, sens, ref, fleche=None):
    """Carte KPI : la flèche suit le sens de l'évolution, la couleur dit si c'est bon ou mauvais."""
    fleche = fleche or ("▲" if delta.startswith(("+", "×")) else "▼" if delta.startswith(("-", "−")) else "●")
    return html.Div([html.Div(lib, className="lib"),
                     html.Div([valeur, html.Span(unite, className="unite")], className="val"),
                     html.Div(f"{fleche} {delta}", className=f"delta {sens}"),
                     html.Div(ref, className="ref")], className="kpi")


def constat(question, reponse, couleur, texte):
    return html.Div([html.Span(reponse, className="badge-rep"),
                     html.Div([html.Div(question, className="q"), html.Div(texte, className="r")])],
                    className="constat", style={"--c": couleur})


def visuel(titre, sous, contenu, classe="", ctrl=None):
    if isinstance(contenu, go.Figure):
        contenu = dcc.Graph(figure=contenu, config=CONFIG, className="graph", style={"height": "100%"})
    elif isinstance(contenu, str):
        contenu = dcc.Graph(id=contenu, config=CONFIG, className="graph", style={"height": "100%"})
    enfants = [html.Div(titre, className="titre"), html.Div(sous, className="sous")]
    if ctrl is not None:
        enfants.append(html.Div(ctrl, className="ctrl"))
    enfants.append(html.Div(contenu, className="zone"))
    return html.Div(enfants, className=f"visuel {classe}")


# ---------- Figures propres au rapport ----------

def fig_avant_apres():
    st = ["Mont-de-Marsan", "Bordeaux-Mérignac", "Nice"]
    av = [moy(s, 1961, 1990, "j30") for s in st]
    ap = [moy(s, 2016, 2025, "j30") for s in st]
    fig = go.Figure([
        go.Bar(name="1961-1990", x=st, y=av, marker_color="#c3c2b7", text=[f"{v:.0f}" for v in av]),
        go.Bar(name="2016-2025", x=st, y=ap, marker_color=FONCE, text=[f"{v:.0f}" for v in ap]),
    ])
    fig.update_traces(textposition="outside", cliponaxis=False, textfont=dict(size=13, color=INK),
                      hovertemplate="%{x}, %{fullData.name} : %{y:.1f} jours<extra></extra>")
    fig.update_yaxes(showticklabels=False, showgrid=False, range=[0, max(ap) * 1.2])
    return base(fig).update_layout(barmode="group", bargap=.3, bargroupgap=.06)


def fig_saison():
    m = F.groupby(["territoire", "mois"]).size().unstack(0).reindex(range(1, 13), fill_value=0)
    mois = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    fig = go.Figure([go.Bar(name=t, x=list(range(1, 13)), y=m[t], marker_color=COULEUR_TERRITOIRE[t],
                            hovertemplate=f"{t} : %{{y}} feux<extra></extra>") for t in TERRITOIRES])
    fig.update_xaxes(tickvals=list(range(1, 13)), ticktext=mois)
    fig.update_yaxes(gridcolor="#e1e0d9")
    return base(fig).update_layout(barmode="group", bargap=.2, hovermode="x unified")


def fig_causes():
    s = [F[F.territoire == t].cause_g.value_counts().reindex(list(COULEUR_CAUSE), fill_value=0).to_dict()
         for t in TERRITOIRES]
    centres = [pct(1 - x["Inconnue"] / sum(x.values())) for x in s]
    return donuts(s, TERRITOIRES, COULEUR_CAUSE, centres, taille=15)


def fig_poids_2022():
    s = {"2022": LG_F[LG_F.annee == 2022].surface_ha.sum(),
         "Autres années": LG_F[(LG_F.annee >= 2016) & (LG_F.annee != 2022)].surface_ha.sum()}
    return donuts([s], [""], {"2022": FONCE, "Autres années": CLAIR}, [pct(P_2022)], taille=22)


def fig_ete():
    s = [{"Été (juin-sept.)": F[(F.territoire == t) & F.ete].surface_ha.sum(),
          "Reste de l'année": F[(F.territoire == t) & ~F.ete].surface_ha.sum()} for t in TERRITOIRES]
    return donuts(s, TERRITOIRES, {"Été (juin-sept.)": FONCE, "Reste de l'année": CLAIR},
                  [pct(P_ETE[t]) for t in TERRITOIRES])


def fig_prev_donuts():
    statuts = [s for s in COULEUR_STATUT if s != "Non classée à risque"]
    p = D["prevention"]
    s, centres = [], []
    for dep in ["Landes", "Gironde", "Alpes-Maritimes"]:
        n = p[(p.dep == {"Landes": "40", "Gironde": "33", "Alpes-Maritimes": "06"}[dep])
              & (p.statut != "Non classée à risque")].statut.value_counts()
        s.append({st: int(n.get(st, 0)) for st in statuts})
        centres.append(pct(PREV.loc[dep, "part_risque_couverte"]))
    return donuts(s, ["Landes", "Gironde", "Alpes-Maritimes"], COULEUR_STATUT, centres)


def fig_statut_surface():
    p = D["prevention"][D["prevention"].territoire == LG]
    statuts = [s for s in COULEUR_STATUT if s != "Non classée à risque"]
    v = p.groupby("statut").surface_brulee_ha.sum().reindex(statuts, fill_value=0)
    fig = go.Figure(go.Bar(x=v.values, y=v.index, orientation="h", marker_color=[COULEUR_STATUT[s] for s in statuts],
                           text=[f"{fmt(x)} ha" for x in v.values], textposition="outside", cliponaxis=False,
                           textfont=dict(size=12, color=INK), hovertemplate="%{y} : %{x:,.0f} ha<extra></extra>"))
    fig.update_xaxes(showticklabels=False, showgrid=False, range=[0, v.max() * 1.35])
    fig.update_yaxes(autorange="reversed")
    return base(fig, legende=False)


def fig_pros_vol():
    s = [{"Professionnels": int(POMP.loc[d, "spp_spm"]), "Volontaires": int(POMP.loc[d, "spv_spr"])}
         for d in ["Landes", "Gironde", "Alpes-Maritimes"]]
    return donuts(s, ["Landes", "Gironde", "Alpes-Maritimes"], {"Professionnels": FONCE, "Volontaires": "#86b6ef"},
                  [pct(POMP.loc[d, "part_volontaires"]) for d in ["Landes", "Gironde", "Alpes-Maritimes"]])


# ---------- Pages ----------

def page_climat():
    return html.Div([
        constat("① Le climat des Landes devient-il méditerranéen ?", "OUI", ROUGE,
                "Depuis les années 2000, les étés de Bordeaux et de Mont-de-Marsan comptent plus de jours "
                "de forte chaleur que ceux de Nice."),
        html.Div([
            kpi("Jours ≥ 30 °C par été, Mont-de-Marsan", f"{K['j30_mdm_now']:.0f}", "jours",
                f"+{evol(K['j30_mdm_ref'], K['j30_mdm_now']):.0%}".replace("%", " %"), "mauvais",
                f"2016-2025, contre {K['j30_mdm_ref']:.0f} j en 1961-1990"),
            kpi("Jours ≥ 35 °C par été, Mont-de-Marsan", fmt(J35_APRES, 1), "jours",
                f"×{J35_APRES / J35_AVANT:.0f}", "mauvais", f"2016-2025, contre {fmt(J35_AVANT, 1)} j en 1961-1990"),
            kpi("Écart de température, Bordeaux-Mérignac", f"+{fmt(ANOM_MER, 1)}", "°C",
                "réchauffement marqué", "mauvais", "Moyenne 2016-2025 vs 1961-1990", fleche="▲"),
            kpi("Avance des Landes sur Nice", f"+{K['j30_mdm_now'] - K['j30_nice_now']:.0f}", "jours ≥ 30 °C",
                f"+{K['j30_mdm_now'] - K['j30_nice_now']:.0f} j", "neutre",
                f"Mont-de-Marsan {K['j30_mdm_now']:.0f} j, Nice {K['j30_nice_now']:.0f} j (2016-2025)"),
        ], className="kpis"),
        html.Div([
            visuel("Jours ≥ 30 °C par été, 1950-2025",
                   "Courbes = moyenne sur 10 ans, points = chaque été. Bande grise = normale 1961-1990.",
                   base(fig_j30()), "l2"),
            visuel("Avant / maintenant", "Jours ≥ 30 °C par été en moyenne.", fig_avant_apres()),
        ], className="visuels une-ligne"),
    ], className="page")


def page_incendies():
    return html.Div([
        constat("② Les incendies changent-ils de nature ?", "EN PARTIE", ORANGE,
                "Moins de départs de feu, mais des feux plus grands et concentrés l'été. "
                "Attention : 2022 pèse pour l'essentiel de la surface brûlée."),
        html.Div([
            kpi("Surface brûlée 2006-2025, Landes de Gascogne", fmt(HA_TOT[LG]), "ha",
                f"×{HA_TOT[LG] / HA_TOT[AM]:.1f}".replace(".", ","), "mauvais",
                f"Alpes-Maritimes : {fmt(HA_TOT[AM])} ha"),
            kpi("Feux par an, Landes de Gascogne", fmt(K["nb_lg_apres"]), "feux",
                f"{evol(K['nb_lg_avant'], K['nb_lg_apres']):.0%}".replace("%", " %"), "bon",
                f"2016-2025, contre {fmt(K['nb_lg_avant'])} en 2006-2015"),
            kpi("Surface moyenne par feu", fmt(K["moy_lg_apres"], 1), "ha",
                f"+{evol(K['moy_lg_avant'], K['moy_lg_apres_hors22']):.0%} hors 2022".replace("%", " %"), "mauvais",
                f"2016-2025, contre {fmt(K['moy_lg_avant'], 1)} ha en 2006-2015"),
            kpi("Grands feux (≥ 100 ha), 2006-2025", f"{GRANDS[LG]}", "feux",
                f"×{GRANDS[LG] / GRANDS[AM]:.1f}".replace(".", ","), "mauvais",
                f"Alpes-Maritimes : {GRANDS[AM]} grands feux"),
        ], className="kpis"),
        html.Div([
            visuel("Surface brûlée par an (ha)", "La rupture de 2022 : Landiras et La Teste-de-Buch.", "g-surface",
                   "l2", ctrl=dbc.Switch(id="log", label="Échelle logarithmique (pour voir les autres années)",
                                         value=False)),
            visuel("Poids de 2022", "Part de 2022 dans la surface brûlée landaise 2016-2025.", fig_poids_2022()),
            visuel("Saison des feux", "Nombre de feux par mois, 2006-2025. Les Landes brûlent l'été.",
                   fig_saison()),
            visuel("Surface brûlée en été", "Part de la surface brûlée entre juin et septembre.", fig_ete()),
            visuel("Causes des feux", "Part des feux par cause ; au centre, part des feux dont la cause est connue.",
                   fig_causes()),
        ], className="visuels deux-lignes"),
    ], className="page")


def page_prevention():
    return html.Div([
        constat("③ La prévention est-elle à la hauteur du risque ?", "NON", ROUGE,
                f"Aucune commune landaise à risque n'a de plan de prévention des incendies approuvé ; "
                f"en Gironde, aucun plan n'a été approuvé depuis {K['der_appro_gironde']:.0f}."),
        html.Div([
            kpi("Landes : communes à risque couvertes", f"{K['plan_landes']}", f"/ {K['risque_landes']}",
                "0 % couvert", "mauvais", "Plan de prévention approuvé (PPRIF)"),
            kpi("Gironde : communes à risque couvertes", f"{K['plan_gironde']}", f"/ {K['risque_gironde']}",
                f"{K['plan_gironde'] / K['risque_gironde']:.0%} couvert".replace("%", " %"), "mauvais",
                f"Dernière approbation : {K['der_appro_gironde']:.0f}"),
            kpi("Alpes-Maritimes : communes couvertes", f"{K['plan_am']}", f"/ {K['risque_am']}",
                f"{K['plan_am'] / K['risque_am']:.0%} couvert".replace("%", " %"), "neutre",
                "Territoire de comparaison"),
            kpi("Surface landaise brûlée hors commune couverte", pct(K["part_brule_sans_plan_lg"]), "",
                "de la surface 2006-2025", "mauvais", "Presque aucune commune n'a de plan : ce n'est pas une preuve"),
        ], className="kpis"),
        html.Div([
            visuel("Communes à risque selon l'état de leur plan",
                   "Au centre : part des communes à risque couvertes par un plan approuvé.", fig_prev_donuts(), "l2"),
            visuel("Carte des communes", "Couleur = statut, taille = surface brûlée 2006-2025.", "g-carte", "h2",
                   ctrl=dbc.RadioItems(TERRITOIRES, LG, id="territoire", inline=True)),
            visuel("Surface brûlée selon le statut (Landes de Gascogne)", "Hectares brûlés 2006-2025.",
                   fig_statut_surface()),
            visuel("Exemple : La Teste-de-Buch", "", html.Div([
                html.Div("2007", className="gros"),
                html.P(["Plan de prévention ", html.B("prescrit en 2007"), ", toujours ", html.B("pas approuvé"),
                        " en 2026."]),
                html.P(["Le 12 juillet 2022, un feu y parcourt ", html.B(f"{fmt(TESTE_2022)} ha"), "."]),
            ], className="encadre")),
        ], className="visuels deux-lignes"),
    ], className="page")


def page_moyens():
    pomp_h = lambda d: POMP.loc[d, "pompiers_100k_hab"]  # noqa: E731
    return html.Div([
        constat("④ Les moyens de lutte sont-ils à la hauteur ?", "PAS ENCORE", ORANGE,
                "Assez de pompiers par habitant, mais trop peu pour l'immense surface du massif, et surtout "
                "des volontaires. Le budget ne rattrape son retard que depuis 2022."),
        html.Div([
            kpi("Pompiers pour 1 000 km², Landes", fmt(K["pomp_km2_landes"]), "",
                f"{evol(K['pomp_km2_am'], K['pomp_km2_landes']):.0%} vs Alpes-Maritimes".replace("%", " %"), "mauvais",
                f"Alpes-Maritimes : {fmt(K['pomp_km2_am'])} (2024)"),
            kpi("Pompiers pour 100 000 habitants, Landes", fmt(pomp_h("Landes")), "",
                f"+{evol(pomp_h('Alpes-Maritimes'), pomp_h('Landes')):.0%} vs Alpes-Maritimes".replace("%", " %"),
                "bon", f"Alpes-Maritimes : {fmt(pomp_h('Alpes-Maritimes'))} (2024)"),
            kpi("Part de volontaires, Landes", pct(K["vol_landes"]), "",
                f"+{(K['vol_landes'] - POMP.loc['Alpes-Maritimes', 'part_volontaires']) * 100:.0f} points", "mauvais",
                f"Alpes-Maritimes : {pct(POMP.loc['Alpes-Maritimes', 'part_volontaires'])}"),
            kpi("Budget du SDIS des Landes", f"{K['bud_landes_2025']:.0f}", "€/hab",
                f"+{evol(K['bud_landes_2021'], K['bud_landes_2025']):.0%} depuis 2021".replace("%", " %"), "bon",
                f"Alpes-Maritimes : {K['bud_am_2025']:.0f} €/hab (2025)"),
        ], className="kpis"),
        html.Div([
            visuel("Sapeurs-pompiers pour 1 000 km² (2024)", "Le territoire à défendre est immense.",
                   base(fig_pompiers(), legende=False).update_yaxes(
                       range=[0, K["pomp_km2_am"] * 1.15], showticklabels=False, showgrid=False)
                   .update_traces(textfont_size=14)),
            visuel("Professionnels et volontaires (2024)", "Au centre : part de volontaires.", fig_pros_vol(), "l2"),
            visuel("Dépenses du SDIS par habitant (€)", "Le rattrapage landais commence après 2022.",
                   base(fig_budget("depenses_totales", "")), "l2"),
            visuel("Moyens aériens", "", html.Div([
                html.P([html.B("Nîmes-Garons"), " (Gard) : la base nationale des bombardiers d'eau "
                        "(~10 Canadair, 7 Dash)."]),
                html.P([html.B("Bordeaux-Mérignac"), " : un détachement ", html.B("seulement l'été"),
                        " (1 Dash et 6 avions bombardiers)."]),
                html.P("Source : presse (Brut, Maire-info), à recouper.", style={"fontSize": ".72rem"}),
            ], className="encadre")),
        ], className="visuels deux-lignes"),
    ], className="page")


def page_verdict():
    scores = [
        ("① Climat", "OUI", ROUGE, f"Mont-de-Marsan : {K['j30_mdm_ref']:.0f} → {K['j30_mdm_now']:.0f} jours ≥ 30 °C "
                                  f"par été, plus que Nice ({K['j30_nice_now']:.0f})."),
        ("② Incendies", "EN PARTIE", ORANGE, f"Moins de feux ({fmt(K['nb_lg_avant'])} → {fmt(K['nb_lg_apres'])} par an) "
                                            f"mais plus grands ; 2022 = {pct(P_2022)} de la surface 2016-2025."),
        ("③ Prévention", "NON", ROUGE, f"{K['plan_landes']} commune landaise sur {K['risque_landes']} couverte par "
                                       "un plan de prévention."),
        ("④ Moyens", "PAS ENCORE", ORANGE, f"{fmt(K['pomp_km2_landes'])} pompiers / 1 000 km² contre "
                                           f"{fmt(K['pomp_km2_am'])} ; budget +{evol(K['bud_landes_2021'], K['bud_landes_2025']):.0%} "
                                           "depuis 2021.".replace("%", " %")),
    ]
    recos = [
        ("Achever les plans de prévention", "En priorité dans les communes déjà touchées (La Teste-de-Buch…)."),
        ("Attaquer les feux naissants", "Patrouilles armées l'été, intervention en moins de 10 minutes."),
        ("Renforcer la présence l'été", "Saisonniers et disponibilité des volontaires en journée."),
        ("Pérenniser les moyens", "Budget du SDIS et base aérienne saisonnière permanente à Mérignac."),
        ("Agir sur les causes", "Débroussaillement obligatoire (loi du 10 juillet 2023), sensibilisation."),
        ("Adapter la forêt", "Coupures de combustible, diversification des essences du massif."),
    ]
    return html.Div([
        html.Div([html.Div("Le réchauffement fait-il basculer le massif landais vers un risque méditerranéen, "
                           "et ses moyens sont-ils à la hauteur ?", className="q"),
                  html.Div("Oui, le climat du massif landais bascule vers un risque méditerranéen. "
                           "Non, sa prévention et ses moyens ne sont pas encore à la hauteur.", className="r")],
                 className="verdict"),
        html.Div([html.Div([html.Div(e, className="etiq"), html.Div(r, className="rep"), html.Div(t, className="chiffre")],
                           className="score", style={"--c": c}) for e, r, c, t in scores], className="scores"),
        html.Div([
            html.Div([html.Div("Et demain ?", className="titre"),
                      html.Div("Trajectoire de réchauffement de référence (TRACC) fixée par l'État pour la France "
                               "hexagonale, par rapport à l'ère préindustrielle :", className="sous"),
                      html.Div([html.Div([html.Span("+2 °C", className="grand"), " en 2030"]),
                                html.Div([html.Span("+2,7 °C", className="grand"), " en 2050"]),
                                html.Div([html.Span("+4 °C", className="grand"), " en 2100"])],
                               className="encadre demain", style={"marginTop": "8px"}),
                      html.Div(["En 2022, Mont-de-Marsan a connu ", html.B(f"{J30_MDM_2022:.0f} jours ≥ 30 °C"),
                                " et le massif a perdu ", html.B(f"{fmt(K['ha_lg_2022'])} ha"),
                                ". Avec un climat plus chaud, ce type d'été risque de devenir plus fréquent : "
                                "la prévention doit s'y préparer dès maintenant."],
                               className="encadre", style={"marginTop": "10px"})],
                     className="visuel"),
            html.Div([html.Div("Recommandations", className="titre"),
                      html.Div("Chacune répond à un constat des pages précédentes.", className="sous"),
                      html.Div([html.Div([html.B(t), d], className="reco") for t, d in recos], className="recos",
                               style={"marginTop": "8px"}),
                      html.Div("Limites de l'analyse", className="titre", style={"marginTop": "14px"}),
                      html.Ul([html.Li(x) for x in LIMITES_COURTES], className="encadre",
                              style={"margin": "4px 0 0", "paddingLeft": "18px"}),
                      html.Div("Sources : Météo-France, BDIFF, GASPAR (Géorisques), DGSCGC, OFGL, geo.api.gouv.fr, "
                               "ministère de la Transition écologique (TRACC). Limites détaillées dans le README.",
                               className="sources", style={"marginTop": "auto"})],
                     className="visuel"),
        ], className="bas"),
    ], className="page")


PAGES = {"climat": ("① Le climat", page_climat), "incendies": ("② Les incendies", page_incendies),
         "prevention": ("③ La prévention", page_prevention), "moyens": ("④ Les moyens", page_moyens),
         "verdict": ("⑤ Verdict", page_verdict)}

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], assets_folder="assets_ecran",
           title="Incendies : Landes vs Côte d'Azur", suppress_callback_exceptions=True)
app.layout = html.Div([
    dcc.Location(id="url"),
    html.Div([html.H1(TITRE),
              html.Div("Le massif des Landes de Gascogne (Gironde + Landes) comparé aux Alpes-Maritimes, territoire "
                       "méditerranéen habitué aux feux. Suivez les étapes pour répondre à la question.",
                       className="question")], className="bandeau-titre"),
    html.Div(dbc.RadioItems(id="nav", value="climat", className="btn-group", inputClassName="btn-check",
                            labelClassName="btn etape", labelCheckedClassName="active",
                            options=[{"label": lib, "value": cle} for cle, (lib, _) in PAGES.items()]),
             className="etapes"),
    html.Div(id="contenu", style={"flex": 1, "minHeight": 0, "display": "flex", "flexDirection": "column"}),
], className="ecran")


@app.callback(Output("nav", "value"), Input("url", "search"))
def page_depuis_adresse(search):
    """?page=incendies ouvre directement une étape (lien partageable)."""
    cle = parse_qs((search or "").lstrip("?")).get("page", ["climat"])[0]
    return cle if cle in PAGES else "climat"


@app.callback(Output("contenu", "children"), Input("nav", "value"))
def afficher_page(cle):
    return PAGES[cle][1]()


@app.callback(Output("g-surface", "figure"), Input("log", "value"))
def maj_surface(log):
    return base(fig_surface(2006, 2025, log)).update_layout(bargap=.2)


@app.callback(Output("g-carte", "figure"), Input("territoire", "value"))
def maj_carte(territoire):
    lat, lon, zoom = CADRAGE[territoire]
    fig = base(fig_carte_prevention(territoire), legende=False)
    return fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), map_center=dict(lat=lat, lon=lon), map_zoom=zoom)


if __name__ == "__main__":
    app.run(debug=False, port=8052)
