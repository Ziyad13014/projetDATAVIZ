# TP jour 1 : Docker, PostgreSQL et Metabase pour la Business Intelligence

**Enseignant :** Jean Delpech

**Cours :** Analyse de données avancée

**Classe :** B3 Data/IA	

**Année scolaire :** 2025/2026

**Dernière mise à jour :** avril 2026

---

**Objectif :**

Ce TP vise à vous guider dans la mise en œuvre de conteneurs basés sur des images PosgreSQL et Metabase via Docker Compose, à vous montrer une procédure simple d’ingestion de données en base et la création d’un dashboard à l’aide de Metabase. Vous saurez ainsi mettre en œuvre un (modeste) environnement BI complet parfait pour de petits projets (petites équipes, TPE/PME, associations…).

## ⚠️ Prérequis

**Avant de commencer**, assurez-vous d'avoir complété le [Guide d'installation des prérequis (TP 0)](./TP_0_installation_prerequis-FINAL.md).

Vérification rapide :
```bash
docker --version              # Doit afficher quelque chose comme v24.x ou supérieur
docker compose version        # Doit afficher v2.x ou supérieur
python3 --version            # Doit afficher 3.8 ou supérieur
pwd                          # Doit afficher /home/votre_nom/bi-formation (ou /Users/... sur Mac)
```

Si une commande ne fonctionne pas, retournez au guide d'installation.

---

## Partie 1 : Rappel Docker

Docker est une plateforme de conteneurisation qui permet d'empaqueter une application et ses dépendances dans un conteneur isolé, portable et léger.

**Analogie** : Docker est traditionnellement présenté comme un conteneur de transport maritime standardisé. Peu importe ce qu'il y a dedans (Metabase, PostgreSQL, une application web), il peut être déplacé, déployé et exécuté n'importe où de la même manière.

### Concepts clés

**Image Docker**
- Blueprint/modèle d'un conteneur
- Contient le système d'exploitation, l'application, les dépendances
- Stockée dans un registre (Docker Hub)
- Exemple : `metabase/metabase:latest`

**Conteneur Docker**
- Instance exécutable d'une image
- Environnement isolé avec ses propres processus, réseau, système de fichiers
- Léger et rapide à démarrer (secondes vs minutes pour une VM)

**Volume Docker**
- Espace de stockage persistant
- Permet de conserver les données même si le conteneur est supprimé
- Essentiel pour les bases de données

**Réseau Docker**
- Permet aux conteneurs de communiquer entre eux
- Isole les applications du réseau hôte

**Docker Compose**
- Outil pour définir et orchestrer plusieurs conteneurs
- Utilise un fichier YAML pour la configuration
- Parfait pour des stacks multi-services (base de données + application BI)

### Commandes Docker essentielles

```bash
# Télécharger une image
docker pull nom_image:tag

# Lister les images locales
docker images

# Lancer un conteneur
docker run [options] nom_image

# Lister les conteneurs en cours d'exécution
docker ps

# Lister tous les conteneurs (même arrêtés)
docker ps -a

# Arrêter un conteneur
docker stop <nom_conteneur>

# Supprimer un conteneur
docker rm <nom_conteneur>

# Voir les logs d'un conteneur
docker logs <nom_conteneur>

# Accéder au shell d'un conteneur
docker exec -it <nom_conteneur> bash
```

### Options importantes de `docker run`

```bash
-d                    # Détaché (en arrière-plan)
-p 8080:80           # Mapping de port (hôte:conteneur)
--name <mon_conteneur> # Nom personnalisé
-v /local:/conteneur # Montage de volume
-e VAR=valeur        # Variable d'environnement
--network <mon_reseau> # Connexion à un réseau spécifique
--rm                 # Suppression automatique à l'arrêt
```

---

## Partie 2 : Configuration de l'environnement

### Architecture de notre stack

![Schéma stack](./Images/Stack-Metabase.png)

### Création du fichier docker-compose.yml

1. Créez un dossier pour votre projet (s’il n’est pas déjà créé) :

```bash
mkdir bi-formation
cd bi-formation
```

