"""Graphiques et verdicts du dashboard.

Chaque fonction `panneau_*` renvoie (figure, verdict) pour une paire de stations
(une landaise, une méditerranéenne). Le verdict contient le statut du critère,
le titre-conclusion et la ligne de chiffres clés affichés au-dessus du graphique.
"""
from dataclasses import dataclass
import math

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import donnees as d

# Palette validée (scripts/validate_palette.js du skill dataviz) : bleu / orange.
COULEURS = {"Landes": "#2a78d6", "Méditerranée": "#eb6834"}
SURFACE = "#fcfcfb"
ENCRE = "#0b0b0b"
ENCRE_2 = "#52514e"
MUET = "#898781"
GRILLE = "#e1e0d9"
AXE = "#c3c2b7"
POLICE = 'system-ui, -apple-system, "Segoe UI", sans-serif'
MOIS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
MOIS_LONGS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
              "août", "septembre", "octobre", "novembre", "décembre"]


@dataclass
class Verdict:
    statut: str  # "oui" | "partiel" | "non"
    libelle: str
    titre: str
    chiffres: str


def _fmt(x: float, dec: int = 0) -> str:
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def _mise_en_page(fig: go.Figure, **kwargs) -> go.Figure:
    fig.update_layout(
        font=dict(family=POLICE, size=14, color=ENCRE_2),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        separators=", ",  # décimales à la française : 2,7 et 1 344
        margin=dict(l=8, r=8, t=8, b=8),
        hoverlabel=dict(font=dict(family=POLICE, size=14), bgcolor="white", bordercolor=AXE),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    font=dict(size=13), bgcolor="rgba(0,0,0,0)"),
        **kwargs,
    )
    fig.update_xaxes(showgrid=False, linecolor=AXE, ticks="outside", tickcolor=AXE,
                     zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=GRILLE, gridwidth=1, linecolor=AXE, zeroline=False,
                     automargin=True)
    return fig


# --- 1. Köppen : distance au seuil méditerranéen --------------------------------

def panneau_koppen(landes: str, med: str) -> tuple[go.Figure, Verdict]:
    fig = go.Figure()
    seuil = d.SEUIL_KOPPEN_MM
    n = d.normales

    fig.add_hrect(y0=0, y1=seuil, fillcolor=COULEURS["Méditerranée"], opacity=0.07,
                  line_width=0, layer="below")
    fig.add_hline(y=seuil, line=dict(color=ENCRE_2, width=1.5, dash="dash"))
    fig.add_annotation(x=0, xref="paper", y=seuil, yshift=-11, xanchor="left", showarrow=False,
                       text=f"Seuil méditerranéen : {seuil} mm", font=dict(size=13, color=ENCRE_2))

    # Les autres stations en gris pour le contexte.
    for poste in d.NOMS_STATIONS:
        if poste in (landes, med):
            continue
        s = n[n.NUM_POSTE == poste]
        fig.add_scatter(x=s.fin, y=s.p_ete_min, mode="lines", name=d.nom(poste),
                        line=dict(color=AXE, width=1), showlegend=False,
                        hovertemplate=f"{d.nom(poste)} · %{{y:.0f}} mm<extra></extra>")

    for poste, groupe in ((landes, "Landes"), (med, "Méditerranée")):
        s = n[n.NUM_POSTE == poste]
        fig.add_scatter(x=s.fin, y=s.p_ete_min, mode="lines", name=d.nom(poste),
                        line=dict(color=COULEURS[groupe], width=3),
                        customdata=s[["debut", "koppen"]],
                        hovertemplate=(f"<b>{d.nom(poste)}</b><br>Normale %{{customdata[0]}}–%{{x}}"
                                       "<br>Mois d'été le plus sec : %{y:.0f} mm"
                                       "<br>Köppen : %{customdata[1]}<extra></extra>"))
        dernier = s.iloc[-1]
        fig.add_annotation(x=dernier.fin, y=dernier.p_ete_min, text=f"<b>{dernier.p_ete_min:.0f} mm</b>",
                           xanchor="left", xshift=6, showarrow=False,
                           font=dict(size=14, color=COULEURS[groupe]))

    _mise_en_page(fig, hovermode="closest")
    fig.update_xaxes(title=dict(text="Fin de la période de 30 ans", font=dict(size=13)))
    fig.update_yaxes(title=dict(text="Pluie du mois d'été le plus sec (mm)", font=dict(size=13)),
                     rangemode="tozero")

    nl, nm = d.normale(landes), d.normale(med)
    ecart = nl.p_ete_min - seuil
    if nl.mediterraneen:
        statut, libelle = "oui", "Oui"
        titre = f"{d.nom(landes)} a franchi le seuil méditerranéen"
    elif ecart <= 5:
        statut, libelle = "partiel", "Presque"
        titre = f"{d.nom(landes)} frôle le seuil méditerranéen, sans le franchir"
    else:
        statut, libelle = "non", "Non"
        titre = f"{d.nom(landes)} reste nettement au-dessus du seuil méditerranéen"
    lib_l = d.KOPPEN_LIBELLES.get(nl.koppen, nl.koppen)
    lib_m = d.KOPPEN_LIBELLES.get(nm.koppen, nm.koppen)
    chiffres = (f"{d.NORMALE_RECENTE[0]}–{d.NORMALE_RECENTE[1]} : {d.nom(landes)} {nl.p_ete_min:.0f} mm "
                f"({nl.koppen}, {lib_l}) · {d.nom(med)} {nm.p_ete_min:.0f} mm ({nm.koppen}, {lib_m})")
    return fig, Verdict(statut, libelle, titre, chiffres)


