"""Éléments partagés par les deux dashboards : chargement des données, couleurs, KPI et textes."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
MANUAL = ROOT / "data" / "manual"

TITRE = "Le massif landais devient-il méditerranéen ?"
PROBLEMATIQUE = ("Le réchauffement fait-il basculer le massif des Landes de Gascogne vers un risque "
                 "d'incendie de type méditerranéen, et ses moyens de prévention et de lutte sont-ils à la hauteur ?")
PUBLIC = "Préfectures, SDIS et élus de Gironde, des Landes et des Alpes-Maritimes"

ANNEE_MIN, ANNEE_MAX = 2006, 2025
TERRITOIRES = ["Landes de Gascogne", "Alpes-Maritimes"]

# Palette catégorielle validée (skill dataviz, slots 1-3) : la couleur suit l'entité, partout.
COULEUR_TERRITOIRE = {"Landes de Gascogne": "#2a78d6", "Alpes-Maritimes": "#eb6834"}
COULEUR_STATION = {"Bordeaux-Mérignac": "#2a78d6", "Mont-de-Marsan": "#1baf7a", "Nice": "#eb6834"}
COULEUR_DEP = {"Gironde": "#2a78d6", "Landes": "#1baf7a", "Alpes-Maritimes": "#eb6834"}
# Statut de prévention : palette de statut (toujours accompagnée d'un libellé)
COULEUR_STATUT = {"Plan approuvé": "#0ca30c", "Plan prescrit, non approuvé": "#fab219",
                  "À risque, sans plan": "#d03b3b", "Non classée à risque": "#c3c2b7"}
# Divergente bleu <-> rouge, milieu gris neutre (bandes de réchauffement)
DIVERGENTE = ["#184f95", "#3987e5", "#9ec5f4", "#f0efec", "#f2b0af", "#e34948", "#a32a29"]
INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"


def fmt(x, dec=0):
    """Nombre au format français : espace fine pour les milliers, virgule décimale."""
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def pct(x):
    return f"{x * 100:.0f} %"


def load():
    """Toutes les tables, prêtes à l'emploi."""
    def rd(nom, **k):
        return pd.read_csv(PROCESSED / nom, **k)
    d = {
        "climat": rd("climat_stations.csv", dtype={"dep": str}),
        "feux": rd("incendies.csv", dtype={"dep": str, "insee": str}, parse_dates=["date"]),
        "feux_an": rd("incendies_annuel_territoire.csv"),
        "nature": rd("nature_feux.csv"),
        "budget": rd("budget_sdis.csv", dtype={"dep": str}),
        "casernes": rd("casernes.csv", dtype={"dep": str}),
        "territoires": rd("territoires.csv"),
        "prevention": rd("prevention_communes.csv", dtype={"dep": str, "insee": str}),
        "prevention_dep": rd("prevention_dep.csv", dtype={"dep": str}),
        "pompiers": rd("pompiers_2024.csv", dtype={"dep": str}),
        "aerien": pd.read_csv(MANUAL / "moyens_aeriens.csv"),
    }
    # Toutes les années 2006-2025 pour chaque territoire, même sans feu
    grid = pd.MultiIndex.from_product([TERRITOIRES, range(ANNEE_MIN, ANNEE_MAX + 1)],
                                      names=["territoire", "annee"])
    d["feux_an"] = d["feux_an"].set_index(["territoire", "annee"]).reindex(grid, fill_value=0).reset_index()
    return d