2. On va devoir créer un fichier `.sql` qui indique à Postgres des bases de données à créer pour que Metabase puisse se lancer. Créez donc le fichier `init-db.sql` :

```sql
-- Script d'initialisation PostgreSQL
CREATE DATABASE metabase;
CREATE DATABASE restaurant;
\echo 'Bases de données créées avec succès !'
```

La base `metabase` est nécessaire au fonctionnement de Metabase.

On va utiliser la base `restaurant` pour notre premier dataset simple de découverte.

3. Créez le fichier `docker-compose.yml` :

```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: bi_postgres
    restart: always
    environment:
      POSTGRES_USER: bi_user
      POSTGRES_PASSWORD: bi_password123
      POSTGRES_DB: postgres  # Base par défaut (important !)
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    networks:
      - bi_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bi_user -d postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  metabase:
    image: metabase/metabase:latest
    container_name: bi_metabase
    restart: always
    ports:
      - "3000:3000"
    environment:
      MB_DB_TYPE: postgres
      MB_DB_DBNAME: metabase
      MB_DB_PORT: 5432
      MB_DB_USER: bi_user
      MB_DB_PASS: bi_password123
      MB_DB_HOST: postgres
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - bi_network

volumes:
  postgres_data:

networks:
  bi_network:
    driver: bridge
```

### Explication de la configuration

**Service PostgreSQL** :

- `postgres:15-alpine` : version 15 de PostgreSQL, variante alpine (plus légère)
- Variables d'environnement pour créer automatiquement la base de données
- Port 5432 exposé pour accès externe (optionnel pour debug)
- Volume `postgres_data` pour persistance des données
- Notez bien le préfixe `01-` dans  `./init-db.sql:/docker-entrypoint-initdb.d/01-init.sql:ro ` il est important, pour gérer l’ordre d’exécution
- Volume `./data` monté dans `/docker-entrypoint-initdb.d` : scripts SQL exécutés au premier démarrage

**Service Metabase** :

- Port 3000 pour l'interface web
- Configuration pour utiliser PostgreSQL comme base de métadonnées Metabase
- `depends_on` : assure que PostgreSQL démarre avant Metabase
- Volume pour persister la configuration Metabase

**Réseau** :
- Réseau bridge personnalisé pour la communication inter-conteneurs
- Les services peuvent se joindre par leur nom (ex: `postgres`)

### Lancement de la stack

```bash
# Démarrer les conteneurs
docker compose up -d

# Vérifier que tout fonctionne
docker compose ps

# Voir les logs
docker compose logs -f # vous pouvez faire un pipe avec grep pour chercher une info spécifique

# Arrêter la stack
docker compose down

# Arrêter et supprimer les volumes (ATTENTION : perte de données)
docker compose down -v
```

On va lancer les conteneurs petit à petit pour vérifier que tout fonctionne, mais vous pourriez lancer tout d’un coup avec `docker compose up -d` .

>  **Premier lancement** : Metabase prend 2-3 minutes pour initialiser sa base de données. Soyez patients ! Vous devriez voir apparaître quelque chose comme ça :

![Exemple lancement docker](./Images/installation-exemple.png)

1. Lancer `postgres` seulement : `docker compose up -d postgres` (vérifiez que vous êtes dans le bon répertoire)

2. Immédiatement après suivez les logs pour voir ce qu’il se passe : `docker compose logs -f postgres`. Regardez si vous voyez apparaître les lignes suivantes : 

   ```bash
   bi_postgres  | CREATE DATABASE
   bi_postgres  | CREATE DATABASE
   bi_postgres  | Bases de données créées avec succès !
   ```

   > Si vous avez lancé l’affichage des logs en continu/temps réel, vous pouvez sortir avec un `ctrl + c`, n’ayant crainte, ça n’arrêtera pas le container

3. Vous pouvez aussi les rechercher spécifiquement avec `docker compose logs -f postgres | grep -i "CREATE DATABASE"` par exemple.