# --- 2. Gaussen : diagramme ombrothermique ---------------------------------------

def panneau_gaussen(landes: str, med: str) -> tuple[go.Figure, Verdict]:
    periode = d.NORMALE_RECENTE
    nl, nm = d.normale(landes), d.normale(med)
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04,
                        subplot_titles=[f"{d.nom(landes)} · {nl.n_mois_secs} mois sec(s)",
                                        f"{d.nom(med)} · {nm.n_mois_secs} mois sec(s)"])
    for col, (poste, groupe) in enumerate(((landes, "Landes"), (med, "Méditerranée")), start=1):
        c = d.climatologie(poste, periode)
        hover = [f"<b>{d.nom(poste)}</b> · {MOIS_LONGS[i]}<br>Pluie : {p:.0f} mm"
                 f"<br>Température : {t:.1f} °C (2T = {2 * t:.0f})"
                 f"<br>{'<b>Mois sec</b>' if p <= 2 * t else 'Mois humide'}"
                 for i, (p, t) in enumerate(zip(c.RR, c.TM))]
        # x numérique : les initiales des mois (J, M, A) se répètent.
        fig.add_bar(x=c.mois, y=c.RR, name="Pluie (mm)", marker_color=COULEURS[groupe],
                    marker_line_width=0, hovertext=hover, hoverinfo="text",
                    showlegend=False, row=1, col=col)
        fig.add_scatter(x=c.mois, y=2 * c.TM, mode="lines+markers", name="2 × température (°C)",
                        line=dict(color=ENCRE, width=2.5), marker=dict(size=8, color=ENCRE),
                        hovertext=hover, hoverinfo="text", showlegend=(col == 1), row=1, col=col)

    _mise_en_page(fig, bargap=0.2, hovermode="closest")
    fig.update_annotations(font=dict(size=14, color=ENCRE))
    fig.update_xaxes(tickfont=dict(size=12), tickmode="array", tickvals=list(range(1, 13)),
                     ticktext=MOIS)
    fig.update_yaxes(title=dict(text="mm  (échelle T = P/2)", font=dict(size=13)), row=1, col=1)
    fig.update_layout(legend=dict(y=-0.12, yanchor="top"), margin=dict(t=30))

    n_l = int(nl.n_mois_secs)
    if n_l >= 3:
        statut, libelle = "oui", "Oui"
        titre = f"{d.nom(landes)} a désormais un été sec, comme {d.nom(med)}"
    elif n_l >= 1:
        statut, libelle = "partiel", "En partie"
        liste = ", ".join(MOIS_LONGS[int(m) - 1] for m in nl.mois_secs.split(","))
        titre = (f"{d.nom(landes)} a désormais {n_l} mois sec{'s' if n_l > 1 else ''} ({liste}), "
                 f"{d.nom(med)} en a {int(nm.n_mois_secs)}")
    else:
        statut, libelle = "non", "Non"
        titre = f"À {d.nom(landes)}, la pluie reste au-dessus de la courbe de sécheresse toute l'année"
    chiffres = (f"Moyennes {periode[0]}–{periode[1]}. Un mois est sec quand la barre de pluie "
                f"passe sous la courbe 2 × température.")
    return fig, Verdict(statut, libelle, titre, chiffres)


