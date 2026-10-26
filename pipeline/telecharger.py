"""Télécharge les données climatologiques mensuelles Météo-France (data.gouv.fr).

Source : https://www.data.gouv.fr/datasets/donnees-climatologiques-de-base-mensuelles
Un fichier par département et par période ; on prend 1950-2024 et 2025-2026.

Usage : python pipeline/telecharger.py
"""
from pathlib import Path
import urllib.request

BASE_URL = "https://meteofrance.s3.sbg.io.cloud.ovh.net/data/synchro_ftp/BASE/MENS"

# Landes (40) et Gironde (33) pour le massif landais ;
# Pyrénées-Orientales (66), Hérault (34), Bouches-du-Rhône (13) comme témoins méditerranéens.
DEPARTEMENTS = ["40", "33", "66", "34", "13"]
PERIODES = ["previous-1950-2024", "latest-2025-2026"]

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def telecharger(force: bool = False) -> list[Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fichiers = []
    for dep in DEPARTEMENTS:
        for periode in PERIODES:
            nom = f"MENSQ_{dep}_{periode}.csv.gz"
            cible = RAW_DIR / nom
            if force or not cible.exists():
                print(f"Téléchargement de {nom}...")
                urllib.request.urlretrieve(f"{BASE_URL}/{nom}", cible)
            else:
                print(f"{nom} déjà présent, ignoré.")
            fichiers.append(cible)
    return fichiers


if __name__ == "__main__":
    telecharger()
