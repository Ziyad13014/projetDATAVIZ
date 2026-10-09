"""Dashboard Streamlit + Altair : Landes de Gascogne vs Alpes-Maritimes face aux incendies.

Lancement (depuis le dossier projet/) : streamlit run app_altair/app.py  puis http://localhost:8501
"""
import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from common import (ANNEE_MAX, ANNEE_MIN, COULEUR_DEP, COULEUR_STATION, COULEUR_STATUT,  # noqa: E402
                    COULEUR_TERRITOIRE, DIVERGENTE, GRID, INK, LIMITES, MUTED, PROBLEMATIQUE, PUBLIC, ROOT,
                    SOURCES, TERRITOIRES, TITRE, kpis, load, pct, recommandations, tuiles)

st.set_page_config(page_title="Incendies : Landes vs Côte d'Azur", layout="wide")
alt.data_transformers.disable_max_rows()
ORDRE_DEP = ["Landes", "Gironde", "Alpes-Maritimes"]


@alt.theme.register("projet", enable=True)
def theme():
    return alt.theme.ThemeConfig({"config": {
        "font": 'system-ui, -apple-system, "Segoe UI", sans-serif',
        "view": {"stroke": None},
        "axis": {"gridColor": GRID, "domainColor": GRID, "tickColor": GRID, "labelColor": MUTED,
                 "titleColor": MUTED, "titleFontWeight": "normal"},
        "axisX": {"grid": False},
        "legend": {"orient": "top", "title": None, "labelColor": INK},
        "title": {"anchor": "start", "color": INK, "fontSize": 14, "fontWeight": 600},
    }})


@st.cache_data
def donnees():
    d = load()
    geo = json.load(open(ROOT / "data" / "raw" / "geo" / "departements.geojson", encoding="utf-8"))
    d["geo"] = {t: [f for f in geo["features"] if f["properties"]["code"] in deps]
                for t, deps in {"Landes de Gascogne": ("33", "40"), "Alpes-Maritimes": ("06",)}.items()}
    return d


D = donnees()
K = kpis(D)


def echelle(mapping):
    return alt.Scale(domain=list(mapping), range=list(mapping.values()))


def afficher(chart):
    st.altair_chart(chart, use_container_width=True)


def fond(territoire):
    return alt.Chart(alt.Data(values=D["geo"][territoire])).mark_geoshape(
        fill="#f4f4f1", stroke="#c3c2b7", strokeWidth=1)


# ---------- En-tête, KPI et filtres ----------
st.title(TITRE)
st.markdown(f"**{PROBLEMATIQUE}**  \nPublic : {PUBLIC}. Comparaison avec les Alpes-Maritimes, "
            "territoire méditerranéen habitué aux feux.")

for col, (label, valeur, detail) in zip(st.columns(5), tuiles(K)):
    with col.container(border=True):
        st.metric(label, valeur)
        st.caption(detail)

with st.sidebar:
    st.header("Filtres")
    periode = st.slider("Période des incendies", ANNEE_MIN, ANNEE_MAX, (ANNEE_MIN, ANNEE_MAX))
    territoire = st.radio("Territoire des cartes", TERRITOIRES)
    log = st.toggle("Échelle logarithmique des surfaces", False,
                    help="Utile pour comparer les années autres que 2022.")
    hors_2022 = st.toggle("Exclure 2022 (année exceptionnelle)", False)
    st.caption("Astuce : sélectionnez des années à la souris sur le graphique des surfaces "
               "pour filtrer la carte et le classement des communes.")

# ---------- 1. Climat ----------
st.header("1. Le climat : des étés landais plus chauds que ceux de Nice")
st.caption("Courbe = moyenne glissante sur 10 ans, points = chaque été. Cliquez sur la légende pour isoler une station.")

clim = D["climat"].dropna(subset=["j30"])
sel_station = alt.selection_point(fields=["station"], bind="legend")
base = alt.Chart(clim).encode(
    x=alt.X("annee:Q", title=None, axis=alt.Axis(format="d"), scale=alt.Scale(zero=False)),
    color=alt.Color("station:N", scale=echelle(COULEUR_STATION)),
    opacity=alt.condition(sel_station, alt.value(1), alt.value(0.12)))
