"""Où ajouter des secours dans la forêt des Landes de Gascogne ?

Entrées : data/processed/feux.csv, data/raw/secours/ (voir telecharger_secours.py)
Sorties : data/processed/
  - feux_geo.csv          feux ≥ 1 ha de Gironde et des Landes, placés au centre de leur commune
  - grille_secours.csv    le massif découpé en carrés de 2 km : distance à la caserne la plus
                          proche avant / après les ajouts, et à la base aérienne la plus proche
  - casernes.csv          casernes existantes (OSM) + casernes et postes de gardes forestiers proposés
  - bases_aeriennes.csv   base Canadair actuelle (Nîmes), pélicandrome (Mérignac), aire proposée

Méthode
-------
Le massif est le « triangle landais » (Soulac, Hossegor, Nérac), limité à la Gironde et aux
Landes, quadrillé tous les 2 km. Les ajouts visent les zones sans pompiers, pas les feux passés :
  1. casernes : on en ajoute une par une là où elles couvrent (rayon 10 km) le plus de zone
     aujourd'hui à plus de 10 km d'une caserne. Trois casernes sont ensuite déplacées dans des
     zones choisies par le groupe (POSTES_IMPOSES) : à l'endroit de la zone le plus éloigné
     de toute caserne ;
  2. gardes forestiers : même chose avec un rayon de 5 km, pour les zones à plus de 5 km ;
  3. aire Canadair : en plus de Mérignac, le point de la forêt qui réduit le plus la distance
     moyenne entre chaque carré du massif et la base aérienne la plus proche.

Distances à vol d'oiseau : le temps réel par la route est plus long.

Usage : python pipeline/indicateurs_secours.py
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "secours"
OUT_DIR = ROOT / "data" / "processed"

DEPARTEMENTS = ["33", "40"]
SURFACE_MIN_HA = 1
PAS_KM = 2
TRIANGLE_LANDAIS = [(-1.12, 45.52), (-1.44, 43.66), (0.34, 44.14), (-1.12, 45.52)]  # lon, lat
DOUBLON_KM = 0.3
N_CASERNES, RAYON_CASERNE_KM = 8, 10
N_GARDES, RAYON_GARDE_KM = 8, 5
VITESSE_CANADAIR_KMH = 300

# Casernes déplacées à la main : rang → (zone (lat min, lat max, lon min, lon max), raison).
POSTES_IMPOSES = {
    3: ((44.75, 45.15, -0.45, 0.20), "à l'est de Bordeaux"),
    6: ((44.68, 44.82, -0.45, -0.15), "en face de Bordeaux, à l'est, un peu plus au sud"),
    7: ((44.50, 44.75, -1.10, -0.75), "au sud du bassin d'Arcachon"),
}

BASES_AERIENNES = [
    ("Nîmes-Garons", 43.7576, 4.4163, "existante",
     "Base permanente des Canadair de la Sécurité civile"),
    ("Bordeaux-Mérignac", 44.8283, -0.7156, "existante",
     "Pélicandrome depuis 2023, avions prépositionnés l'été"),
]


def distance_km(lat1, lon1, lat2, lon2):
    """Distance à vol d'oiseau (haversine), vectorisée."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def _dans(lon: np.ndarray, lat: np.ndarray, anneau) -> np.ndarray:
    """Points dans un polygone (lancer de rayon)."""
    a = np.asarray(anneau)
    x1, y1, x2, y2 = a[:-1, 0], a[:-1, 1], a[1:, 0], a[1:, 1]
    coupe = ((y1 > lat[:, None]) != (y2 > lat[:, None])) & (
        lon[:, None] < (x2 - x1) * (lat[:, None] - y1) / (y2 - y1 + 1e-12) + x1)
    return coupe.sum(axis=1) % 2 == 1


def lire_communes() -> pd.DataFrame:
    lignes = []
    for dep in DEPARTEMENTS:
        for c in json.loads((RAW_DIR / f"communes_{dep}.json").read_text(encoding="utf-8")):
            lon, lat = c["centre"]["coordinates"]
            lignes.append({"code_insee": c["code"], "commune": c["nom"], "lat": lat, "lon": lon})
    return pd.DataFrame(lignes)


