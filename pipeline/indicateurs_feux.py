"""Calcule les indicateurs feux de forêt à partir des exports BDIFF.

Entrée  : data/raw/bdiff/bdiff_*.csv (voir telecharger_feux.py)
Sorties : data/processed/
  - feux.csv            un feu par ligne (nettoyé, surfaces en ha)
  - feux_annuel.csv     une ligne par département × année
  - feux_mensuel.csv    une ligne par département × année × mois
  - feux_lacunes.csv    trous signalés par la BDIFF (département × année)

Groupes
-------
Massif landais : Gironde (33), Landes (40), Lot-et-Garonne (47).
Témoins méditerranéens : les mêmes départements que pour le climat (66, 34, 13).
Les autres départements des deux zones sont gardés avec groupe = « Autre ».

Usage : python pipeline/indicateurs_feux.py
"""
from pathlib import Path
import csv

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "bdiff"
OUT_DIR = ROOT / "data" / "processed"

GROUPES = {
    "33": "Landes", "40": "Landes", "47": "Landes",
    "66": "Méditerranée", "34": "Méditerranée", "13": "Méditerranée",
}
COLONNES = {
    "Année": "annee",
    "Numéro": "numero",
    "Département": "departement",
    "Code INSEE": "code_insee",
    "Nom de la commune": "commune",
    "Date de première alerte": "date_alerte",
    "Surface parcourue (m2)": "surface_m2",
    "Surface forêt (m2)": "surface_foret_m2",
    "Nature": "cause",
}
SEUIL_GRAND_FEU_HA = 100
MOIS_ETE = [6, 7, 8, 9]


def lire_export(fichier: Path) -> tuple[pd.DataFrame, list[dict]]:
    """Un export BDIFF = quelques lignes de notes, puis le CSV proprement dit."""
    lignes = fichier.read_text(encoding="utf-8").splitlines()
    debut = next(i for i, l in enumerate(lignes) if l.startswith("Année;"))

    zone = next((c.split(":", 1)[1].strip() for l in lignes[:debut]
                 for c in next(csv.reader([l], delimiter=";")) if c.startswith("Zone :")), None)
    lacunes = []
    for ligne in lignes[:debut]:
        cellules = next(csv.reader([ligne], delimiter=";"))
        # ex. « 2010 - 64 : » ; « Données perdues suite à un incident technique. »
        if len(cellules) == 2 and " - " in cellules[0]:
            annee, dep = cellules[0].rstrip(": ").split(" - ")
            lacunes.append({"annee": int(annee), "departement": dep.strip(), "note": cellules[1]})

    df = pd.read_csv(fichier, sep=";", skiprows=debut, usecols=list(COLONNES),
                     dtype={"Département": str, "Code INSEE": str})
    df = df.rename(columns=COLONNES)
    df["zone"] = zone
    return df, lacunes


def charger() -> tuple[pd.DataFrame, pd.DataFrame]:
    fichiers = sorted(RAW_DIR.glob("bdiff_*.csv"))
    if not fichiers:
        raise FileNotFoundError(f"Aucun fichier dans {RAW_DIR} : lancer telecharger_feux.py")
    exports = [lire_export(f) for f in fichiers]
    feux = pd.concat(df for df, _ in exports).drop_duplicates(["annee", "numero", "departement"])
    lacunes = pd.DataFrame([l for _, ls in exports for l in ls]).drop_duplicates()

    feux["date_alerte"] = pd.to_datetime(feux.date_alerte)
    feux["mois"] = feux.date_alerte.dt.month
    feux["jour_annee"] = feux.date_alerte.dt.dayofyear
    feux["surface_ha"] = feux.surface_m2.fillna(0) / 10_000
    feux["surface_foret_ha"] = feux.surface_foret_m2.fillna(0) / 10_000
    feux["groupe"] = feux.departement.map(GROUPES).fillna("Autre")
    feux = feux.drop(columns=["surface_m2", "surface_foret_m2"])
    return feux.sort_values("date_alerte").reset_index(drop=True), lacunes


def indicateurs_annuels(feux: pd.DataFrame) -> pd.DataFrame:
    def stats(g: pd.DataFrame) -> pd.Series:
        # Saison des feux : fenêtre qui contient 80 % des départs (10e → 90e centile).
        p10, p90 = np.percentile(g.jour_annee, [10, 90])
        return pd.Series({
            "n_feux": len(g),
            "surface_ha": round(g.surface_ha.sum(), 1),
            "surface_foret_ha": round(g.surface_foret_ha.sum(), 1),
            "n_feux_1ha": int((g.surface_ha >= 1).sum()),
            "n_grands_feux": int((g.surface_ha >= SEUIL_GRAND_FEU_HA).sum()),
            "plus_grand_feu_ha": round(g.surface_ha.max(), 1),
            "part_feux_ete": round(g.mois.isin(MOIS_ETE).mean(), 3),
            "part_surface_ete": round(g.loc[g.mois.isin(MOIS_ETE), "surface_ha"].sum()
                                      / g.surface_ha.sum(), 3) if g.surface_ha.sum() > 0 else np.nan,
            "saison_debut_jour": int(p10),
            "saison_fin_jour": int(p90),
            "saison_longueur_jours": int(p90 - p10),
        })

    return (feux.groupby(["departement", "groupe", "zone", "annee"])
            .apply(stats, include_groups=False).reset_index())


def indicateurs_mensuels(feux: pd.DataFrame) -> pd.DataFrame:
    return (feux.groupby(["departement", "groupe", "zone", "annee", "mois"])
            .agg(n_feux=("numero", "size"), surface_ha=("surface_ha", "sum"))
            .round({"surface_ha": 1}).reset_index())


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    feux, lacunes = charger()
    annuel = indicateurs_annuels(feux)
    mensuel = indicateurs_mensuels(feux)

    feux.to_csv(OUT_DIR / "feux.csv", index=False)
    annuel.to_csv(OUT_DIR / "feux_annuel.csv", index=False)
    mensuel.to_csv(OUT_DIR / "feux_mensuel.csv", index=False)
    lacunes.to_csv(OUT_DIR / "feux_lacunes.csv", index=False)

    print(f"{len(feux)} feux, {feux.departement.nunique()} départements, "
          f"{feux.annee.min()}-{feux.annee.max()}, {len(lacunes)} lacunes signalées")
    print(f"Fichiers écrits dans {OUT_DIR}")


if __name__ == "__main__":
    main()
