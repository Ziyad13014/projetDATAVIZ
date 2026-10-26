"""Télécharge les données de secours du massif landais (Gironde, Landes).

- Casernes de pompiers : OpenStreetMap (amenity=fire_station) via l'API Overpass,
  licence ODbL. https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dfire_station
- Centres des communes : API Découpage administratif (geo.api.gouv.fr), Licence Ouverte,
  pour placer chaque feu de la BDIFF (localisé à la commune) sur la carte.

Usage : python pipeline/telecharger_secours.py
"""
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

DEPARTEMENTS = ["33", "40"]
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
GEO_API_URL = "https://geo.api.gouv.fr/communes"
ENTETES = {"User-Agent": "projet-dataviz-ynov/1.0"}

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "secours"


def _get_json(url: str, data: bytes | None = None) -> dict | list:
    with urlopen(Request(url, data=data, headers=ENTETES), timeout=180) as reponse:
        return json.load(reponse)


def casernes() -> dict:
    zones = "".join(f'area["ref:INSEE"="{dep}"]["admin_level"="6"];' for dep in DEPARTEMENTS)
    requete = f'[out:json][timeout:120];({zones})->.a;nwr["amenity"="fire_station"](area.a);out center tags;'
    return _get_json(OVERPASS_URL, urlencode({"data": requete}).encode())


def communes(departement: str) -> list:
    criteres = {"codeDepartement": departement, "fields": "code,nom,centre", "format": "json"}
    return _get_json(f"{GEO_API_URL}?{urlencode(criteres)}")


def contours(departement: str) -> dict:
    """Contours des communes (GeoJSON), pour quadriller le territoire."""
    criteres = {"codeDepartement": departement, "fields": "code,nom",
                "format": "geojson", "geometry": "contour"}
    return _get_json(f"{GEO_API_URL}?{urlencode(criteres)}")


def telecharger(force: bool = False) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cibles = {"casernes_osm.json": casernes,
              **{f"communes_{dep}.json": (lambda dep=dep: communes(dep)) for dep in DEPARTEMENTS},
              **{f"contours_{dep}.geojson": (lambda dep=dep: contours(dep)) for dep in DEPARTEMENTS}}
    for nom, charger in cibles.items():
        cible = RAW_DIR / nom
        if force or not cible.exists():
            print(f"Téléchargement {nom}...")
            cible.write_text(json.dumps(charger(), ensure_ascii=False), encoding="utf-8")
        else:
            print(f"{nom} déjà présent, ignoré.")


if __name__ == "__main__":
    telecharger()
