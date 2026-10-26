"""Calcule les indicateurs de « méditerranéité » climatique par station.

Entrée  : data/raw/MENSQ_*.csv.gz (voir telecharger.py)
Sorties : data/processed/
  - stations.csv      métadonnées des stations retenues
  - mensuel.csv       une ligne par station × mois (RR, TM, mois sec Gaussen)
  - annuel.csv        une ligne par station × année (Gaussen + Köppen sur l'année)
  - normales_30.csv   une ligne par station × fenêtre glissante de 30 ans
                      (Köppen calculé sur la climatologie moyenne, méthode standard)

Définitions
-----------
Gaussen   : un mois est sec si P ≤ 2T (P en mm, T en °C).
Köppen    : classification de Peel et al. (2007), seuil C/D à 0 °C,
            été = avril-septembre (hémisphère nord).
            Le « s » méditerranéen (Cs) exige : mois d'été le plus sec < 40 mm
            ET < 1/3 du mois d'hiver le plus humide.
            Köppen est normalement défini sur une normale de 30 ans ;
            la version annuelle n'est qu'un indicateur de tendance.

Usage : python pipeline/indicateurs.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"

# Stations à séries complètes 1950-2026 (922 mois avec RR et TM).
STATIONS = {
    # Massif landais
    "40192001": "Landes",       # Mont-de-Marsan
    "33529001": "Landes",       # Cazaux (cœur du massif, près de Biscarrosse)
    "33504001": "Landes",       # Sauternes (lisière est du massif)
    "33281001": "Landes",       # Bordeaux-Mérignac
    # Témoins méditerranéens
    "66136001": "Méditerranée",  # Perpignan
    "34154001": "Méditerranée",  # Montpellier-Aéroport
    "13054001": "Méditerranée",  # Marignane
}

MOIS_ETE = [4, 5, 6, 7, 8, 9]
MOIS_HIVER = [10, 11, 12, 1, 2, 3]
FENETRE_NORMALE = 30


def charger_mensuel() -> pd.DataFrame:
    colonnes = ["NUM_POSTE", "NOM_USUEL", "LAT", "LON", "ALTI", "AAAAMM", "RR", "TM"]
    fichiers = sorted(RAW_DIR.glob("MENSQ_*.csv.gz"))
    if not fichiers:
        raise FileNotFoundError(f"Aucun fichier dans {RAW_DIR} : lancer telecharger.py")
    df = pd.concat(
        pd.read_csv(f, sep=";", usecols=colonnes, dtype={"NUM_POSTE": str})
        for f in fichiers
    )
    df = df[df.NUM_POSTE.isin(STATIONS)].drop_duplicates(["NUM_POSTE", "AAAAMM"])
    df["groupe"] = df.NUM_POSTE.map(STATIONS)
    df["annee"] = df.AAAAMM // 100
    df["mois"] = df.AAAAMM % 100
    df["mois_sec"] = (df.RR <= 2 * df.TM).astype("boolean")
    df.loc[df.RR.isna() | df.TM.isna(), "mois_sec"] = pd.NA
    return df.sort_values(["NUM_POSTE", "AAAAMM"]).reset_index(drop=True)


def koppen(t: pd.Series, p: pd.Series) -> dict:
    """Classe de Köppen à partir de 12 valeurs mensuelles (index = mois 1..12)."""
    t_moy, p_tot = t.mean(), p.sum()
    p_ete, p_hiver = p[MOIS_ETE], p[MOIS_HIVER]

    part_ete = p_ete.sum() / p_tot if p_tot > 0 else 0.5
    if part_ete >= 0.7:
        seuil_aride = 2 * t_moy + 28
    elif part_ete <= 0.3:
        seuil_aride = 2 * t_moy
    else:
        seuil_aride = 2 * t_moy + 14

    p_ete_min, p_hiver_max = p_ete.min(), p_hiver.max()
    s_40mm = p_ete_min < 40
    s_tiers = p_ete_min < p_hiver_max / 3

    if t.max() < 10:
        classe = "ET" if t.max() > 0 else "EF"
    elif p_tot < 10 * seuil_aride:
        classe = ("BW" if p_tot < 5 * seuil_aride else "BS") + ("h" if t_moy >= 18 else "k")
    elif t.min() >= 18:
        classe = "A"  # non pertinent ici, pas de sous-type
    else:
        principal = "C" if t.min() > 0 else "D"
        if s_40mm and s_tiers:
            regime = "s"
        elif p_hiver.min() < p_ete.max() / 10:
            regime = "w"
        else:
            regime = "f"
        if t.max() >= 22:
            ete = "a"
        elif (t >= 10).sum() >= 4:
            ete = "b"
        else:
            ete = "c"
        classe = principal + regime + ete

    return {
        "koppen": classe,
        "mediterraneen": classe.startswith("Cs"),
        "p_ete_min": round(p_ete_min, 1),
        "p_hiver_max": round(p_hiver_max, 1),
        "ratio_ete_hiver": round(p_ete_min / p_hiver_max, 3) if p_hiver_max > 0 else np.nan,
        "critere_40mm": s_40mm,
        "critere_tiers": s_tiers,
    }


def gaussen(t: pd.Series, p: pd.Series) -> dict:
    secs = p <= 2 * t
    return {
        "n_mois_secs": int(secs.sum()),
        "mois_secs": ",".join(str(m) for m in secs[secs].index),
        # Déficit cumulé (mm) : surface entre 2T et P sur les mois secs
        "deficit_gaussen": round(float((2 * t - p)[secs].sum()), 1),
    }


def indicateurs_annuels(mensuel: pd.DataFrame) -> pd.DataFrame:
    lignes = []
    for (poste, annee), g in mensuel.groupby(["NUM_POSTE", "annee"]):
        g = g.dropna(subset=["RR", "TM"]).set_index("mois")
        ligne = {"NUM_POSTE": poste, "annee": annee, "n_mois_valides": len(g)}
        if len(g) == 12:
            ligne |= {"p_annuelle": round(g.RR.sum(), 1), "t_moyenne": round(g.TM.mean(), 2)}
            ligne |= gaussen(g.TM, g.RR) | koppen(g.TM, g.RR)
        lignes.append(ligne)
    return pd.DataFrame(lignes)


def normales_glissantes(mensuel: pd.DataFrame) -> pd.DataFrame:
    lignes = []
    for poste, g in mensuel.groupby("NUM_POSTE"):
        annees_completes = g.dropna(subset=["RR", "TM"]).groupby("annee").size()
        annees_completes = annees_completes[annees_completes == 12].index
        g = g[g.annee.isin(annees_completes)]
        for fin in range(g.annee.min() + FENETRE_NORMALE - 1, g.annee.max() + 1):
            fen = g[g.annee.between(fin - FENETRE_NORMALE + 1, fin)]
            n_annees = fen.annee.nunique()
            if n_annees < 0.8 * FENETRE_NORMALE:
                continue
            clim = fen.groupby("mois")[["TM", "RR"]].mean()
            lignes.append(
                {"NUM_POSTE": poste, "debut": fin - FENETRE_NORMALE + 1, "fin": fin,
                 "n_annees": n_annees,
                 "p_annuelle": round(clim.RR.sum(), 1), "t_moyenne": round(clim.TM.mean(), 2)}
                | gaussen(clim.TM, clim.RR)
                | koppen(clim.TM, clim.RR)
            )
    return pd.DataFrame(lignes)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mensuel = charger_mensuel()

    stations = (
        mensuel.groupby("NUM_POSTE")
        .agg(nom=("NOM_USUEL", "first"), groupe=("groupe", "first"),
             lat=("LAT", "first"), lon=("LON", "first"), altitude=("ALTI", "first"))
        .reset_index()
    )
    # Sur une seule année, presque tout été a un mois < 40 mm : la classe Köppen
    # annuelle surestime fortement le « Cs ». On la renomme pour éviter la confusion
    # avec la classe calculée sur les normales (la seule valable).
    annuel = indicateurs_annuels(mensuel).rename(
        columns={"koppen": "koppen_annuel", "mediterraneen": "cs_annuel"})
    normales = normales_glissantes(mensuel)

    meta = stations[["NUM_POSTE", "nom", "groupe"]]
    stations.to_csv(OUT_DIR / "stations.csv", index=False)
    mensuel[["NUM_POSTE", "annee", "mois", "RR", "TM", "mois_sec"]].merge(meta).to_csv(
        OUT_DIR / "mensuel.csv", index=False)
    annuel.merge(meta).to_csv(OUT_DIR / "annuel.csv", index=False)
    normales.merge(meta).to_csv(OUT_DIR / "normales_30.csv", index=False)

    print(f"{len(stations)} stations, {len(mensuel)} mois, "
          f"{annuel.koppen_annuel.notna().sum()} années complètes, {len(normales)} normales glissantes")
    print(f"Fichiers écrits dans {OUT_DIR}")


if __name__ == "__main__":
    main()
