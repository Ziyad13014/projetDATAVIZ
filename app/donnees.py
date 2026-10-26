"""Chargement des données préparées par le pipeline (data/processed/)."""
from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"

# Normale récente utilisée partout dans le dashboard.
NORMALE_RECENTE = (1996, 2025)
NORMALE_ANCIENNE = (1950, 1979)
SEUIL_KOPPEN_MM = 40

NOMS_STATIONS = {
    "40192001": "Mont-de-Marsan",
    "33529001": "Cazaux",
    "33504001": "Sauternes",
    "33281001": "Bordeaux-Mérignac",
    "66136001": "Perpignan",
    "34154001": "Montpellier",
    "13054001": "Marignane",
}
NOMS_DEPARTEMENTS = {
    "40": "Landes",
    "33": "Gironde",
    "66": "Pyrénées-Orientales",
    "34": "Hérault",
    "13": "Bouches-du-Rhône",
}
# Complément de lieu, pour écrire « en Gironde », « dans les Landes »…
DANS_DEPARTEMENT = {
    "40": "dans les Landes",
    "33": "en Gironde",
    "66": "dans les Pyrénées-Orientales",
    "34": "dans l'Hérault",
    "13": "dans les Bouches-du-Rhône",
}
KOPPEN_LIBELLES = {
    "Cfb": "océanique",
    "Cfa": "subtropical humide",
    "Csa": "méditerranéen",
    "Csb": "méditerranéen à été tempéré",
}


def _lire(nom: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED / nom, dtype={"NUM_POSTE": str, "departement": str})


stations = _lire("stations.csv")
stations["nom_affiche"] = stations.NUM_POSTE.map(NOMS_STATIONS)
stations["departement"] = stations.NUM_POSTE.str[:2]

annuel = _lire("annuel.csv").dropna(subset=["n_mois_secs"])
normales = _lire("normales_30.csv")
mensuel = _lire("mensuel.csv")
feux_annuel = _lire("feux_annuel.csv")

# Page « Solutions » (pipeline/indicateurs_secours.py)
PAS_GRILLE_KM = 2
feux_geo = _lire("feux_geo.csv")
grille_secours = _lire("grille_secours.csv")
casernes = _lire("casernes.csv")
bases_aeriennes = _lire("bases_aeriennes.csv")

STATIONS_LANDES = stations[stations.groupe == "Landes"].NUM_POSTE.tolist()
STATIONS_MED = stations[stations.groupe == "Méditerranée"].NUM_POSTE.tolist()


def nom(poste: str) -> str:
    return NOMS_STATIONS[poste]


def departement(poste: str) -> str:
    return poste[:2]


def climatologie(poste: str, periode: tuple[int, int]) -> pd.DataFrame:
    """Moyennes mensuelles (P, T) d'une station sur une période."""
    m = mensuel[(mensuel.NUM_POSTE == poste) & mensuel.annee.between(*periode)]
    return m.groupby("mois")[["RR", "TM"]].mean().reset_index()


def normale(poste: str, fin: int = NORMALE_RECENTE[1]) -> pd.Series:
    n = normales[(normales.NUM_POSTE == poste) & (normales.fin == fin)]
    return n.iloc[0]


def mois_secs_moyens(poste: str, periode: tuple[int, int]) -> float:
    a = annuel[(annuel.NUM_POSTE == poste) & annuel.annee.between(*periode)]
    return a.n_mois_secs.mean()