4. Vérifiez ces bases avec `docker exec -it bi_postgres psql -U bi_user -d postgres -c "\l"` (`docker exec` permet d’exécuter une ligne de commande dans le container visé). Vous devriez voir un truc comme ça :

   ```
       List of databases
       Name    |  Owner  | Encoding | Locale Provider |   Collate   |    Ctype    | ...
   ------------+---------+----------+-----------------+-------------+-------------+
    metabase   | bi_user | UTF8     | libc            | en_US.utf8  | en_US.utf8  |
    postgres   | bi_user | UTF8     | libc            | en_US.utf8  | en_US.utf8  |
    restaurant | bi_user | UTF8     | libc            | en_US.utf8  | en_US.utf8  |
   ```


5. Si tout se passe bien pour Postgres, lancez ensuite le conteneur de Metabase : `docker compose up -d metabase`

### Si ça ne marche pas ?

Si ça marche, allez à la section suivante (mais n’hésitez pas à revenir ici pour lire comment on cherche un bug ou comment on reprend tout à zéro).

La première chose à faire est de tout reprendre depuis le début en vérifiant notamment que la base a été correctement initialisée (dans ce cas vous devriez voir apparaître dans les logs une phrase du type : `bi_postgres  | 2026-04-01 19:08:15.839 UTC [633] FATAL:  database "metabase" does not exist`).

1. On nettoie tout : `docker compose down -v`, ce qui devrait supprimer les volume

2. Vérifiez quand même que les volumes ont été supprimé en les listant avec `docker volume ls` si vraiment vous avez beaucoup de volume, vous pouvez faire un pipe avec `grep` : `docker volume ls | grep -i bi-formation` mais ça ne devrait pas être le cas dans ce cours

3. Si vous voyez des volumes qui restent, du genre :

   ```bash
   DRIVER    VOLUME NAME
   local     bi-formation_postgres_data
   ```

   Supprimez les manuellement : 

   ```bash
   docker volume rm bi-formation_postgres_data
   docker volume rm bi-formation_metabase_data # etc. bien sûr en fonction de ce que vous avez listé
   ```

4. Vérifiez bien les fichiers `init-db.sql` (et qu’il est bien dans le dossier `bi-formation`, ou que vous lancez bien vos commande dans ce dossier… erreur bête mais courante) et `docker-compose.yml` (cf. ci-dessus)
5. Relancez tout comme ci-dessus

#### Si ça ne marche pas : (1) on tente à la main

> Bien sûr les instructions ci-dessous ne sont pertinentes que si le problème vient de ce que la base `metabase` n’existe pas ou n’est pas créée.

Ce n’est pas très recommandé (surtout en production), mais on peut tenter de créer les bases à la volée, au démarrage :

```bash
# 1. Lancer SEULEMENT PostgreSQL
docker compose up -d postgres

# 2. Provoquer une pause de quelques secondes
sleep 10

# 3. Créer les bases MANUELLEMENT
docker exec -it bi_postgres psql -U bi_user -d postgres << EOF
CREATE DATABASE metabase;
CREATE DATABASE restaurant;
\l
EOF

# 4. Vous devez voir metabase et restaurant dans la liste avec 
docker exec -it bi_postgres psql -U bi_user -d postgres -c "\l"

# 5. Maintenant lancer Metabase
docker compose up -d metabase

# 6. Logs
docker compose logs -f metabase
```

#### Si ça ne marche toujours pas : (2) on tente avec une config minimale 

Ce n’est pas recommandé en production (performance) mais pour un usage en cours, on peut utiliser une base « intégrée » pour `metabase`, on n’utilise Postgres que pour servir les données de notre dataset. Le `.yml` correspondant est alors :

```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: bi_postgres
    restart: always
    environment:
      POSTGRES_USER: bi_user
      POSTGRES_PASSWORD: bi_password123
      POSTGRES_DB: restaurant  # Une seule base suffit
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - bi_network

  metabase:
    image: metabase/metabase:latest
    container_name: bi_metabase
    restart: always
    ports:
      - "3000:3000"
    volumes:
      - metabase_data:/metabase-data
    networks:
      - bi_network
    # PAS de configuration MB_DB_* = utilise H2 intégré

volumes:
  postgres_data:
  metabase_data:

networks:
  bi_network:
    driver: bridge
```

### Accès à Metabase

