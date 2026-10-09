"""Préparation des données du projet « Landes vs Alpes-Maritimes ».

Lit les fichiers bruts de data/raw/ et écrit des tables propres dans data/processed/,
utilisées à l'identique par l'app Dash et l'app Streamlit + Altair.

Usage : python src/prepare_data.py
"""
from pathlib import Path
import glob
import json

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

DEPS = ["06", "33", "40"]
TERRITOIRE = {"06": "Alpes-Maritimes", "33": "Landes de Gascogne", "40": "Landes de Gascogne"}
NOM_DEP = {"06": "Alpes-Maritimes", "33": "Gironde", "40": "Landes"}

# Une station de référence par département : séries longues et quasi complètes.
STATIONS = {
    6088001: ("Nice", "06"),
    33281001: ("Bordeaux-Mérignac", "33"),
    40192001: ("Mont-de-Marsan", "40"),
}
NORMALE = (1961, 1990)  # période de référence climatique (OMM)
SEUIL_GRAND_FEU_HA = 100


def climat():
    cols = ["NUM_POSTE", "AAAAMM", "TM", "TX", "RR", "NBJTX30", "NBJTX35", "NBJTNS20", "NBJGELEE"]
    files = [f for d in DEPS for f in glob.glob(str(RAW / f"MENSQ_{d}_*.csv.gz"))]
    m = pd.concat(pd.read_csv(f, sep=";", usecols=cols, low_memory=False) for f in files)
    m = m[m.NUM_POSTE.isin(STATIONS)].drop_duplicates(["NUM_POSTE", "AAAAMM"])
    m["annee"] = m.AAAAMM // 100
    m["mois"] = m.AAAAMM % 100
    m["station"] = m.NUM_POSTE.map(lambda s: STATIONS[s][0])
    m["dep"] = m.NUM_POSTE.map(lambda s: STATIONS[s][1])
    m["territoire"] = m.dep.map(TERRITOIRE)

    # Année complète (12 mois de TM) -> anomalie de température moyenne annuelle
    an = m.groupby(["station", "dep", "territoire", "annee"]).agg(
        n=("TM", "count"), tm=("TM", "mean"), gel=("NBJGELEE", "sum"))
    an = an[an.n == 12].drop(columns="n").reset_index()
    ref = an[an.annee.between(*NORMALE)].groupby("station").tm.mean()
    an["anomalie"] = an.tm - an.station.map(ref)

    # Été (juin-août complet)
    ete = m[m.mois.isin([6, 7, 8])].groupby(["station", "annee"]).agg(
        n=("TX", "count"), tx_ete=("TX", "mean"), j30=("NBJTX30", "sum"),
        j35=("NBJTX35", "sum"), nuits_trop=("NBJTNS20", "sum"), rr_ete=("RR", "sum"))
    ete = ete[ete.n == 3].drop(columns="n").reset_index()

    df = an.merge(ete, on=["station", "annee"], how="outer")
    for c in ["dep", "territoire"]:
        df[c] = df.station.map(an.drop_duplicates("station").set_index("station")[c])
    df = df[df.annee >= 1950].sort_values(["station", "annee"])
    df["j30_moy10"] = df.groupby("station").j30.transform(lambda s: s.rolling(10, min_periods=7).mean())
    df.round(2).to_csv(OUT / "climat_stations.csv", index=False)
    return df


def communes():
    rows = []
    for d in DEPS:
        for c in json.load(open(RAW / "geo" / f"communes_{d}.json", encoding="utf-8")):
            lon, lat = c["centre"]["coordinates"]
            rows.append({"insee": c["code"], "commune": c["nom"], "dep": d, "lat": lat, "lon": lon,
                         "surface_km2": c.get("surface", np.nan) / 100, "population": c.get("population")})
    return pd.DataFrame(rows)