normale = alt.Chart(pd.DataFrame({"a": [1961], "b": [1990], "t": ["Normale 1961-1990"]})).encode(
    x="a:Q", x2="b:Q")
afficher((normale.mark_rect(color="#f0efec")
          + normale.mark_text(align="left", dx=4, y=8, color=MUTED).encode(text="t:N")
          + base.mark_circle(size=22, opacity=.35).encode(
              y=alt.Y("j30:Q", title="Jours ≥ 30 °C (juin-août)"),
              tooltip=[alt.Tooltip("station:N"), alt.Tooltip("annee:Q", title="Année"),
                       alt.Tooltip("j30:Q", title="Jours ≥ 30 °C")])
          + base.mark_line(strokeWidth=2.5).encode(
              y="j30_moy10:Q", tooltip=[alt.Tooltip("station:N"), alt.Tooltip("annee:Q", title="Année"),
                                        alt.Tooltip("j30_moy10:Q", title="Moyenne 10 ans", format=".1f")])
          ).add_params(sel_station).properties(height=320))

st.subheader("Écart de température annuelle à la normale 1961-1990")
afficher(alt.Chart(D["climat"].dropna(subset=["anomalie"])).mark_rect().encode(
    x=alt.X("annee:O", title=None, axis=alt.Axis(values=list(range(1950, 2030, 10)), labelAngle=0)),
    y=alt.Y("station:N", title=None, sort=list(COULEUR_STATION)),
    color=alt.Color("anomalie:Q", title="Écart (°C)", scale=alt.Scale(
        domain=[-2.5, 2.5], domainMid=0, range=DIVERGENTE, clamp=True, interpolate="rgb")),
    tooltip=[alt.Tooltip("station:N"), alt.Tooltip("annee:O", title="Année"),
             alt.Tooltip("anomalie:Q", title="Écart (°C)", format="+.1f")],
).properties(height=150))

# ---------- 2. Incendies ----------
st.header("2. Les incendies : moins de départs, mais des feux plus grands")
st.caption("Les Landes de Gascogne brûlent régulièrement plus que les Alpes-Maritimes, et 2022 change d'échelle.")

fa = D["feux_an"][D["feux_an"].annee.between(*periode)]
if hors_2022:
    fa = fa[fa.annee != 2022]
brush = alt.selection_interval(encodings=["x"])
barres = alt.Chart(fa).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
    x=alt.X("annee:O", title=None, axis=alt.Axis(labelAngle=0)),
    xOffset=alt.XOffset("territoire:N", sort=TERRITOIRES),
    y=alt.Y("surface_ha:Q", title="Surface brûlée (ha)",
            scale=alt.Scale(type="symlog") if log else alt.Scale()),
    color=alt.Color("territoire:N", scale=echelle(COULEUR_TERRITOIRE), sort=TERRITOIRES),
    opacity=alt.condition(brush, alt.value(1), alt.value(.3)),
    tooltip=[alt.Tooltip("territoire:N"), alt.Tooltip("annee:O", title="Année"),
             alt.Tooltip("surface_ha:Q", title="Surface (ha)", format=",.0f"),
             alt.Tooltip("nb_feux:Q", title="Nombre de feux"),
             alt.Tooltip("grands_feux:Q", title="Feux ≥ 100 ha"),
             alt.Tooltip("plus_gros_feu_ha:Q", title="Plus gros feu (ha)", format=",.0f")],
).add_params(brush).properties(height=300)

f = D["feux"]
f = f[(f.territoire == territoire) & f.annee.between(*periode)].dropna(subset=["lat"])
if hors_2022:
    f = f[f.annee != 2022]
com = f.groupby(["commune", "lat", "lon", "annee"]).surface_ha.agg(["sum", "size"]).reset_index().rename(
    columns={"sum": "surface_ha", "size": "nb"})