def lire_casernes() -> pd.DataFrame:
    elements = json.loads((RAW_DIR / "casernes_osm.json").read_text(encoding="utf-8"))["elements"]
    lignes = []
    for e in elements:
        centre = e.get("center", e)
        tags = e.get("tags", {})
        lignes.append({"nom": tags.get("name", "Caserne de pompiers"),
                       "lat": centre["lat"], "lon": centre["lon"]})
    c = pd.DataFrame(lignes)
    # Une même caserne est parfois dessinée deux fois (point + bâtiment) : on dédoublonne.
    garder = []
    for i, ligne in c.iterrows():
        if all(distance_km(ligne.lat, ligne.lon, c.lat[j], c.lon[j]) > DOUBLON_KM for j in garder):
            garder.append(i)
    return c.loc[garder].reset_index(drop=True)


def grille_massif(zone=(43.45, 45.6, -1.35, 0.35), pas_km: float = PAS_KM,
                  triangle: bool = True) -> pd.DataFrame:
    """Carrés de `pas_km` d'une zone (par défaut le triangle landais), avec leur commune."""
    lat_min, lat_max, lon_min, lon_max = zone
    lats = np.arange(lat_min, lat_max, pas_km / 111.2)
    lons = np.arange(lon_min, lon_max, pas_km / (111.2 * np.cos(np.radians(44.5))))
    lon, lat = (m.ravel() for m in np.meshgrid(lons, lats))
    commune = np.full(len(lon), None, dtype=object)
    for dep in DEPARTEMENTS:
        geo = json.loads((RAW_DIR / f"contours_{dep}.geojson").read_text(encoding="utf-8"))
        for f in geo["features"]:
            g = f["geometry"]
            for polygone in g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]:
                a = np.asarray(polygone[0])
                idx = np.where((lon >= a[:, 0].min()) & (lon <= a[:, 0].max()) & (lat >= a[:, 1].min())
                               & (lat <= a[:, 1].max()) & (commune == None))[0]  # noqa: E711
                if len(idx):
                    commune[idx[_dans(lon[idx], lat[idx], a)]] = f["properties"]["nom"]
    g = pd.DataFrame({"lat": lat, "lon": lon, "commune": commune}).dropna()
    if triangle:
        g = g[_dans(g.lon.to_numpy(), g.lat.to_numpy(), TRIANGLE_LANDAIS)]
    return g.reset_index(drop=True)


def feux_geolocalises(communes: pd.DataFrame) -> pd.DataFrame:
    f = pd.read_csv(OUT_DIR / "feux.csv", dtype={"departement": str, "code_insee": str})
    f = f[f.departement.isin(DEPARTEMENTS) & (f.surface_ha >= SURFACE_MIN_HA)]
    geo = f.merge(communes[["code_insee", "lat", "lon"]], on="code_insee", how="left")
    perdus = geo.lat.isna()
    if perdus.any():
        print(f"{perdus.sum()} feux sans commune actuelle (fusions) ignorés.")
    return geo[~perdus][["annee", "departement", "code_insee", "commune", "date_alerte",
                         "surface_ha", "lat", "lon"]].reset_index(drop=True)


def ajouter_postes(grille: pd.DataFrame, d_min: np.ndarray, d_grille: np.ndarray,
                   n: int, rayon: float, type_poste: str, libelle: str, rang0: int) -> tuple[list, np.ndarray]:
    """Couverture maximale gloutonne : chaque poste couvre le plus de carrés encore à plus de `rayon`."""
    postes = []
    for i in range(n):
        gain = ((d_min[:, None] > rayon) & (d_grille <= rayon)).sum(axis=0)
        j = int(gain.argmax())
        d_min = np.minimum(d_min, d_grille[:, j])
        c = grille.iloc[j]
        postes.append({"nom": f"{libelle} n° {rang0 + i} — {c.commune}",
                       "lat": c.lat, "lon": c.lon, "statut": "proposee", "type": type_poste,
                       "rang": rang0 + i, "rayon_km": rayon, "gain_km2": int(gain[j]) * PAS_KM ** 2})
    return postes, d_min


def deplacer_postes(postes: list, existantes: pd.DataFrame) -> list:
    """Place chaque caserne imposée au point de sa zone le plus loin de toute caserne."""
    for rang, (zone, raison) in POSTES_IMPOSES.items():
        autres = pd.concat([existantes, pd.DataFrame([q for q in postes if q["rang"] != rang])])
        z = grille_massif(zone, pas_km=1, triangle=False)
        dist = distance_km(z.lat.to_numpy()[:, None], z.lon.to_numpy()[:, None],
                           autres.lat.to_numpy()[None, :], autres.lon.to_numpy()[None, :]).min(axis=1)
        c = z.iloc[int(dist.argmax())]
        poste = next(q for q in postes if q["rang"] == rang)
        poste.update(nom=f"Caserne proposée n° {rang} — {c.commune}", lat=c.lat, lon=c.lon,
                     gain_km2=np.nan, choix=f"Placée {raison} ({dist.max():.0f} km de toute caserne)")
    return postes