# --- 3. Tendance : mois secs par an ---------------------------------------------

def panneau_tendance(landes: str, med: str) -> tuple[go.Figure, Verdict]:
    fig = go.Figure()
    for poste, groupe in ((landes, "Landes"), (med, "Méditerranée")):
        a = d.annuel[d.annuel.NUM_POSTE == poste].sort_values("annee")
        lisse = a.n_mois_secs.rolling(11, center=True, min_periods=6).mean()
        fig.add_scatter(x=a.annee, y=a.n_mois_secs, mode="markers", name=d.nom(poste),
                        marker=dict(color=COULEURS[groupe], size=7, opacity=0.25),
                        showlegend=False, customdata=a.mois_secs.fillna("aucun"),
                        hovertemplate=(f"<b>{d.nom(poste)}</b> %{{x}}<br>%{{y}} mois sec(s)"
                                       "<br>Mois : %{customdata}<extra></extra>"))
        fig.add_scatter(x=a.annee, y=lisse, mode="lines", name=f"{d.nom(poste)} (moyenne 11 ans)",
                        line=dict(color=COULEURS[groupe], width=3),
                        hovertemplate=f"{d.nom(poste)} · moyenne : %{{y:.1f}} mois<extra></extra>")
        fin = lisse.last_valid_index()
        fig.add_annotation(x=a.annee[fin], y=lisse[fin], text=f"<b>{_fmt(lisse[fin], 1)}</b>",
                           xanchor="left", xshift=6, showarrow=False,
                           font=dict(size=14, color=COULEURS[groupe]))

    _mise_en_page(fig, hovermode="closest")
    fig.update_xaxes(title=dict(text="Année", font=dict(size=13)))
    fig.update_yaxes(title=dict(text="Mois secs dans l'année", font=dict(size=13)),
                     range=[-0.3, 10.5], dtick=2)

    anc, rec = d.NORMALE_ANCIENNE, d.NORMALE_RECENTE
    l0, l1 = d.mois_secs_moyens(landes, anc), d.mois_secs_moyens(landes, rec)
    m0, m1 = d.mois_secs_moyens(med, anc), d.mois_secs_moyens(med, rec)
    ecart0, ecart1 = m0 - l0, m1 - l1
    if l1 - l0 < 0.15:
        statut, libelle = "non", "Non"
        titre = f"{d.nom(landes)} ne compte pas plus de mois secs qu'en 1950"
    elif ecart1 <= ecart0 / 2:
        statut, libelle = "oui", "Oui"
        titre = f"{d.nom(landes)} rattrape {d.nom(med)} : l'écart de sécheresse a fondu"
    else:
        statut, libelle = "partiel", "En partie"
        verbe = "se creuse" if ecart1 > ecart0 else "ne se réduit presque pas"
        titre = f"{d.nom(landes)} s'assèche, mais l'écart avec {d.nom(med)} {verbe}"
    chiffres = (f"Mois secs par an, {anc[0]}–{anc[1]} → {rec[0]}–{rec[1]} : "
                f"{d.nom(landes)} {_fmt(l0, 1)} → {_fmt(l1, 1)} · {d.nom(med)} {_fmt(m0, 1)} → {_fmt(m1, 1)}")
    return fig, Verdict(statut, libelle, titre, chiffres)