Ouvrez votre navigateur : et allez voir ce qu’il se passe à http://localhost:3000

Vous devriez voir une invite à démarrer (première connexion). Pour le moment, ne faites rien, on va d’abord scripter l’import de données dans Postgres (section suivante). Si vous ne voyez rien ou qu’un message d’erreur apparaît, jetez un œil à la section précédente.

Si vous êtes vraiment curieux, sachez qu’ensuite, lors du premier accès, vous devrez :
1. Choisir votre langue (éventuellement)
2. Créer un compte administrateur (+ répondre à quelques questions)
3. Configurer la connexion à votre base de données de données métier (important !)

Mais d’abord, le dataset !

---

## Partie 3 : Import du dataset Tips

Vous vous souvenez du dataset `Tips` que nous avions chargé depuis Seaborn ? Nous allons l’utiliser pour nous familiariser avec Metabase et le chargement dans Postgres.

> N’oubliez pas de rajouter Seaborn à votre environnement virtuel, en vérifiant bien d’abord que `venv` est bien activé !

Voici un script qui :

* charge le dataset `Tips` depuis seaborn
* se connecte à la base de donnée Posgres
* charge les données dans Postgres avec la méthode `.to_sql()`
* fait des petits tests pour vérifier que tout se passe bien

Que des choses que vous savez déjà faire normalement. Créez donc le fichier `prepare_tips_data.py` :

``` python
"""
Charge le dataset Tips dans PostgreSQL
"""
import pandas as pd
import seaborn as sns
from sqlalchemy import create_engine

# 1. Charger les données depuis seaborn
print("Chargement du dataset Tips...")
tips = sns.load_dataset('tips')

print(f"{len(tips)} lignes chargées")
print("\nAperçu des données :")
print(tips.head())
print("\nTypes de données :")
print(tips.dtypes)

# 2. Connexion PostgreSQL
DATABASE_URL = "postgresql://bi_user:bi_password123@localhost:5432/restaurant"

print("\nConnexion à PostgreSQL...")
engine = create_engine(DATABASE_URL)

# 3. Charger les données
print("\nChargement des données dans PostgreSQL...")
tips.to_sql('tips', engine, if_exists='replace', index=False)

print("Données chargées dans la table 'tips'")

# 4. Vérification
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM tips"))
    count = result.fetchone()[0]
    print(f"\nVérification : {count} lignes dans la table")

print("\nPrêt ! Vous pouvez maintenant utiliser Metabase")
print("\nInformations de connexion Metabase :")
print("  Type : PostgreSQL")
print("  Host : postgres")
print("  Port : 5432")
print("  Database : restaurant")
print("  User : bi_user")
print("  Password : bi_password123")
print("  Table : tips")
```

Bien sûr exécutez le script. Il vous rappellera les informations à saisir dans Metabase pour le connecter à la base dans l’étape suivante.

### Rappel de commandes PostgreSQL

On peut, en cas de problème où si on veut tester que tout va bien, envoyer des commandes à PostgreSQL pour lister les bases, les tables dans une base, envoyer des requêtes simples pour afficher quelques lignes d’une table…

Pour envoyer une commande (one-liner) à PostgreSQL on peut utiliser la commande `docker exec`. Voici une petite liste des commandes les plus courantes (on peut aussi envoyer des requêtes) :

```bash
# Lister les bases de données
docker exec -it bi_postgres psql -U bi_user -d postgres -c "\l"

# Lister les tables de la base "restaurant"
docker exec -it bi_postgres psql -U bi_user -d restaurant -c "\dt"

# Voir le schéma d'une table
docker exec -it bi_postgres psql -U bi_user -d restaurant -c "\d tips"

# Compter les lignes
docker exec -it bi_postgres psql -U bi_user -d restaurant -c "SELECT COUNT(*) FROM tips;"

# Voir quelques lignes
docker exec -it bi_postgres psql -U bi_user -d restaurant -c "SELECT * FROM tips LIMIT 5;"

# Mode interactif (plus pratique)
docker exec -it bi_postgres psql -U bi_user -d restaurant
# Puis taper les commandes SQL directement
# Pour sortir : \q
```