def kpis(d):
    """Chiffres clés affichés en tête et réutilisés dans les textes."""
    c = d["climat"]

    def j30(st, a, b):
        return c[(c.station == st) & c.annee.between(a, b)].j30.mean()

    nat = d["nature"].set_index(["territoire", "periode", "variante"])

    def nat_val(col, t, p, v="toutes années"):
        return nat.loc[(t, p, v), col]

    prev = d["prevention_dep"].set_index("departement")
    pomp = d["pompiers"].set_index("departement")
    lg = d["pompiers"][d["pompiers"].territoire == "Landes de Gascogne"]
    bud = d["budget"].set_index(["departement", "annee"])
    p = d["prevention"]
    p_lg = p[p.territoire == "Landes de Gascogne"]
    LG, AM = "Landes de Gascogne", "Alpes-Maritimes"
    return {
        "j30_mdm_ref": j30("Mont-de-Marsan", 1961, 1990), "j30_mdm_now": j30("Mont-de-Marsan", 2016, 2025),
        "j30_mer_ref": j30("Bordeaux-Mérignac", 1961, 1990), "j30_mer_now": j30("Bordeaux-Mérignac", 2016, 2025),
        "j30_nice_ref": j30("Nice", 1961, 1990), "j30_nice_now": j30("Nice", 2016, 2025),
        "moy_lg_avant": nat_val("surface_moyenne_par_feu_ha", LG, "2006-2015"),
        "moy_lg_apres": nat_val("surface_moyenne_par_feu_ha", LG, "2016-2025"),
        "moy_lg_apres_hors22": nat_val("surface_moyenne_par_feu_ha", LG, "2016-2025", "hors 2022"),
        "moy_am_avant": nat_val("surface_moyenne_par_feu_ha", AM, "2006-2015"),
        "moy_am_apres": nat_val("surface_moyenne_par_feu_ha", AM, "2016-2025"),
        "nb_lg_avant": nat_val("feux_par_an", LG, "2006-2015"),
        "nb_lg_apres": nat_val("feux_par_an", LG, "2016-2025"),
        "ha_lg_2022": d["feux_an"].set_index(["territoire", "annee"]).surface_ha[(LG, 2022)],
        "risque_landes": int(prev.loc["Landes", "a_risque"]), "plan_landes": int(prev.loc["Landes", "plan_approuve"]),
        "risque_gironde": int(prev.loc["Gironde", "a_risque"]),
        "plan_gironde": int(prev.loc["Gironde", "plan_approuve"]),
        "der_appro_gironde": prev.loc["Gironde", "derniere_approbation"],
        "risque_am": int(prev.loc["Alpes-Maritimes", "a_risque"]),
        "plan_am": int(prev.loc["Alpes-Maritimes", "plan_approuve"]),
        "part_brule_sans_plan_lg": p_lg[p_lg.statut != "Plan approuvé"].surface_brulee_ha.sum()
        / p_lg.surface_brulee_ha.sum(),
        "pomp_km2_lg": lg.pompiers.sum() / lg.surface_km2.sum() * 1e3,
        "pomp_km2_am": pomp.loc["Alpes-Maritimes", "pompiers_1000km2"],
        "pomp_km2_landes": pomp.loc["Landes", "pompiers_1000km2"],
        "vol_landes": pomp.loc["Landes", "part_volontaires"],
        "bud_landes_2021": bud.loc[("Landes", 2021), "depenses_totales"],
        "bud_landes_2025": bud.loc[("Landes", 2025), "depenses_totales"],
        "bud_am_2025": bud.loc[("Alpes-Maritimes", 2025), "depenses_totales"],
        "veh_landes_2021": bud.loc[("Landes", 2021), "vehicules"],
        "veh_landes_2024": bud.loc[("Landes", 2024), "vehicules"],
    }


def tuiles(k):
    """Les 5 KPI de tête : (libellé, valeur, comparaison)."""
    return [
        ("Jours ≥ 30 °C par été à Mont-de-Marsan", f"{k['j30_mdm_now']:.0f} j",
         f"2016-2025, contre {k['j30_mdm_ref']:.0f} j en 1961-1990. Nice : {k['j30_nice_now']:.0f} j."),
        ("Surface moyenne par feu, Landes de Gascogne", f"{fmt(k['moy_lg_apres'], 1)} ha",
         f"2016-2025, contre {fmt(k['moy_lg_avant'], 1)} ha en 2006-2015 "
         f"({fmt(k['moy_lg_apres_hors22'], 1)} ha hors 2022)."),
        ("Communes landaises à risque avec un plan de prévention", f"{k['plan_landes']} / {k['risque_landes']}",
         f"Gironde : {k['plan_gironde']} / {k['risque_gironde']}. Alpes-Maritimes : {k['plan_am']} / {k['risque_am']}."),
        ("Sapeurs-pompiers pour 1 000 km², Landes de Gascogne", fmt(k["pomp_km2_lg"]),
         f"Contre {fmt(k['pomp_km2_am'])} dans les Alpes-Maritimes (2024)."),
        ("Budget du SDIS des Landes", f"{k['bud_landes_2025']:.0f} €/hab",
         f"2025, contre {k['bud_landes_2021']:.0f} € en 2021 et {k['bud_am_2025']:.0f} € dans les Alpes-Maritimes."),
    ]