def incendies(com):
    f = pd.read_csv(RAW / "BDIFF_incendies_06_33_40_2006-2025.csv", sep=";", skiprows=3,
                    dtype={"Département": str, "Code INSEE": str})
    f = f.rename(columns={
        "Année": "annee", "Département": "dep", "Code INSEE": "insee", "Nom de la commune": "commune_bdiff",
        "Date de première alerte": "date", "Nature": "cause",
        "Nombre de bâtiments totalement détruits": "bat_detruits", "Nombre de décès": "deces"})
    f["surface_ha"] = f["Surface parcourue (m2)"] / 1e4
    f["surface_foret_ha"] = f["Surface forêt (m2)"].fillna(0) / 1e4
    f["date"] = pd.to_datetime(f["date"], errors="coerce")
    f["mois"] = f.date.dt.month
    f["cause"] = f.cause.fillna("Inconnue")
    f["territoire"] = f.dep.map(TERRITOIRE)
    f["grand_feu"] = f.surface_ha >= SEUIL_GRAND_FEU_HA
    f = f.merge(com[["insee", "commune", "lat", "lon"]], on="insee", how="left")
    f["commune"] = f.commune.fillna(f.commune_bdiff)
    keep = ["annee", "date", "mois", "dep", "territoire", "insee", "commune", "lat", "lon",
            "surface_ha", "surface_foret_ha", "grand_feu", "cause", "deces", "bat_detruits"]
    f[keep].to_csv(OUT / "incendies.csv", index=False)
    print(f"incendies : {len(f)} feux, {f.lat.isna().sum()} sans coordonnées (communes fusionnées)")

    agg = dict(nb_feux=("surface_ha", "size"), surface_ha=("surface_ha", "sum"),
               grands_feux=("grand_feu", "sum"), plus_gros_feu_ha=("surface_ha", "max"))
    f.groupby(["territoire", "annee"]).agg(**agg).reset_index().round(1).to_csv(
        OUT / "incendies_annuel_territoire.csv", index=False)
    f.groupby(["dep", "annee"]).agg(**agg).reset_index().round(1).to_csv(
        OUT / "incendies_annuel_dep.csv", index=False)
    return f


def casernes():
    geo = json.load(open(RAW / "geo" / "departements.geojson", encoding="utf-8"))
    polys = {ft["properties"]["code"]: shape(ft["geometry"]) for ft in geo["features"]
             if ft["properties"]["code"] in DEPS}
    rows = []
    for e in json.load(open(RAW / "osm" / "fire_stations_06_33_40.json", encoding="utf-8"))["elements"]:
        t = e.get("tags", {})
        lat, lon = (e["lat"], e["lon"]) if "lat" in e else (e["center"]["lat"], e["center"]["lon"])
        op = t.get("operator", "")
        # On garde les centres des SDIS : on écarte aéroports (SSLIA, DGAC) et pompiers de Paris (BSPP)
        if op and not op.replace(" ", "").startswith("SDIS"):
            continue
        if t.get("fire_station:type:FR") in ("SSLIA",):
            continue
        dep = next((d for d, p in polys.items() if p.contains(Point(lon, lat))), None)
        if dep is None:
            continue
        rows.append({"nom": t.get("name", "Centre de secours"), "type": t.get("fire_station:type:FR", "n.c."),
                     "dep": dep, "territoire": TERRITOIRE[dep], "lat": lat, "lon": lon})
    c = pd.DataFrame(rows).drop_duplicates(["lat", "lon"])
    c.to_csv(OUT / "casernes.csv", index=False)
    return c


def budget_sdis():
    d = pd.read_csv(RAW / "ofgl_sdis.csv", sep=";", low_memory=False, dtype={"Code Département": str})
    d = d[d["Code Département"].isin(DEPS)]
    aggs = {"Dépenses totales": "depenses_totales", "Dépenses de fonctionnement": "fonctionnement",
            "Dépenses d'investissement hors remb": "investissement", "Frais de personnel": "personnel",
            "Dépenses d'équipement - véhicules": "vehicules"}
    d = d[d["Agrégat"].isin(aggs)]
    p = d.pivot_table(index=["Code Département", "Exercice"], columns="Agrégat",
                      values="Montant en € par habitant", aggfunc="sum").rename(columns=aggs).reset_index()
    p = p.rename(columns={"Code Département": "dep", "Exercice": "annee"})
    p["departement"] = p.dep.map(NOM_DEP)
    p.round(1).to_csv(OUT / "budget_sdis.csv", index=False)
    return p


def indicateurs_territoire(com, cas):
    t = com.assign(territoire=com.dep.map(TERRITOIRE)).groupby("territoire").agg(
        surface_km2=("surface_km2", "sum"), population=("population", "sum"))
    t["casernes"] = cas.groupby("territoire").size()
    t["casernes_par_1000km2"] = t.casernes / t.surface_km2 * 1000
    t["casernes_par_100k_hab"] = t.casernes / t.population * 1e5
    t.round(1).reset_index().to_csv(OUT / "territoires.csv", index=False)
    return t


def nature_feux(feux):
    """Nombre de feux et surface moyenne par feu, par décennie, avec et sans 2022."""
    rows = []
    for (terr, per), g in feux.assign(
            periode=np.where(feux.annee <= 2015, "2006-2015", "2016-2025")).groupby(["territoire", "periode"]):
        for variante, gg in [("toutes années", g), ("hors 2022", g[g.annee != 2022])]:
            n_ans = 9 if (variante == "hors 2022" and per == "2016-2025") else 10
            rows.append({"territoire": terr, "periode": per, "variante": variante,
                         "feux_par_an": len(gg) / n_ans, "surface_par_an_ha": gg.surface_ha.sum() / n_ans,
                         "surface_moyenne_par_feu_ha": gg.surface_ha.mean(),
                         "grands_feux": int(gg.grand_feu.sum())})
    out = pd.DataFrame(rows).round(2)
    out.to_csv(OUT / "nature_feux.csv", index=False)
    return out