# --- 4. Feux : surface brûlée par an -------------------------------------------

def panneau_feux(landes: str, med: str) -> tuple[go.Figure, Verdict]:
    fig = go.Figure()
    f = d.feux_annuel
    series = {}
    for poste, groupe in ((landes, "Landes"), (med, "Méditerranée")):
        dep = d.departement(poste)
        s = f[f.departement == dep].sort_values("annee")
        series[groupe] = (dep, s)
        fig.add_bar(x=s.annee, y=s.surface_ha, name=f"{d.NOMS_DEPARTEMENTS[dep]} ({dep})",
                    marker_color=COULEURS[groupe], marker_line_width=0,
                    customdata=s[["n_feux", "n_feux_1ha", "plus_grand_feu_ha"]],
                    hovertemplate=(f"<b>{d.NOMS_DEPARTEMENTS[dep]}</b> %{{x}}"
                                   "<br>Surface brûlée : %{y:,.0f} ha"
                                   "<br>%{customdata[0]} feux, dont %{customdata[1]} ≥ 1 ha"
                                   "<br>Plus grand feu : %{customdata[2]:,.0f} ha<extra></extra>"))

    dep_l, s_l = series["Landes"]
    dep_m, s_m = series["Méditerranée"]
    pire = s_l.loc[s_l.surface_ha.idxmax()]
    # Sur un axe log, une annotation attend log10(y).
    fig.add_annotation(x=pire.annee, y=math.log10(pire.surface_ha), text=f"<b>{_fmt(pire.surface_ha)} ha</b>",
                       showarrow=False, xanchor="right", xshift=-12,
                       font=dict(size=14, color=COULEURS["Landes"]))

    _mise_en_page(fig, barmode="group", bargap=0.25, bargroupgap=0.08, hovermode="closest")
    fig.update_yaxes(type="log", title=dict(text="Surface brûlée (ha, échelle log)", font=dict(size=13)),
                     dtick=1, tickformat=",.0f", separatethousands=True)
    fig.update_xaxes(dtick=2, tickfont=dict(size=12))

    max_l, max_m = s_l.surface_ha.max(), s_m.surface_ha.max()
    nom_l, nom_m = d.NOMS_DEPARTEMENTS[dep_l], d.NOMS_DEPARTEMENTS[dep_m]
    dans_l, dans_m = d.DANS_DEPARTEMENT[dep_l], d.DANS_DEPARTEMENT[dep_m]
    ha_an_l, ha_an_m = s_l.surface_ha.median(), s_m.surface_ha.median()
    if max_l >= max_m and ha_an_l >= ha_an_m:
        statut, libelle = "oui", "Oui"
        titre = (f"Autant de surface brûlée {dans_l} que {dans_m}, "
                 "en année normale comme en année extrême")
    elif max_l >= 0.5 * max_m:
        statut, libelle = "partiel", "En partie"
        quantite = "plus" if max_l >= max_m else "presque autant"
        titre = (f"Peu de feux {dans_l} en année normale, mais en {int(pire.annee)} il y a brûlé "
                 f"{quantite} que lors de la pire année {dans_m}")
    else:
        statut, libelle = "non", "Non"
        titre = f"Bien moins de surface brûlée {dans_l} que {dans_m}, même en année extrême"
    chiffres = (f"2006–2025, année médiane : {nom_l} {_fmt(ha_an_l)} ha · {nom_m} {_fmt(ha_an_m)} ha · "
                f"pire année : {_fmt(max_l)} ha contre {_fmt(max_m)} ha")
    return fig, Verdict(statut, libelle, titre, chiffres)