> Rappel : de base, dans un terminal on lance PostgreSQL avec `psql`, on se connecte avec un nom d’utilisateur avec `psql -U <nom_utilisateur>`
>
> Ensuite on peut envoyer des commandes raccourcies grâce à un antislash `\` : `\l` ou`\list`  permet de lister les bases de données, `\c <nom_base>` de se connecter à une base,`\dt` les tables de la base à laquelle on est connecté, etc. Voici une petite liste : 
>
> ```
> \l = liste des bases
> \d = liste des tables
> \du = liste des utilisateurs
> \dn+ = lister les schemas et les droits
> \q = quitter
> \h = aide
> USE <nom_base> = se connecter à la base <nom_base>
> \c <nom_base> = se connecter à la base <nom_base>
> SELECT version(); = version PostgreSQL
> ```

Parfois quand on veut investiguer un problème plus en profondeur on préfère se connecter de manière interactive (pour envoyer plusieurs commande à la suite, et pas juste envoyer une commande grâce à `docker exec` ). Dans ce cas on peut rentrer dans PostgreSQL dans le conteneur. Pour cela, on se connecte avec une commande `docker exec` sur un compte utilisateur de la base, et ensuite le prompt du terminal devient le prompt de PostgreSQL dans le conteneur, un peu comme avec une connexion SSH :

```
# Se connecter
docker exec -it bi_postgres psql -U bi_user -d restaurant