filtre = alt.Chart(com).transform_filter(brush).transform_aggregate(
    surface_ha="sum(surface_ha)", nb="sum(nb)", groupby=["commune", "lat", "lon"])
cas = D["casernes"][D["casernes"].territoire == territoire]
pts_cas = alt.Chart(cas).mark_point(shape="cross", size=30, color=INK, opacity=.6, filled=True).encode(
    longitude="lon:Q", latitude="lat:Q", tooltip=[alt.Tooltip("nom:N", title="Centre de secours")])
bulles = filtre.mark_circle(color=COULEUR_TERRITOIRE[territoire], opacity=.55, stroke="white",
                            strokeWidth=1).encode(
    longitude="lon:Q", latitude="lat:Q",
    size=alt.Size("surface_ha:Q", title="Surface brûlée (ha)", scale=alt.Scale(range=[10, 1800])),
    tooltip=[alt.Tooltip("commune:N"), alt.Tooltip("surface_ha:Q", title="Surface (ha)", format=",.0f"),
             alt.Tooltip("nb:Q", title="Nombre de feux")])
carte = (fond(territoire) + bulles + pts_cas).project("mercator").properties(
    height=430, title="Surface brûlée par commune (croix = centres de secours)")
top = filtre.transform_window(rang="rank(surface_ha)", sort=[alt.SortField("surface_ha", order="descending")]
                              ).transform_filter("datum.rang <= 12").mark_bar(
    color=COULEUR_TERRITOIRE[territoire], cornerRadiusEnd=3).encode(
    y=alt.Y("commune:N", sort="-x", title=None), x=alt.X("surface_ha:Q", title="Surface brûlée (ha)"),
    tooltip=[alt.Tooltip("commune:N"), alt.Tooltip("surface_ha:Q", format=",.0f", title="Surface (ha)")],
).properties(height=430, title="Communes les plus touchées")
afficher(alt.vconcat(barres, alt.hconcat(carte, top).resolve_scale(size="independent")
                     ).resolve_scale(color="independent"))

with st.expander("Voir les données annuelles (tableau)"):
    st.dataframe(fa.pivot(index="annee", columns="territoire", values="surface_ha").round(0),
                 use_container_width=True)

st.subheader("Nature des feux : 2006-2015 contre 2016-2025")
nat = D["nature"][D["nature"].variante == ("hors 2022" if hors_2022 else "toutes années")]