def aire_canadair(grille: pd.DataFrame, d_grille: np.ndarray) -> dict:
    """Aire qui, avec Mérignac, rapproche le plus chaque carré du massif d'une base aérienne."""
    merignac = BASES_AERIENNES[1]
    d_merignac = distance_km(grille.lat.to_numpy(), grille.lon.to_numpy(), merignac[1], merignac[2])
    j = int(np.minimum(d_merignac[:, None], d_grille).mean(axis=0).argmin())
    c = grille.iloc[j]
    return {"nom": f"Aire Canadair proposée — {c.commune}", "lat": c.lat, "lon": c.lon,
            "statut": "proposee", "description": "Au centre de la forêt, en complément de Mérignac"}


def main() -> None:
    communes = lire_communes()
    feux = feux_geolocalises(communes)
    grille = grille_massif()
    la, lo = grille.lat.to_numpy(), grille.lon.to_numpy()
    d_grille = distance_km(la[:, None], lo[:, None], la[None, :], lo[None, :])

    existantes = lire_casernes().assign(statut="existante", type="caserne")
    d_avant = distance_km(la[:, None], lo[:, None], existantes.lat.to_numpy()[None, :],
                          existantes.lon.to_numpy()[None, :]).min(axis=1)
    casernes, _ = ajouter_postes(grille, d_avant, d_grille, N_CASERNES, RAYON_CASERNE_KM,
                                 "caserne", "Caserne proposée", 1)
    casernes = deplacer_postes(casernes, existantes)
    c = pd.DataFrame(casernes)
    d_min = np.minimum(d_avant, distance_km(la[:, None], lo[:, None], c.lat.to_numpy()[None, :],
                                            c.lon.to_numpy()[None, :]).min(axis=1))
    gardes, d_apres = ajouter_postes(grille, d_min, d_grille, N_GARDES, RAYON_GARDE_KM,
                                     "garde", "Poste de gardes forestiers", N_CASERNES + 1)
    tous = pd.concat([existantes, pd.DataFrame(casernes + gardes)], ignore_index=True)

    bases = pd.DataFrame([dict(zip(["nom", "lat", "lon", "statut", "description"], b))
                          for b in BASES_AERIENNES] + [aire_canadair(grille, d_grille)])
    d_bases = distance_km(la[:, None], lo[:, None], bases.lat.to_numpy()[None, :],
                          bases.lon.to_numpy()[None, :])
    bases["distance_moy_km"] = d_bases.mean(axis=0)
    bases["temps_vol_min"] = bases.distance_moy_km / VITESSE_CANADAIR_KMH * 60

    grille["dist_caserne_avant_km"] = d_avant
    grille["dist_caserne_apres_km"] = d_apres
    grille["dist_air_avant_km"] = d_bases[:, 1]               # Mérignac seul
    grille["dist_air_apres_km"] = d_bases[:, 1:].min(axis=1)  # Mérignac + aire proposée

    feux.to_csv(OUT_DIR / "feux_geo.csv", index=False)
    grille.round(4).to_csv(OUT_DIR / "grille_secours.csv", index=False)
    tous.to_csv(OUT_DIR / "casernes.csv", index=False)
    bases.round({"distance_moy_km": 1, "temps_vol_min": 1}).to_csv(OUT_DIR / "bases_aeriennes.csv", index=False)

    print(f"Massif : {len(grille) * PAS_KM ** 2} km², {len(existantes)} casernes existantes.")
    for seuil in (RAYON_GARDE_KM, RAYON_CASERNE_KM):
        print(f"À plus de {seuil} km d'une caserne : {(d_avant > seuil).mean():.1%} → {(d_apres > seuil).mean():.1%}")
    print(pd.DataFrame(casernes + gardes)[["nom", "gain_km2"]].to_string(index=False))
    print(bases[["nom", "distance_moy_km", "temps_vol_min"]].to_string(index=False))


if __name__ == "__main__":
    main()