# Une fois connecté :
\dt                          # Lister les tables
\d tips                      # Schéma de la table tips
SELECT * FROM tips LIMIT 5;  # Voir des données
\q                           # Quitter
```

## Partie 4 : Configuration de Metabase et premières requêtes

### Configuration initiale de Metabase

1. Accédez à http://localhost:3000

2. Créez votre compte admin (utilisez des identifiants simples à retenir pour le cours) et répondez au questions

3. **Ajouter la base de données** :

   * Sélectionnez le type de base dans la liste (PosgreSQL)

   - Affichez le nom : Tips (c’est comment sera nommée la donnée dans Metabase)
   - Hôte : `postgres` (nom du service Docker)
   - Port : `5432`
   - Nom de la base : `restaurant`
   - Utilisateur : `bi_user`
   - Mot de passe : `bi_password123`
   - Table (si demandé) : `tips`
   - Ignorez les autres options 
   - Cliquez sur "Connecter la base de donnée" (vous devez avoir une infobulle qui confirme que vous êtes bien connectés)

Metabase va scanner automatiquement le schéma et vous proposer des questions suggérées.

> **Note** : Si erreur de connexion, remplacer `Host: postgres` par `Host: host.docker.internal` (Mac/Windows) ou `172.17.0.1` (Linux)

Cliquez sur « Emmenez moi dans Metabase »

### Exploration de l'interface Metabase

**Navigation principale** :

- **Home** : tableau de bord d'accueil
- **Questions** : requêtes sauvegardées
- **Dashboards** : tableaux de bord
- **Collections** : organisation des contenus
- **Données** : explorer le schéma

Prenez le temps d’explorer les différents éléments/sections. 

Vous avez un lien direct vers [des tutoriels de Metabase](https://www.metabase.com/learn/) en cliquant sur « Metabase conseils ».

Dans le volet à gauche, la section Examples mérite d’être explorée pour voir ce qu’il est possible de faire.

### 2.2 Explorer les données

**Étape 1 : Ouvrir l'explorateur**

```
Page d'accueil → Section "Données"
Cliquer sur "Bases de données"
Cliquer sur ¨"Tips"
Voir la liste des tables → Cliquer sur "tips"
```

Metabase affiche un aperçu de la table.

Si vous cliquez directement (sur la page d’accueil) sur « Un aperçu de Tips », Metabase affiche directement : 

- Nombre de lignes (244)
- Première visualisation (distribution)
- Aperçu des colonnes (menus déroulant). À droite, en sélectionnant une colonne donnée, vous pouvez avoir un aperçu plus précis (nombre de lignes, valeurs distinctes, valeurs nulles, distribution, tableaux croisés…)



**Étape 2 : Questions simples**

Sur la page de la base de donnée restaurant qui liste les tables (ici seule `Tips` apparaît), vous avez un bouton « Apprenez de vos données » : 

Vous arriverez sur une page « référentiel de données » avec des données dont `Tips`

![apprendre des données](./Images/ApprendreDonnées.png)

Vous pouvez créer un Glossaire à l’attention des collaborateurs de votre équipe.

Vous pouvez aussi définir des segments qui sont en quelques sortes des échantillons remarquables ou des zoom/vues spécifiques sur vos données.

Ce qui nous intéresse ici c’est « Nos données » -> Tips 

Vous pouvez ajouter des descriptions des données / de la table par rapport au métier dans la section « Détail ».

Et si vous cliquez sur « Tables dans Tips » -> Tips

Vous accédez à une présentation plus précise :

![Questions](./Images/Questions.png)

Ici vous pouvez avoir accès :

- détails (dont des « questions » potentielles générées automatiquement par Metabase, ici juste le nombre de de lignes, un vue de la table)
- Les champs (avec datatypes)
- Radiographier cette table vous donne les mêmes informations (ditributions, nombre de lignes…) que « Aperçu » vu précédemment
- Question à propos -> c’est là qu’on va créer nos premières visualisations (« Poser une question ») en créant des requêtes visuellement (boutons et menus pour réaliser des agrégations, filtres, tris, etc. (toutes les fontions SQL de base).
- On peut aussi poser une question avec le bouton « Nouveau » en haut à droite, puis en sélection « question »

Essayez quelques questions pour vous familiariser.

### 2.3 Créer votre première question

**Question 1 : Pourboire moyen par jour de la semaine**


1. Cliquer "+ New" (en haut à droite) → "Question"

2. Choisir les données :
   "Restaurant Tips" → "tips"

3. Construire la question (interface visuelle) :
   
   Résumer: Moyenne de ... (dans le menu déroulant) →  `tip` (sélectionner la colonne dans l’invite)
   
   Pour faire un `GROUP BY`  sélectionner « par » →  `day` (dans « choisissez une colonne d’agrégation)

4. Cliquer "Visualize"

   Metabase affiche un bar chart automatiquement !

5. Personnaliser la visualisation :
   
   Cliquer sur "Visualiser" (tout en bas à gauche)
   
   Vous obtenez automatiquement un Bar chart
   
   Avec :
     - axes des X : `day`
     - axes des Y : Moyenne de `tip`
     - Labels : Afficher les valeurs

   Vous pouvez modifier les caractéristiques de cette visualisation en cliquant sur la roue crantée en bas à gauche à côté du bouton « visualisation ». Le bouton « visualisation » quant à lui sert à modifier le type de graphique.
   
   ![Dataviz](./Images/Dataviz.png)
   
6. Sauvegarder :
   
   Cliquer "Sauvegarder" (en haut à droite)
   Nom: "Pourboire moyen par jour"
   Description : "Distribution des pourboires selon le jour de la semaine"
   
   (vous pouvez ajouter à une collection existante ou une « nouvelle collection »)
   
   Cliquer sur "Sauvegarder"
   
   Metabase demande : "Ajouter au dashboard?"
   → Choisir "Créer un nouveau dashboard"
   
   Si vous avez loupé l’infobulle, en haut droite cliquez sur les trois petits points et sélectionnez « ajouter à un dashboard »
   
   Vous aurez à nouveau la boîte de dialogue des collections, mais en bas à gauche vous aurez un bouton « nouveau dashboard», que vous pourrez nommer "Analyse Pourboires"
   
   Cliquer "Sélectionner". Vous verrez apparaître votre dataviz sur une grille
   
   Puis « Sauvegarder ».

**Vous avez créé votre première visualisation**

![](./Images/GrilleDashboard.png)



**Question 2 : Total des additions par moment (Lunch vs Dinner)**

1. "+ New" → "Question"

2. Restaurant `Tips` →`tips`

3. Construire :
   
   Résumé : Somme de... → `total_bill`
   Group by : `time`

4. Visualiser

5. Changer le type de graphique :
   
   Visualisation → `Camenbert`
   
   Settings :
     - Dans l’onglet données : 
       - Détail: `time`
       - Mesure : Somme de `total_bill`
     - Dans l’onglet Affichage 
       - Afficher les pourcentages : (sélectionner sur le graphique)
   
6. Sauvegarder :
   
   Save → "CA par moment (Lunch/Dinner)"
   Où voulez vous enregistrer ? : "Analyse Pourboires" (existant) → la figure apparaîtra direct sur la grille 
   
   (n’oubliez pas de sauvegarder !!!)

**Question 3 : Relation addition vs pourboire (scatter plot)**

1. "+ New" → "Question"

2. Restaurant Tips → `tips`

3. Cette fois, on veut juste les données brutes :
   
   Ne rien sélectionner dans "Résumé"
   Juste cliquer "Visualiser"

4. Changer la visualisation :
   
   Visualisation → Affichage → Nuage de point
   
   Settings / Données 	:
     - X-axis : total_bill
     - Y-axis : tip
     - Taille des bulles : (laisser par défaut)

6. Sauvegarder :
   
   Sauvegarder → "Corrélation Addition vs Pourboire"
   Ajouter à "Analyse Pourboires" et ne pas oublier de sauvegarder une dernière fois.

On voit ici une limite de Metabase : dans un scatterplot on aimerait pouvoir ajouter une ligne de tendance, mais ce n’est pas disponible. Deux options :

- calculer la colonne correspondante aux coordonnées y de la ligne en SQL (hardcore !)
- calculer les coordonnées des points de la droite en python et la rajouter dans une colonne de la base (pratique courante). On verra ce genre de manip (et le monitoring associé) plus tard dans le cours.

### 2.4 Finaliser le dashboard

**Étape 1 : Accéder au dashboard**

Cliquer sur les trois traits à gauche de "Accueil / Home" (logo Metabase en haut à gauche)
Section "Collection" → Cliquer sur le dashboard "Analyse Pourboires"

**Étape 2 : Organiser les visualisations**

Cliquer "Modifier le dashboard" (crayon à gauche des petites icônes en haut à droite)

Réorganiser par glisser-déposer (il peut être utile de redimensionner avant de déplacer). Ajuster les tailles en tirant sur les coins.

![Dashboard réorganisé](./Images/Dashboard.png)



**Étape 3 : Ajouter un filtre**

Dans le mode Edit :

Cliquer sur "Ajouter un filtre" (les trois petites barres parallèles qui forment un triangle)

Sélectionner le type : Texte ou Categorue → `smoker`

Connecter le filtre aux questions : sur chaque figure, dans le menu déroulant sélectionner `smoker`

Dans le panneau latéral, écrire/modifier le label du filtre (« Fumeur »)

Cliquer "OK" puis sauvegarder le dashboard

Le filtre apparaît comme un menu déroulant en haut du dashboard

**Étape 4 : Ajouter un texte explicatif**

Cliquer sur l’icône en forme de 'T' « Ajouter un en-tête ou texte »

Donner un titre : **« Analyse des pourboires »**.

Vous pouvez aussi rajouter un boîte de texte :

``` 
Résumé de l’analyse :  