def barres_nature(col, titre):
    b = alt.Chart(nat).encode(
        x=alt.X("periode:N", title=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("territoire:N", sort=TERRITOIRES),
        y=alt.Y(f"{col}:Q", title=None),
        color=alt.Color("territoire:N", scale=echelle(COULEUR_TERRITOIRE), sort=TERRITOIRES),
        tooltip=[alt.Tooltip("territoire:N"), alt.Tooltip("periode:N", title="Période"),
                 alt.Tooltip(f"{col}:Q", title=titre, format=".1f")])
    return (b.mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            + b.mark_text(dy=-6).encode(text=alt.Text(f"{col}:Q", format=".1f"), color=alt.value(MUTED))
            ).properties(height=260, title=titre)


afficher(alt.hconcat(barres_nature("feux_par_an", "Nombre de feux par an"),
                     barres_nature("surface_moyenne_par_feu_ha", "Surface moyenne par feu (ha)")))
st.caption("Même sans 2022, la surface moyenne par feu augmente dans les deux territoires (+56 % dans les Landes "
           "de Gascogne, +75 % dans les Alpes-Maritimes), alors que le nombre de départs baisse : les feux "
           "deviennent plus difficiles à contenir partout.")

st.subheader("Chaleur de l'été et surface brûlée")
st.caption("Un point par année et par territoire. Le lien existe dans les Landes (r ≈ 0,4) mais reste modéré ; "
           "aucun lien visible dans les Alpes-Maritimes avec la station littorale de Nice.")
cl = D["climat"]
ete = pd.concat([
    cl[cl.station == "Nice"].assign(territoire="Alpes-Maritimes"),
    cl[cl.station.isin(["Bordeaux-Mérignac", "Mont-de-Marsan"])].assign(territoire="Landes de Gascogne"),
]).groupby(["territoire", "annee"]).j30.mean().reset_index()
nuage = D["feux_an"].merge(ete, on=["territoire", "annee"])
sel_terr = alt.selection_point(fields=["territoire"], bind="legend")
pts = alt.Chart(nuage).encode(
    x=alt.X("j30:Q", title="Jours ≥ 30 °C dans l'été"),
    y=alt.Y("surface_ha:Q", title="Surface brûlée (ha, échelle log)", scale=alt.Scale(type="log"),
            axis=alt.Axis(values=[10, 100, 1000, 10000, 100000], format=",.0f")),
    color=alt.Color("territoire:N", scale=echelle(COULEUR_TERRITOIRE), sort=TERRITOIRES),
    opacity=alt.condition(sel_terr, alt.value(1), alt.value(.1)))
afficher((pts.mark_circle(size=90, stroke="white", strokeWidth=2).encode(
    tooltip=[alt.Tooltip("territoire:N"), alt.Tooltip("annee:Q", title="Année"),
             alt.Tooltip("j30:Q", title="Jours ≥ 30 °C", format=".0f"),
             alt.Tooltip("surface_ha:Q", title="Surface (ha)", format=",.0f")])
    + pts.mark_text(dy=-10, fontSize=10, color=MUTED).encode(text="annee:Q")
).add_params(sel_terr).properties(height=360))

# ---------- 3. Prévention ----------
st.header("3. La prévention : des plans quasi absents du massif landais")
st.caption(f"Communes classées à risque feu de forêt et état de leur plan de prévention des risques d'incendie "
           f"(PPRIF). Dans les Landes, {K['plan_landes']} commune sur {K['risque_landes']} en a un. Le plan de "
           "La Teste-de-Buch, prescrit en 2007, n'était toujours pas approuvé lors des feux de 2022.")
prev = D["prevention"].assign(departement=lambda x: x.dep.map(
    {"06": "Alpes-Maritimes", "33": "Gironde", "40": "Landes"}))
statuts = [s for s in COULEUR_STATUT if s != "Non classée à risque"]
g, d = st.columns([5, 7])
with g:
    n = prev[prev.statut != "Non classée à risque"].groupby(["departement", "statut"]).size().reset_index(
        name="communes")
    n["ordre"] = n.statut.map({s: i for i, s in enumerate(statuts)})
    afficher(alt.Chart(n).mark_bar(stroke="white", strokeWidth=2).encode(
        y=alt.Y("departement:N", title=None, sort=ORDRE_DEP),
        x=alt.X("communes:Q", title="Communes classées à risque feu de forêt"),
        color=alt.Color("statut:N", scale=alt.Scale(domain=statuts, range=[COULEUR_STATUT[s] for s in statuts]),
                        legend=alt.Legend(orient="top", columns=1)),
        order=alt.Order("ordre:Q"),
        tooltip=[alt.Tooltip("departement:N", title="Département"), alt.Tooltip("statut:N", title="Statut"),
                 alt.Tooltip("communes:Q", title="Communes")],
    ).properties(height=260))
    st.caption(f"{pct(K['part_brule_sans_plan_lg'])} de la surface brûlée des Landes de Gascogne depuis 2006 l'a été "
               "dans des communes sans plan approuvé. Attention : presque aucune commune n'en a, ce chiffre ne "
               "prouve donc pas que les plans sont efficaces.")
with d:
    p = prev[prev.territoire == territoire]
    tout = list(COULEUR_STATUT)
    afficher((fond(territoire) + alt.Chart(p).mark_circle(stroke="white", strokeWidth=.8, opacity=.85).encode(
        longitude="lon:Q", latitude="lat:Q",
        color=alt.Color("statut:N", scale=alt.Scale(domain=tout, range=[COULEUR_STATUT[s] for s in tout]),
                        title=None),
        size=alt.Size("surface_brulee_ha:Q", title="Surface brûlée 2006-2025 (ha)",
                      scale=alt.Scale(range=[15, 1500])),
        order=alt.Order("surface_brulee_ha:Q"),
        tooltip=[alt.Tooltip("commune:N", title="Commune"), alt.Tooltip("statut:N", title="Statut"),
                 alt.Tooltip("surface_brulee_ha:Q", title="Surface brûlée (ha)", format=",.0f")],
    )).project("mercator").properties(height=460, title="Statut de prévention par commune"))

# ---------- 4. Moyens ----------
st.header("4. Les moyens : un territoire immense pour peu de pompiers")
st.caption("Les Landes ont beaucoup de pompiers par habitant, mais très peu par km² de territoire à défendre, "
           "et surtout des volontaires. Le budget rattrape son retard depuis 2022.")
c1, c2, c3 = st.columns(3)
pomp = D["pompiers"]
with c1:
    b = alt.Chart(pomp).encode(
        x=alt.X("departement:N", title=None, sort=ORDRE_DEP, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("pompiers_1000km2:Q", title=None),
        color=alt.Color("departement:N", scale=echelle(COULEUR_DEP), legend=None),
        tooltip=[alt.Tooltip("departement:N", title="Département"),
                 alt.Tooltip("pompiers:Q", title="Sapeurs-pompiers", format=",.0f"),
                 alt.Tooltip("pompiers_1000km2:Q", title="Pour 1 000 km²", format=".0f"),
                 alt.Tooltip("pompiers_100k_hab:Q", title="Pour 100 000 hab.", format=".0f"),
                 alt.Tooltip("part_volontaires:Q", title="Volontaires", format=".0%")])
    afficher((b.mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, size=50)
              + b.mark_text(dy=-6).encode(text=alt.Text("pompiers_1000km2:Q", format=".0f"), color=alt.value(MUTED))
              ).properties(height=300, title="Sapeurs-pompiers pour 1 000 km² (2024)"))


def ligne_budget(col, titre):
    bb = alt.Chart(D["budget"]).encode(
        x=alt.X("annee:Q", title=None, axis=alt.Axis(format="d"), scale=alt.Scale(zero=False)),
        y=alt.Y(f"{col}:Q", title="€ par habitant", scale=alt.Scale(zero=False)),
        color=alt.Color("departement:N", scale=echelle(COULEUR_DEP)),
        tooltip=[alt.Tooltip("departement:N", title="SDIS"), alt.Tooltip("annee:Q", title="Année"),
                 alt.Tooltip(f"{col}:Q", title="€/hab", format=".1f")])
    regle = alt.Chart(pd.DataFrame({"x": [2022]})).mark_rule(color=MUTED).encode(x="x:Q")
    return (bb.mark_line(strokeWidth=2.5) + bb.mark_point(filled=True, size=45) + regle).properties(
        height=300, title=titre)


with c2:
    afficher(ligne_budget("depenses_totales", "Dépenses totales du SDIS par habitant"))
with c3:
    afficher(ligne_budget("vehicules", "Achats de véhicules par habitant"))
st.markdown("**Moyens aériens**")
for r in D["aerien"].itertuples():
    st.markdown(f"- **{r.base}** : {r.moyens} ({r.statut.lower()})")

# ---------- 5. Recommandations ----------
st.header("5. Recommandations")
st.caption("Chaque action découle d'un constat chiffré du tableau de bord.")
cols = st.columns(3)
for i, (titre, constat, action) in enumerate(recommandations(K)):
    with cols[i % 3].container(border=True):
        st.markdown(f"**{titre}**")
        st.caption(constat)
        st.markdown(f"**Action :** {action}")

# ---------- 6. Limites ----------
st.header("6. Limites et sources")
st.markdown("\n".join(f"- {lim}" for lim in LIMITES))
st.caption("Sources : " + " · ".join(f"[{n}]({u})" for n, u in SOURCES))