# --- Page « Solutions » : cartes des secours -----------------------------------

CASERNE = "#52514e"
PROPOSE = COULEURS["Landes"]
GARDE = "#1f8a70"
AIRE_CANADAIR = "#d4a017"  # doré : se distingue du bleu et du vert, même pour les daltoniens
FEU = COULEURS["Méditerranée"]
CENTRE_CARTE = dict(lat=44.45, lon=-0.75)
TEMPS_VOL_KM = 50  # ≈ 10 min de vol à 300 km/h


def _cercle(lat: float, lon: float, rayon_km: float, n: int = 64) -> tuple[list, list]:
    angles = np.linspace(0, 2 * np.pi, n)
    dlat = rayon_km / 111.2
    dlon = rayon_km / (111.2 * np.cos(np.radians(lat)))
    return list(lat + dlat * np.sin(angles)), list(lon + dlon * np.cos(angles))


def _feux(fig: go.Figure, opacite: float) -> None:
    """Un rond par feu ≥ 1 ha, de surface proportionnelle à la surface brûlée."""
    f = d.feux_geo.sort_values("surface_ha", ascending=False)
    fig.add_scattermap(
        lat=f.lat, lon=f.lon, mode="markers", name="Feux ≥ 1 ha (2006–2025)",
        marker=dict(size=np.clip(np.sqrt(f.surface_ha) * 0.9, 4, 60), color=FEU, opacity=opacite),
        customdata=f[["commune", "annee", "surface_ha"]],
        hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]:,.0f} ha<extra>Feu</extra>")


def _rayons(fig: go.Figure, postes, couleur: str, nom_legende: str) -> None:
    """Zone couverte par chaque poste proposé (10 km pour une caserne, 5 km pour un garde)."""
    for i, poste in enumerate(postes.itertuples()):
        lat, lon = _cercle(poste.lat, poste.lon, poste.rayon_km)
        fig.add_scattermap(lat=lat, lon=lon, mode="lines", fill="toself", hoverinfo="skip",
                           line=dict(color=couleur, width=1), fillcolor="rgba(0,0,0,0)",
                           name=nom_legende, legendgroup=nom_legende, showlegend=i == 0)


def _casernes(fig: go.Figure, opacite: float) -> None:
    c = d.casernes[d.casernes.statut == "existante"]
    fig.add_scattermap(lat=c.lat, lon=c.lon, mode="markers", name="Casernes existantes",
                       marker=dict(size=7, color=CASERNE, opacity=opacite), text=c.nom,
                       hovertemplate="%{text}<extra>Caserne</extra>")


def _base_aerienne(fig: go.Figure, base, nom_legende: str, couleur: str, portee: bool) -> None:
    if portee:
        lat, lon = _cercle(base.lat, base.lon, TEMPS_VOL_KM)
        fig.add_scattermap(lat=lat, lon=lon, mode="lines", hoverinfo="skip", showlegend=False,
                           line=dict(color=couleur, width=1.5))
    fig.add_scattermap(lat=[base.lat], lon=[base.lon], mode="markers+text", name=nom_legende,
                       marker=dict(size=20, color=couleur), text=[base.nom.split(" — ")[-1]],
                       textposition="top center", textfont=dict(size=13, color=ENCRE),
                       customdata=[[base.description]],
                       hovertemplate="<b>%{text}</b><br>%{customdata[0]}<extra></extra>")


def _mise_en_page_carte(fig: go.Figure) -> go.Figure:
    _mise_en_page(fig, map=dict(style="carto-positron", center=CENTRE_CARTE, zoom=7.0))
    fig.update_layout(legend=dict(orientation="v", yanchor="top", y=0.99, xanchor="left", x=0.01,
                                  font=dict(size=12), bgcolor="rgba(252,252,251,0.9)"))
    return fig


def _base(nom: str):
    b = d.bases_aeriennes
    return b[b.nom.str.startswith(nom)].iloc[0]


