"""Télécharge les feux de forêt de la BDIFF (open data, Licence Ouverte v2).

Source : https://www.data.gouv.fr/datasets/base-de-donnees-sur-les-incendies-de-forets-en-france-bdiff
Portail : https://bdiff.agriculture.gouv.fr/incendies

Le portail n'a pas d'API : on reproduit la recherche du formulaire puis on appelle
le bouton « CSV » (/incendies/zip), qui exporte la dernière recherche de la session.
Un export est limité à 30 000 lignes, d'où le découpage par zone et par période.

Usage : python pipeline/telecharger_feux.py
"""
from http.cookiejar import CookieJar
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, build_opener
import zipfile

BASE_URL = "https://bdiff.agriculture.gouv.fr"

# Codes de zone du formulaire BDIFF.
ZONES = {"1": "mediterranee", "20": "aquitaine"}
PERIODES = [(2006, 2015), (2016, 2025)]

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "bdiff"


def exporter(zone: str, debut: int, fin: int) -> bytes:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    criteres = {
        "if[zone]": zone,
        "if[periodeAnnees][anneeDeb]": debut,
        "if[periodeAnnees][anneeFin]": fin,
    }
    opener.open(f"{BASE_URL}/incendies?{urlencode(criteres)}").read()
    reponse = opener.open(f"{BASE_URL}/incendies/zip")
    if "zip" not in reponse.headers.get("Content-Type", ""):
        raise RuntimeError(f"Export refusé (zone {zone}, {debut}-{fin}) : plus de 30 000 lignes ?")
    with zipfile.ZipFile(BytesIO(reponse.read())) as z:
        return z.read("Incendies.csv")


def telecharger(force: bool = False) -> list[Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fichiers = []
    for zone, nom_zone in ZONES.items():
        for debut, fin in PERIODES:
            cible = RAW_DIR / f"bdiff_{nom_zone}_{debut}-{fin}.csv"
            if force or not cible.exists():
                print(f"Export BDIFF {nom_zone} {debut}-{fin}...")
                cible.write_bytes(exporter(zone, debut, fin))
            else:
                print(f"{cible.name} déjà présent, ignoré.")
            fichiers.append(cible)
    return fichiers


if __name__ == "__main__":
    telecharger()
