# Séance 1 : Rappels et généralités
## Module Data Visualisation M2 EIA – Ynov Campus Aix

**Enseignant : Jean Delpech**

Version : octobre 2026

---

## Panorama des solutions de dataviz / dashboarding

Vous avez peut-être déjà pratiqué la plupart de ces outils en stage ou en alternance, ou en cours. Si non, certains de ces outils peuvent vous intéresser. Il s’agit là simplement de les passer en revue pour centraliser certaines informations, les comparer, retrouver des ressources facilement… À vous de compléter ce document pour votre usage, et de l’utiliser comme base pour vos explorations.

#### Metabase
- **Description** : BI libre orientée self-service : on « pose une question » via une interface simple ou en SQL, puis on l'épingle dans un dashboard.
- **Cas d'usage** : dashboards internes rapides sur une base déjà structurée, BI pour utilisateurs non développeurs.
- **Contraintes** : moins de liberté graphique qu'avec du code ; pensé pour interroger une base relationnelle (pas des fichiers bruts) ; hébergement à prévoir (JAR, Docker, ou Metabase Cloud).
- **Technos associées** : Java (serveur), connexion JDBC à PostgreSQL/MySQL/ etc.
- **Propriétaire ?**  open-source (édition Community gratuite, Enterprise payante).
- **Ressources** : 
  - site [metabase.com](https://www.metabase.com/) 
  - doc [metabase.com/docs/latest](https://www.metabase.com/docs/latest/) ·
  - tutoriels [metabase.com/learn](https://www.metabase.com/learn/)
  - vous trouverez un guide d’installation et de démarrage sur le dépôt (issu de mon cours analyse BI)

#### Apache Superset
- **Description** : plateforme de BI/exploration de données plus complète que Metabase : SQL Lab (IDE SQL intégré), large choix de types de graphiques dont des visualisations géospatiales (via deck.gl).
- **Cas d'usage** : dashboards à l'échelle d'une organisation, besoin de nombreux types de graphiques et d'un contrôle d'accès fin.
- **Contraintes** : plus lourd à déployer/administrer que Metabase, courbe d'apprentissage un peu plus longue.
- **Technos associées** : Python/Flask (backend), React (frontend), SQLAlchemy pour la connexion aux bases.
- **Propriétaire ?** projet de la fondation Apache, entièrement open-source.
- **Ressources** : 
  - site [superset.apache.org](https://superset.apache.org/)
  - galerie [superset.apache.org/gallery](https://superset.apache.org/gallery)
  - doc [superset.apache.org/docs/intro](https://superset.apache.org/docs/intro)

#### Dash (Plotly)
- **Description** : framework Python pour construire des applications web de dataviz interactives sur-mesure (layout + callbacks), bâti sur Plotly.js, React et Flask.
- **Cas d'usage** : logique métier spécifique qu'un outil de BI standard ne permet pas (interactions complexes, intégration à un modèle ML...).
- **Contraintes** : demande d'écrire du code et de concevoir l'interface soi-même, déploiement à gérer (sauf Dash Enterprise, payant).
- **Technos associées** : Python, Plotly.js/React sous le capot, s'intègre bien avec Pandas/GeoPandas.
- **Propriétaire ?** Non pour Dash lui-même (open-source), une offre « Enterprise » payante existe pour le déploiement/l'administration.
- **Ressources** : 
- site [plotly.com/dash](https://plotly.com/dash/)
- doc[dash.plotly.com](https://dash.plotly.com/)
- galerie d'exemples [plotly.com/examples](https://plotly.com/examples/)
- tutoriel officiel « Dash in 20 Minutes » sur dash.plotly.com/tutorial

*Pour mémoire, en comparaison avec ce que vous connaissez déjà* : **Streamlit** reste la référence la plus simple pour un prototypage rapide en Python pur, mais offre moins de contrôle fin sur l'interface que Dash.

#### Stack géospatiale Python
Il ne s'agit pas d'un outil unique mais de plusieurs briques complémentaires :

- **GeoPandas** : extension de pandas pour manipuler des données géospatiales vectorielles (`GeoDataFrame`), lire des shapefiles/GeoJSON.
  [geopandas.org](https://geopandas.org/en/latest/)
- **Shapely** : manipulation géométrique bas niveau (points, lignes, polygones, opérations spatiales comme l'intersection ou le buffer).
  [shapely.readthedocs.io](https://shapely.readthedocs.io/)
- **GDAL** : bibliothèque bas niveau de lecture/écriture/conversion de formats géospatiaux (vecteur et raster), souvent la dépendance invisible derrièreGeoPandas. *
  [gdal.org](https://gdal.org/)
- **Cartopy** : cartes statiques avec projections cartographiques, intégré à Matplotlib, adapté à un usage scientifique/publication plutôt qu'interactif. 
  [scitools.org.uk/cartopy/docs/latest](https://scitools.org.uk/cartopy/docs/latest/)
- **Folium / Leaflet** : cartes interactives web depuis Python : Folium génère du Leaflet.js. 
  [python-visualization.github.io/folium/latest](https://python-visualization.github.io/folium/latest/)
  Site Leaflet : [leafletjs.com](https://leafletjs.com/)
- **Cas d'usage** : toute donnée à composante spatiale (adresses, communes, zones, trajets, réseaux).
- **Contraintes** : 
  - GDAL peut être délicat à installer selon l'OS (dépendances système)
  - Cartopy convient aux cartes statiques, pas à l'interactif
  - Folium reste limité en volumétrie (rendu côté client, un millier de point max pour Leaflet. Au-delà il faut du WebGL avec MapLibre par exemple).
- **Propriétaire ?** Toute la stack est open-source.

#### Tableau
- **Description** : solution de BI propriétaire leader du marché, interface glisser-déposer très riche en interactions, forte communauté.
- **Cas d'usage** : dataviz d'entreprise avec forte exigence de finition visuelle et de self-service pour utilisateurs non techniques ; très utilisé aussi en datajournalisme via Tableau Public.
- **Contraintes** : licence payante (sauf Tableau Public, gratuit mais données publiées publiquement) ; moins flexible que du code pour une logique très spécifique.
- **Technos associées** : VizQL (moteur propriétaire de requêtage visuel).
- **Propriétaire ?** Oui (Salesforce). Usage gratuit via Tableau Public (visualisation publique).
- **Ressources** : 
  - site [tableau.com](https://www.tableau.com/)
  - formations[tableau.com/learn/training](https://www.tableau.com/learn/training) 
  - galerie/hébergement gratuit [public.tableau.com](https://public.tableau.com/)

#### Power BI
- **Description** : solution de BI propriétaire de Microsoft, forte intégration à l'écosystème Microsoft/Excel, langage DAX pour les mesures.
- **Cas d'usage** : organisations déjà sur l'écosystème Microsoft (Excel, Azure, SharePoint), reporting périodique.
- **Contraintes** : Power BI Desktop est gratuit pour créer, mais le partage via le service en ligne nécessite une licence au-delà d'un usage individuel. DAX a sa propre courbe d'apprentissage.
- **Technos associées** : DAX (mesures), Power Query / langage M (préparation des données).
- **Propriétaire ?** Oui (Microsoft).
- **Ressources** : 
  - doc officielle [learn.microsoft.com/power-bi](https://learn.microsoft.com/power-bi/)
  - téléchargement [powerbi.microsoft.com](https://powerbi.microsoft.com/)
  - formations gratuites sur Microsoft Learn

#### Écosystème JavaScript « bas niveau »
Ces briques sont mentionnées pour que vous sachiez qu'elles existent et à quoi elles servent si vous vous spécialisez un jour. Ce n'est **pas** l'outillage attendu pour ce module.

- **D3.js** : bibliothèque JS bas niveau de manipulation du DOM/SVG pilotée par la donnée. Contrôle total, coût d'apprentissage élevé.
  Site : [d3js.org](https://d3js.org/)
  galerie [observablehq.com/@d3/gallery](https://observablehq.com/@d3/gallery)
- **React / Vue** : frameworks JS d'interface. Pas des outils de dataviz en soi, mais l'écosystème dans lequel s'intègrent des composants de graphique en production. [react.dev](https://react.dev/) · [vuejs.org](https://vuejs.org/)
- **Three.js** : rendu 3D (WebGL) en JS. Usage niche en dataviz (visualisation volumétrique, VR/AR), mais puissant. [threejs.org](https://threejs.org/)
- **MapLibre GL JS** :  cartographie vectorielle interactive, fork open-source de Mapbox GL JS. [maplibre.org](https://maplibre.org/)
- **kepler.gl** : outil (React, bâti sur MapLibre + deck.gl) d'exploration visuelle de données géospatiales volumineuses, sans code.
  [kepler.gl](https://kepler.gl/) · doc [docs.kepler.gl](https://docs.kepler.gl/)

### 5.3 Tableau comparatif

| Solution | Propriétaire ? | Technos clés | Cas d'usage type | Contrainte principale |
|---|---|---|---|---|
| Metabase | Non (Community gratuite) | Java, JDBC | BI self-service rapide, utilisateurs non techniques | Peu de liberté graphique |
| Apache Superset | Non | Python/Flask, React, SQLAlchemy | BI à l'échelle, nombreux types de viz, géospatial inclus | Déploiement/administration plus lourds |
| Dash (Plotly) | Non (Enterprise payante en option) | Python, Plotly.js, React | App interactive sur-mesure, logique métier spécifique | Demande du code et une conception d'UI |
| Streamlit *(déjà connu)* | Non | Python | Prototypage rapide en Python pur | Moins de contrôle fin sur l'UI que Dash |
| Stack géospatiale Python | Non | GeoPandas, Shapely, GDAL, Cartopy, Folium/Leaflet | Toute donnée à composante spatiale | GDAL parfois délicat à installer |
| Tableau | Oui (Tableau Public gratuit) | VizQL | BI d'entreprise très finie, datajournalisme | Licence payante hors Tableau Public |
| Power BI | Oui | DAX, Power Query | Entreprises sur écosystème Microsoft | Partage en ligne payant au-delà d'un usage individuel |
| D3.js *(mention)* | Non | JavaScript, SVG/DOM | Dataviz web sur-mesure, besoin total de contrôle | Coût d'apprentissage élevé |
| kepler.gl *(mention)* | Non | React, MapLibre, deck.gl | Exploration géospatiale de gros volumes, sans code | Spécialisé géospatial uniquement |
