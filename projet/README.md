# Le massif landais devient-il méditerranéen ?

Projet du module **Concevoir une dataviz** (M2 IA/Data, Ynov Aix, octobre 2026), réalisé sur le défi
[Changement climatique](https://defis.data.gouv.fr/defis/changement-climatique) de l'Open Data University.

Deux versions du même tableau de bord, construites sur les mêmes données préparées :

| Version | Dossier | Lancement | Adresse |
|---|---|---|---|
| Dash + Plotly | `app_dash/` | `python app_dash/app.py` | http://127.0.0.1:8050 |
| Streamlit + Altair | `app_altair/` | `streamlit run app_altair/app.py` | http://localhost:8501 |
| **Rapport façon Power BI** (Dash, 5 pages d'un écran : climat → incendies → prévention → moyens → verdict) | `app_dash/ecran.py` | `python app_dash/ecran.py` | http://127.0.0.1:8052 |

Les deux versions Dash partagent les mêmes graphiques (`app_dash/figures.py`). Le rapport tient sur un écran dès 700 px de haut (plein écran F11 conseillé sur un portable) ; on peut ouvrir directement une étape avec `?page=climat`, `incendies`, `prevention`, `moyens` ou `verdict`.

## 1. Cadrage

**Problématique** : le réchauffement fait-il basculer le massif des Landes de Gascogne (Gironde + Landes)
vers un risque d'incendie de type méditerranéen, et ses moyens de prévention et de lutte sont-ils à la hauteur ?

| Élément | Réponse |
|---|---|
| Public | Préfectures, SDIS et élus de Gironde, des Landes et des Alpes-Maritimes |
| Décision visée | Faut-il aligner la prévention et les moyens du massif landais sur le modèle méditerranéen ? |
| Message en une phrase | Les étés landais sont désormais plus chauds que ceux de Nice, et le massif reste moins couvert par les plans de prévention et moins doté en pompiers au km². |
| Territoire témoin | Alpes-Maritimes : territoire méditerranéen habitué aux feux |
| Période | 2006-2025 pour les incendies, 1950-2025 pour le climat |

**Questions métier** :

1. Le climat des Landes devient-il méditerranéen ?
2. Les incendies landais changent-ils de nature ?
3. La prévention réglementaire est-elle à la hauteur du risque ?
4. Les moyens de lutte sont-ils à la hauteur du territoire à défendre ?

**Les 5 KPI de tête** (chacun avec un point de comparaison) :

| KPI | Valeur | Comparaison |
|---|---|---|
| Jours ≥ 30 °C par été à Mont-de-Marsan | 33 j (2016-2025) | 17 j en 1961-1990, Nice : 15 j |
| Surface moyenne par feu, Landes de Gascogne | 16,1 ha (2016-2025) | 1,6 ha en 2006-2015 ; 2,5 ha hors 2022 |
| Communes landaises à risque avec un plan de prévention | 0 / 182 | Gironde 13 / 159, Alpes-Maritimes 46 / 163 |
| Sapeurs-pompiers pour 1 000 km², Landes de Gascogne | 374 (2024) | Alpes-Maritimes : 1 056 |
| Budget du SDIS des Landes | 103 €/hab (2025) | 80 € en 2021, 150 € dans les Alpes-Maritimes |

**Jalons** : cadrage → collecte et préparation des données → prototype (deux versions) →
itérations UX, accessibilité, storytelling → choix de la version finale → soutenance.

## 2. Données

| Source | Producteur | Contenu | Fichier brut |
|---|---|---|---|
| [Données climatologiques mensuelles](https://meteo.data.gouv.fr) | Météo-France | Températures, pluie, jours ≥ 30 °C par station | `data/raw/MENSQ_*.csv.gz` |
| [BDIFF](https://bdiff.agriculture.gouv.fr) | Ministère de l'Agriculture | 7 359 feux de forêt (06, 33, 40), 2006-2025 | `data/raw/BDIFF_incendies_06_33_40_2006-2025.csv` |
| [GASPAR](https://www.data.gouv.fr/fr/datasets/base-nationale-de-gestion-assistee-des-procedures-administratives-relatives-aux-risques-gaspar/) | Ministère de la Transition écologique | Communes à risque feu de forêt, plans de prévention (PPRIF) | `data/raw/gaspar/` |
| [Statistiques des SIS, édition 2025](https://www.interieur.gouv.fr/documentation/etudes-et-statistiques/statistiques-2024-dgscgc.html) | DGSCGC (ministère de l'Intérieur) | Effectifs de pompiers 2024 (annexes p. 68-70, saisis à la main) | `data/raw/dgscgc_stats_sdis_2024.csv` |
| [Comptes des SDIS 2012-2025](https://www.data.gouv.fr/datasets/comptes-des-sdis-2012-2025) | OFGL | Dépenses par habitant (totales, véhicules) | `data/raw/ofgl_sdis.csv` |
| [geo.api.gouv.fr](https://geo.api.gouv.fr) | Etalab / IGN / Insee | Communes : coordonnées, surface, population | `data/raw/geo/` |
| [OpenStreetMap](https://www.openstreetmap.org) | Contributeurs OSM | Centres de secours (complément indicatif) | `data/raw/osm/` |
| Presse | Brut, Maire-info | Bases aériennes (indicatif) | `data/manual/moyens_aeriens.csv` |

Stations météo de référence : Nice (06088001), Bordeaux-Mérignac (33281001), Mont-de-Marsan (40192001).

Préparation : `python src/prepare_data.py` lit `data/raw/` et écrit les tables propres dans `data/processed/`.
Les deux applications lisent les mêmes fichiers via `src/common.py` (chargement, couleurs, KPI,
recommandations, limites) : un texte modifié là change dans les deux versions.

## 3. Structure du tableau de bord

Le déroulé suit le storytelling vu en cours (contexte → problème → preuve → action) :

1. **Climat** : jours ≥ 30 °C par été, bandes de réchauffement (écart à la normale 1961-1990).
2. **Incendies** : surface brûlée par an, nombre de feux et surface moyenne par feu (avec ou sans 2022),
   carte par commune, lien entre chaleur et surface brûlée.
3. **Prévention** : communes à risque et état de leur plan de prévention, carte par commune.
4. **Moyens** : sapeurs-pompiers par km², budget des SDIS, achats de véhicules, bases aériennes.
5. **Recommandations** : chaque action découle d'un constat chiffré.
6. **Limites et sources.**

Interactions : période, territoire des cartes, échelle linéaire ou logarithmique, exclusion de 2022,
légendes cliquables, sélection d'années à la souris (Altair), tableau de données dépliable.

## 4. Dash ou Altair : éléments pour argumenter le choix

| Critère | Dash + Plotly | Streamlit + Altair |
|---|---|---|
| Interactions entre graphiques | Par callbacks Python : plus de code, contrôle total | Déclaratives (grammaire Vega-Lite) : sélection d'années qui filtre carte et classement en quelques lignes |
| Mise en page | Grille Bootstrap, entièrement maîtrisée | Simple, moins personnalisable |
| Cartes | Fond de carte interactif (zoom, déplacement) | Fond vectoriel statique, sans zoom |
| Temps de développement | Plus long | Plus court |
| Lien avec le cours | Outil BI sur mesure | Grammaire de visualisation (Wilkinson, Vega-Lite) |

## 5. Limites

- Une station météo par département ; Nice est littorale et sous-estime la chaleur de l'arrière-pays.
- 2022 pèse énormément : hors 2022, la surface brûlée annuelle des Landes de Gascogne n'augmente pas ;
  seule la surface moyenne par feu augmente (+56 %, et +75 % dans les Alpes-Maritimes).
- Plans de prévention : presque aucune commune à risque n'en a, donc la plupart des surfaces brûlées s'y trouvent
  mécaniquement. Ce n'est pas une preuve de l'efficacité des plans.
- BDIFF : cause inconnue pour environ 50 % des feux, 33 feux sans coordonnées (communes fusionnées).
- Sapeurs-pompiers : une seule année (2024) ; surfaces des départements, pas des forêts.
- Centres de secours (OSM) et bases aériennes (presse) : indicatifs.
- OFGL : achats de véhicules de la Gironde anormalement bas (location probable), non interprétés.
- Corrélation n'est pas causalité : le climat joue surtout sur la taille des feux, pas sur leur nombre.

## Installation

Sous Windows, un double-clic sur `lancer_dash.bat` ou `lancer_altair.bat` suffit à lancer un dashboard.
Sinon, depuis ce dossier :

```bash
pip install -r requirements.txt
python src/prepare_data.py
```

L'app Streamlit est forcée en thème clair par `.streamlit/config.toml` (à lancer depuis le dossier `projet/`).