def _part(colonne: str, seuil: float, au_dela: bool = True) -> float:
    g = d.grille_secours[colonne]
    return ((g > seuil) if au_dela else (g <= seuil)).mean() * 100


def carte_actuelle() -> tuple[go.Figure, Verdict]:
    fig = go.Figure()
    _feux(fig, 0.55)
    _casernes(fig, 0.9)
    _base_aerienne(fig, _base("Bordeaux-Mérignac"), "Pélicandrome (avions l'été seulement)",
                   ENCRE, portee=True)

    km2_10 = (d.grille_secours.dist_caserne_avant_km > 10).sum() * d.PAS_GRILLE_KM ** 2
    titre = (f"{_fmt(km2_10)} km² du massif à plus de 10 km d'une caserne, et "
             f"{_fmt(_part('dist_caserne_avant_km', 5))} % du massif à plus de 5 km")
    chiffres = (f"{(d.casernes.statut == 'existante').sum()} casernes · Canadair basés à Nîmes "
                f"({_fmt(_base('Nîmes').temps_vol_min)} min de vol) · seulement "
                f"{_fmt(_part('dist_air_avant_km', TEMPS_VOL_KM, au_dela=False))} % du massif "
                f"à moins de 10 min de vol de Mérignac (cercle)")
    return _mise_en_page_carte(fig), Verdict("non", "", titre, chiffres)


def carte_solution() -> tuple[go.Figure, Verdict]:
    fig = go.Figure()
    _feux(fig, 0.25)
    _casernes(fig, 0.35)
    p = d.casernes[d.casernes.statut == "proposee"].sort_values("rang")
    _rayons(fig, p[p.type == "caserne"], PROPOSE, "Rayon de 10 km (casernes)")
    _rayons(fig, p[p.type == "garde"], GARDE, "Rayon de 5 km (gardes)")
    for type_poste, couleur, nom_legende in (("caserne", PROPOSE, "Casernes proposées"),
                                             ("garde", GARDE, "Postes de gardes forestiers")):
        q = p[p.type == type_poste]
        fig.add_scattermap(lat=q.lat, lon=q.lon, mode="markers+text", name=nom_legende,
                           marker=dict(size=18, color=couleur), text=q.rang.astype(int).astype(str),
                           textfont=dict(size=11, color="white"), customdata=q[["nom", "rayon_km"]],
                           hovertemplate="<b>%{customdata[0]}</b><br>Couvre %{customdata[1]:.0f} km"
                                         "<extra></extra>")
    _base_aerienne(fig, _base("Bordeaux-Mérignac"), "Pélicandrome de Mérignac", ENCRE, portee=True)
    _base_aerienne(fig, _base("Aire Canadair"), "Aire Canadair proposée", AIRE_CANADAIR, portee=True)

    n_c, n_g = (p.type == "caserne").sum(), (p.type == "garde").sum()
    sabres = _base("Aire Canadair").nom.split(" — ")[-1]
    titre = (f"{n_c} casernes et {n_g} postes de gardes forestiers en plus : "
             f"{_fmt(_part('dist_caserne_apres_km', 10), 1)} % du massif à plus de 10 km "
             f"des pompiers (contre {_fmt(_part('dist_caserne_avant_km', 10), 1)} %)")
    chiffres = (f"À plus de 5 km : {_fmt(_part('dist_caserne_avant_km', 5))} → "
                f"{_fmt(_part('dist_caserne_apres_km', 5))} % · avec une aire Canadair à {sabres}, "
                f"à moins de 10 min de vol d'une base : "
                f"{_fmt(_part('dist_air_avant_km', TEMPS_VOL_KM, au_dela=False))} → "
                f"{_fmt(_part('dist_air_apres_km', TEMPS_VOL_KM, au_dela=False))} % du massif")
    return _mise_en_page_carte(fig), Verdict("oui", "", titre, chiffres)