Ce dashboard analyse 244 transactions de notre restaurant.

  **Questions clés :**

  - Quels jours génèrent le plus de pourboires ?
  - Lunch ou Dinner est plus rentable ?
  - Y a-t-il une corrélation entre l'addition et le pourboire ?

  **Filtres disponibles :** Fumeur/Non-fumeur
```

Toujours ne pas oublier de sauvegarder (en haut à droite)

**Étape 5 : Tester le dashboard**

Cliquer "Exit editing"

Tester le filtre :
  - Sélectionner "Yes" (fumeurs)
  - Observer les changements dans toutes les visualisations
  - Sélectionner "No" (non-fumeurs)
  - Comparer

Cliquer sur une barre dans le bar chart pour voir les options disponibles.

Vous avez votre dashboard !

### 2.5 Ajouter une question SQL custom :

L’intérêt de Metabase est qu’il n’est pas seulement « no-code » / «drag and drop », il permet aussi de créer des requêtes SQL :


"+ New" → "Requête SQL"

```SQL
  SELECT 
      day,
      time,
      COUNT(*) as nb_transactions,
      AVG(tip) as avg_tip,
      AVG(total_bill) as avg_bill,
      AVG(tip * 100.0 / total_bill) as tip_percentage
  FROM tips
  GROUP BY day, time
  ORDER BY day, time