def recommandations(k):
    """Chaque recommandation est reliée à un constat chiffré du dashboard."""
    return [
        ("Reconnaître le massif landais comme zone de risque « méditerranéen »",
         f"Mont-de-Marsan compte {k['j30_mdm_now']:.0f} jours ≥ 30 °C par été (2016-2025), "
         f"contre {k['j30_mdm_ref']:.0f} en 1961-1990 et {k['j30_nice_now']:.0f} à Nice.",
         "Allonger la saison de vigilance et aligner la réglementation (emploi du feu, accès aux massifs)."),
        ("Achever les plans de prévention des risques d'incendie",
         f"{k['plan_landes']} commune landaise sur {k['risque_landes']} à risque a un plan approuvé ; "
         f"en Gironde, aucun plan approuvé depuis {k['der_appro_gironde']:.0f}. "
         "Celui de La Teste-de-Buch, prescrit en 2007, ne l'est toujours pas.",
         "Prioriser l'approbation des plans dans les communes en lisière de forêt, à commencer par celles déjà touchées."),
        ("Attaquer massivement les feux naissants",
         f"Moins de départs ({fmt(k['nb_lg_avant'])} → {fmt(k['nb_lg_apres'])} feux par an), mais des feux plus "
         f"grands : {fmt(k['moy_lg_avant'], 1)} → {fmt(k['moy_lg_apres_hors22'], 1)} ha en moyenne, même hors 2022.",
         "Doctrine méditerranéenne : patrouilles armées en été et intervention en moins de 10 minutes."),
        ("Renforcer la présence de sapeurs-pompiers sur le massif",
         f"{fmt(k['pomp_km2_landes'])} pompiers pour 1 000 km² dans les Landes contre {fmt(k['pomp_km2_am'])} "
         f"dans les Alpes-Maritimes ; {pct(k['vol_landes'])} sont volontaires.",
         "Recruter des saisonniers l'été et soutenir la disponibilité des volontaires en journée."),
        ("Pérenniser l'effort budgétaire et les moyens aériens",
         f"Achats de véhicules du SDIS des Landes : {fmt(k['veh_landes_2021'], 1)} €/hab en 2021, "
         f"{fmt(k['veh_landes_2024'], 1)} €/hab en 2024. Les bombardiers d'eau restent basés à Nîmes.",
         "Sécuriser la hausse engagée après 2022 et faire du détachement aérien de Mérignac une base saisonnière permanente."),
        ("Agir sur les causes et le combustible",
         "La cause est inconnue pour environ la moitié des feux ; environ 2 causes connues sur 3 sont humaines.",
         "Faire appliquer les obligations de débroussaillement (loi du 10 juillet 2023), créer des coupures "
         "de combustible et diversifier les essences du massif."),
    ]


LIMITES = [
    "Une station météo par département : Nice est littorale et sous-estime la chaleur de l'arrière-pays.",
    "2022 pèse énormément : hors 2022, la surface brûlée annuelle des Landes de Gascogne n'augmente pas ; "
    "seule la surface moyenne par feu augmente (+56 %).",
    "Plans de prévention : presque aucune commune à risque n'en a, donc la plupart des surfaces brûlées s'y trouvent "
    "mécaniquement. Ce n'est pas une preuve de l'efficacité des plans.",
    "BDIFF : cause inconnue pour environ 50 % des feux ; 33 feux sans coordonnées (communes fusionnées).",
    "Sapeurs-pompiers : une seule année (2024) ; les surfaces sont celles des départements, pas des forêts.",
    "Centres de secours (OpenStreetMap) et bases aériennes (presse) : données indicatives, à recouper.",
    "Comptes OFGL : les achats de véhicules de la Gironde sont anormalement bas (location probable) : non interprétés.",
    "Corrélation n'est pas causalité : le climat joue surtout sur la taille des feux, pas sur leur nombre.",
]

SOURCES = [
    ("Météo-France, données climatologiques mensuelles", "https://meteo.data.gouv.fr"),
    ("BDIFF, base de données sur les incendies de forêt", "https://bdiff.agriculture.gouv.fr"),
    ("GASPAR (Géorisques), risques et plans de prévention par commune",
     "https://www.data.gouv.fr/fr/datasets/base-nationale-de-gestion-assistee-des-procedures-administratives-relatives-aux-risques-gaspar/"),
    ("DGSCGC, statistiques des services d'incendie et de secours, édition 2025",
     "https://www.interieur.gouv.fr/documentation/etudes-et-statistiques/statistiques-2024-dgscgc.html"),
    ("OFGL, comptes des SDIS 2012-2025", "https://www.data.gouv.fr/datasets/comptes-des-sdis-2012-2025"),
    ("OpenStreetMap, centres de secours", "https://www.openstreetmap.org"),
    ("geo.api.gouv.fr, communes", "https://geo.api.gouv.fr"),
]