def prevention(com, feux):
    """GASPAR : communes classées à risque feu de forêt (DDRM) et plans de prévention (PPRIF)."""
    g = RAW / "gaspar"
    ddrm = pd.read_csv(next(g.glob("ddrm_risq_gaspar_*.csv")), sep=";", dtype=str)
    risque = set(ddrm[ddrm.lib_risque.str.contains("Feu de forêt", case=False, na=False)].cod_commune)

    p = pd.read_csv(next(g.glob("pprn_gaspar_*.csv")), sep=";", dtype=str, low_memory=False)
    est_ff = p["LIBELLE MODELE"].str.contains("Feu de For", na=False) | p[
        ["LIBELLE RISQUE 1", "LIBELLE RISQUE 2", "LIBELLE RISQUE 3"]].apply(
        lambda c: c.str.contains("orêt", na=False)).any(axis=1)
    p = p[est_ff & p["CODE INSEE DEPARTEMENT"].isin(DEPS)]
    p = p[p["LIBELLE ETAT"].isin(["Opposable", "Prescrit"])]
    rang = {"Opposable": 0, "Prescrit": 1}
    p = p.assign(r=p["LIBELLE ETAT"].map(rang)).sort_values("r").drop_duplicates("CODE INSEE COMMUNE")
    plans = p.set_index("CODE INSEE COMMUNE")[["LIBELLE ETAT", "APPROBATION", "PRESCRIPTION"]]

    c = com.copy()
    c["territoire"] = c.dep.map(TERRITOIRE)
    c["a_risque"] = c.insee.isin(risque)
    c = c.join(plans, on="insee")
    c["statut"] = np.select(
        [c["LIBELLE ETAT"] == "Opposable", c["LIBELLE ETAT"] == "Prescrit", c.a_risque],
        ["Plan approuvé", "Plan prescrit, non approuvé", "À risque, sans plan"], "Non classée à risque")
    c["annee_approbation"] = pd.to_numeric(c.APPROBATION.str[:4], errors="coerce")
    c["annee_prescription"] = pd.to_numeric(c.PRESCRIPTION.str[:4], errors="coerce")
    brule = feux.groupby("insee").surface_ha.sum()
    c["surface_brulee_ha"] = c.insee.map(brule).fillna(0).round(1)
    c = c.drop(columns=["LIBELLE ETAT", "APPROBATION", "PRESCRIPTION"])
    c.to_csv(OUT / "prevention_communes.csv", index=False)

    r = c.groupby("dep").agg(communes=("insee", "size"), a_risque=("a_risque", "sum"),
                             plan_approuve=("statut", lambda s: (s == "Plan approuvé").sum()),
                             plan_prescrit=("statut", lambda s: (s == "Plan prescrit, non approuvé").sum()),
                             derniere_approbation=("annee_approbation", "max")).reset_index()
    r["departement"] = r.dep.map(NOM_DEP)
    r["part_risque_couverte"] = (r.plan_approuve / r.a_risque).round(3)
    r.to_csv(OUT / "prevention_dep.csv", index=False)
    print(r.to_string())
    return c


def pompiers(com):
    """Effectifs 2024 (DGSCGC, édition 2025) rapportés à la population et à la surface."""
    s = pd.read_csv(RAW / "dgscgc_stats_sdis_2024.csv", dtype={"dep": str})
    t = com.groupby("dep").agg(population=("population", "sum"), surface_km2=("surface_km2", "sum"))
    s = s.join(t, on="dep")
    s["pompiers"] = s.spp_spm + s.spv_spr
    s["pompiers_100k_hab"] = s.pompiers / s.population * 1e5
    s["pompiers_1000km2"] = s.pompiers / s.surface_km2 * 1e3
    s["part_volontaires"] = s.spv_spr / s.pompiers
    s["departement"] = s.dep.map(NOM_DEP)
    s["territoire"] = s.dep.map(TERRITOIRE)
    s.round(3).to_csv(OUT / "pompiers_2024.csv", index=False)
    return s


if __name__ == "__main__":
    clim = climat()
    com = communes()
    feux = incendies(com)
    cas = casernes()
    bud = budget_sdis()
    terr = indicateurs_territoire(com, cas)
    nature_feux(feux)
    prevention(com, feux)
    pompiers(com)
    print(terr.round(1).to_string())
    print("OK ->", OUT)