```
Visualiser → Tableau

Personnaliser :
  - Renommer les colonnes (clic sur l'en-tête et sélectionner la roue crantée)
  - Formater tip_percentage en % (settings → ajouter un suffixe → %. Il y a aussi un style « pourcentage » mais attention il faut des valeurs entre 0 et 1 dans ce cas)

![Tableau](./Images/Tableau.png)

Sauvegarder → "Analyse détaillée par jour et moment"
Ajouter au Dashboard

![Dashboard complet](./Images/DashboardComplet.png)

## Partie 5 : Quitter

Grâce au volume `postgres_data` que nous avons mis en place, tout notre travail devrait être sauvegardé même si nous quittons Metabase et arrêtons les conteneurs :

+ Dans **Metabase** (qui stocke ses données dans la base `metabase` dans PostgreSQL) :
  - compte utilisateur
  - connexion à la base "Restaurant Tips"
  - questions/visualisations
  - dashboards
+ Dans **PostgreSQL** (et donc le volume `postgres_data`) :
  - base `metabase` et les données vues ci-dessus
  - base `restaurant`
  - table `tips` avec les 244 lignes
  - les données éventuellement ajoutées

Vérifions bien que ce volume existe avec `docker volume ls`.

Autre moyen de vérifier : 

* lister les bases de PostgreSQL avec `docker exec -it bi_postgres psql -U bi_user -d postgres -c "\l"`
* lister les tables créées par Metabase dans PostgreSQL avec `docker exec -it bi_postgres psql -U bi_user -d metabase -c "\dt"`

Si on voit de nombreuses tables c’est ok ! On peut quitter proprement Docker : `docker compose down` 

Pour redémarrer et retrouve son travail il suffira de faire `docker compose up -d`

On peut toujours sauver son travail en faisant un dump des bases PostgreSQL :

```bash
 # Exporter PostgreSQL 
 docker exec bi_postgres pg_dump -U bi_user restaurant > backup.sql 
 # Restaurer plus tard si besoin 
 docker exec -i bi_postgres psql -U bi_user restaurant < backup.sql
```


---

## Ressources

- Documentation Metabase : https://www.metabase.com/docs/latest/
- Docker Compose reference : https://docs.docker.com/compose/
- PostgreSQL tutorial : https://www.postgresql.org/docs/current/tutorial.html

---

## Pour aller plus loin

- Recommencez cette procédure avec un jeu de données réelles : le fameux [Instacart par exemple](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis) (la préparation des données sera plus complexe, il y a plusieurs tables, n’hésitez pas à explorer d’abord les données plus classiquement dans un notebook pour en prendre connaissance). Soyez prêt-e-s à me présenter votre dashboard le lundi 20 avril (note de participation).
- Réaliser des dashboards plus élaborés (créez des filtres dynamiques dans vos dashboards, etc.), n’hésitez pas à explorer des ressources sur le net, tutoriels vidéos, etc. 
- Jetez un œil à la capacité de Metabase d’envoyer des rapports automatiquement par mail (« [subscriptions](https://www.metabase.com/docs/latest/dashboards/subscriptions) »). Un serveur mail est configurée par défaut dans la version cloud de metabase, mais il faut le faire soit-même pour Metabase « self-hosted » comme nous l’avons fait. On peut, pour tester, utiliser un compte Gmail en définissant un mot de passe d’application dans votre compte Gmail et ensuite configurer Metabase pour utiliser le serveur SMTP de Gmail. Bien sûr en production il faudra utiliser d’autres méthodes, plus professionnelles.
- Explorez les "Questions suggérées" de Metabase et les exemples de données proposées
- Si les bases vues aujourd’hui sont bien assimilées, nous installerons [Apache Superset](https://superset.apache.org/) à la prochaine séance, et créerons un dashboard à partir d’un jeu de données bien plus complexe.
