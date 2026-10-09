# TP 3 : Apache Superset et dashboards avancés sur Instacart

**Enseignant :** Jean Delpech

**Cours :** Analyse de données avancée

**Classe :** B3 Data/IA	

**Année scolaire :** 2025/2026

**Dernière mise à jour :** avril 2026

---

**Objectif :**

Ce TP vous guide dans l'installation d'Apache Superset, un outil BI open-source plus puissant que Metabase, et la création de dashboards avancés sur le dataset Instacart. L’installation est très délicate, notamment pour la connexion avec la base de donnée. Même si j’ai essayé d’être assez complet et d’expliquer le plus de choses possibles, il y a des détails très techniques au sein des fichiers de configuration que vous ne verrez pas forcément au premier coup d’œil, n’hésitez pas à poser des questions. Dans ce TPdécouvrirez les différences d'architecture – et les points communs – entre Metabase et Superset, et exploiterez des visualisations plus sophistiquées (heatmaps, treemaps, etc.).

---

## ⚠️ Prérequis

**Avant de commencer**, assurez-vous d'avoir :

+ Complété le [TP 0 (Installation des prérequis)](./TP_0_installation_prerequis-FINAL.md)  
+ Complété le [TP 1 (Docker, PostgreSQL et Metabase)](./TP_1_docker_metabase-FINAL.md)  
+ Complété le [TP 2 (Import Instacart et dashboards Metabase)](./TP_2_metabase-instacart.md)  
+ Base de données `instacart` chargée avec ~37M lignes (ce qui devrait être le cas si vous avez fait le TP 2)

Vérification rapide :
```bash
cd ~/bi-formation
docker compose ps  # PostgreSQL et Metabase doivent être "Up"

# Vérifier que la base Instacart existe
docker exec -it bi_postgres psql -U bi_user -d postgres -c "\l" | grep instacart

# Vérifier le nombre de lignes
docker exec -it bi_postgres psql -U bi_user -d instacart -c "SELECT COUNT(*) FROM order_products_prior;"
# Doit afficher : ~32,434,489
```

---

## Partie 1 : Comprendre Apache Superset

### 1.1 Qu'est-ce que Superset ?

**Apache Superset** est une plateforme open-source de visualisation de données et d'exploration, créée par Airbnb en 2015 puis donnée à la fondation Apache.

**Différences clés avec Metabase** :

| Aspect | Metabase | Superset |
|--------|----------|----------|
| **Philosophie** | Simplicité, business users | Puissance, data analysts |
| **Visualisations** | ~15 types | 50+ types |
| **SQL Lab** | Éditeur basique | IDE SQL complet |
| **Architecture** | Simple (1 conteneur suffit) | Complexe (app + cache + async) |
| **Courbe d'apprentissage** | 10 minutes | 30-60 minutes |
| **Performance** | Bonne (<10M lignes) | Excellente (100M+ lignes) |
| **Customisation** | Limitée | Très étendue (plugins, API) |

**Quand utiliser Superset ?** 
- Équipe technique (à l'aise avec SQL)
- Besoin de visualisations variées (heatmaps, treemaps, etc.)
- Gros volumes de données (>10M lignes)
- Besoin de SQL Lab pour exploration
- Customisation/embedding avancé

**Pourquoi préférer de tels outils assez rigides plutôt qu’un bon vieux Streamlit qui permet un contrôle plus libre des dataviz ?**

Il ne faut pas perdre de vue qu’une solution est créée pour répondre à certaines contraintes, notamment industrielles. Le terme « industriel » n’est pas usurpé par des outils tels que Superset, qui sont développés et mis en œuvre par des grands comptes ou des multinationales. Ces outils de dataviz ne se contentent pas de « juste » créer des graphiques ou des dashboards accessibles via son navigateur. Il faut prendre un peu de recul et ne pas s’imaginer que tout est comparable au fait de développer un petit dashboard en local pour afficher les données téléchargées sur Kaggle et stockée sur une petite base de quelques milliers de lignes servit par une API qui répond à une requête d’un utilisateur toutes les 10 minutes. 

[Voici un article de 2021](https://medium.com/airbnb-engineering/supercharging-apache-superset-b1a2393278bd) d’Erik Ritter (Tech lead chez AirBnB à l’époque et aujourd’hui membre du staff technique d’OpenAI) sur l’utilisation de Superset à AirBnB. On y apprend qu’alors Superset servait, sur une base **hebdomadaire** :

* 6 000 dashboards
* 125 000 figures
* 50 000 requêtes
* pour 2 000 utilisateurs

**Globalement en 2021 leur système gérait 100 000 tables, 200 000 figures et 14 000 dashboards. 25% des employés à AirBnB utilisent Superset.** On peut facilement imaginer que ce nombre n’a pu que croître depuis. Cette scalabilité implique la mise en place d’un système de cache (Redis), d’une optimisation du moteur de requête (Presto, Apache Druid) avec de nombreux jobs en tâche de fond (Airflow). Afficher un dashboard dans un navigateur demande l’exécution d’autant de requêtes en simultané que ce qu’il y a de figures, ce qui demande de contourner les limitations des navigateurs (qui limitent le nombre de requêtes simultanées, créant un goulot d’étranglement). Je paraphrase ici la présentation chiffrée d’Erick Nitter dans son article.

Donc se dire que développer un dashboard sur stremalit se fait avec plus de facilité et de liberté, c’est comme comparer une presse hydraulique à un marteau, en trouvant qu’une presse n’a aucun intérêt car moins flexible dans son utilisation qu’un marteau ! Comme souvent ces jugements ridicules oublient que la différence se joue sur le contexte d’usage, conduisant à des comparaisons biaisées.

Il est donc important, malgré les désagréments de devoir se conformer à une logique rigide et de ressentir sa liberté restreinte, de connaître ces outils qui sont des standards industriels. 

### 1.2 Architecture (simplifiée) de Superset

Contrairement à Metabase (un simple processus Python/Java), Superset nécessite plusieurs composants :

![Architecture Superset](./Images/Superset-Archi.png)


**Composants** :

1. **Superset (application principale)** :
   - Application Flask (Python backend)
   - Interface React (frontend)
   - Port : 8088

2. **Redis** (cache) :
   - Stocke les résultats de requêtes en cache
   - Accélère l'affichage des dashboards
   - Évite de re-exécuter les mêmes requêtes SQL
   - Port : interne, pas exposé

3. **Celery** (tâches asynchrones - optionnel en dev) :
   - Exécute les requêtes longues en arrière-plan
   - Génération de rapports
   - Envoi d'emails
   - Pas nécessaire pour notre setup de formation

4. **PostgreSQL (métadonnées)** :
   - Base `superset` : stocke dashboards, charts, users
   - Base `instacart` : vos données à visualiser

   **Pourquoi cette complexité ?**

Cette complexité est essentiellement due au fait que Superset a vocation à traiter un volume massif de données (« big data ») :

- **Redis** : Superset fait des requêtes SQL potentiellement lourdes. Redis cache les résultats pour éviter de surcharger la base.
- **Plusieurs bases** : Sépare les métadonnées Superset (config) des données métier (instacart) - c’était déjà le cas avec Metabase.
- **Scalabilité** : Architecture pensée pour le big data et la production

#### Installation

Maintenant que vous avez une vue d’ensemble de Superset et de ses composant, nous allons l’installer. La procédure sera sensiblement la même que ce que nous avons fait pour Metabase :

- configuration avec un `docker-compose.yml` : on va rajouter les services `superset:` et `redis:`. La configuration sera un peu plus compliquée car on va devoir définir un peu plus de choses que pour Metabase
- création d’une base de donnée pour les metadonnées de Superset
- au premier démarrage : téléchargement des images, installation, surveillance des logs, création de l’utilisateur admin…
- lancement de Superset, connexion de la base Instacart
- création de nos premières figures et assemblage du premier dashboard

---

## Partie 2 : Configuration du docker-compose.yml

### 2.1 Ajouter Superset et Redis

Nous allons **modifier** le fichier `docker-compose.yml` existant pour **ajouter** Superset et Redis.

**Ouvrez** `~/bi-formation/docker-compose.yml` :

```bash
cd ~/bi-formation
nano docker-compose.yml  # ou code docker-compose.yml ou vi docker-compose.yml
```

**Ajoutez ces deux services** à la fin du fichier (après les services `postgres:` et `metabase:`, et avant `volumes:`, ne touchez pas au reste) :

```yaml
services:
  postgres:
    # ... (configuration existante, ne pas modifier)

  metabase:
    # ... (configuration existante, ne pas modifier)

  # NOUVEAUX SERVICES CI-DESSOUS

  redis:
    image: redis:7-alpine
    container_name: bi_redis
    restart: always
    ports:
      - "6379:6379"
    networks:
      - bi_network
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

  superset:
    image: apache/superset:latest
    container_name: bi_superset
    restart: always
    ports:
      - "8088:8088"
    environment:
      # Secret key pour sécuriser les sessions
      SUPERSET_SECRET_KEY: "votre_cle_secrete_super_longue_et_aleatoire_123456789"
      
      # Configuration de la base de métadonnées Superset
      DATABASE_DIALECT: postgresql
      DATABASE_USER: bi_user
      DATABASE_PASSWORD: bi_password123
      DATABASE_HOST: postgres
      DATABASE_PORT: 5432
      DATABASE_DB: superset
      
      # Configuration Redis pour le cache
      REDIS_HOST: redis
      REDIS_PORT: 6379
      
      # Désactiver les exemples (optionnel)
      SUPERSET_LOAD_EXAMPLES: "no"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - bi_network
    command: >
      bash -c "
        superset db upgrade &&
        superset fab create-admin --username admin --firstname Admin --lastname User --email admin@example.com --password admin &&
        superset init &&
        gunicorn --bind 0.0.0.0:8088 --workers 4 --timeout 120 'superset.app:create_app()'
      "
# laisser ensuite la définition des volumes et networks telle quelle :
volumes:
  postgres_data:

networks:
  bi_network:
    driver: bridge
```

Attention quand vous faites le copier coller. Yaml est très pointilleux sur les indentations (*une indentation = deux espaces*). C’est souvent source de problèmes. Voici un rappel des indentations attendues :

```
services:
··postgres:    # 2 espaces
····image: ... # 4 espaces (2 de plus)
··metabase:    # 2 espaces
··redis:       # 2 espaces
··superset:    # 2 espaces
```

Si vous avez un message d’erreur de type :

```
yaml: line XXX: did not find expected key 
```

Allez à la ligne XXX et vérifier l’indentation, c’est une erreur très courante. Pour voir facilement les espaces dans l’éditeur que vous aurez choisi :

* VS Code : `View → Render Whitespace`
* si vous utilisez nano : Les espaces sont visibles naturellement
* et pour vim :  `:set listchars=space:.,tab:>-` puis `:set list` (affichera un `.` pour les espace et un `-` pour les tabulations)

Rappel : il faut deux espaces pour une indentation dans un fichier `.yml` et pas de tabulation !

### 2.2 Comprendre la configuration Superset

Voici quelques points sensibles de la config qui nécessitent quelques explications :

#### SUPERSET_SECRET_KEY

C’est une clé secrète utilisée par Flask (framework Python de Superset) pour :

- Chiffrer les sessions utilisateur (cookies)
- Signer les tokens de sécurité (CSRF protection)
- Protéger les données sensibles en mémoire

C’est le développeur qui la définit en choisissant une valeur alphanumérique aléatoire suffisamment longue, qui devra être conservée.

**Bonnes pratiques** :

1. **En développement/formation** (comme maintenant) :
   Par simplicité on peut se contenter de définir la clé avec quelque chose de simple et facile à retenir

   ```yaml
   SUPERSET_SECRET_KEY: "votre_cle_secrete_super_longue_et_aleatoire_123456789"
   ```
   - N'importe quelle chaîne longue (>30 caractères)
   - Peut contenir lettres, chiffres, symboles
   - Exemple simple : `formation_bi_ynov_2026_secret_key_12345`

2. **En production** :
   C’est une autre histoire : il faut adopter des pratiques robustes qui garantissent la sécurité : chaîne longue et réellement aléatoire, stockée comme un secret dans une variable d’environnement dédiée. Bien sûr vous pouvez décider dès le début du développement d’adopter ces pratiques pour éviter de mettre en production une app non sécurisée, ce qui alourdit un peu. Comment il faut faire :

   ```yaml
   # dans le fichier de config
   SUPERSET_SECRET_KEY: "${SUPERSET_SECRET_KEY}"  # Variable d'environnement
   ```
   Puis dans un fichier `.env` (**non commité dans Git**, pensez à configurer votre .gitignore) :
   ```bash
   # .env
   SUPERSET_SECRET_KEY="Kp9#mL2$xR7@nQ4&wT8!vZ1^yH6%fJ3"
   ```

   Pour générer une clé aléatoire sécurisée :
   ```bash
   # Méthode 1
   openssl rand -base64 42
   
   # Méthode 2
   python3 -c "import secrets; print(secrets.token_urlsafe(42))"
   ```

   **Que se passe-t-il si on ne la définit pas ?**

   Superset génère une clé aléatoire à **chaque redémarrage** → tous les utilisateurs sont déconnectés, les dashboards publics cassent, etc.

   Pour ce TP je vous conseille de gardez une clé simple et fixe dans le `docker-compose.yml`, à moins de vouloir vous entraîner aux pratiques vues ci-dessus.

#### Commande de démarrage Superset

Dans le fichier de config on définit une série de commandes qui seront exécutées au démarrage :

```yaml
command: >
  bash -c "
    superset db upgrade &&
    superset fab create-admin ... &&
    superset init &&
    gunicorn ...
  "
```

**Commandes exécutées au démarrage** :

1. `superset db upgrade` : Crée/met à jour le schéma de la base `superset` (tables pour dashboards, users, etc.)

2. `superset fab create-admin` : Crée un compte administrateur. Lors du développement ou de la formation, même idée que précédemment, on crée des credentials simples et facile à retenir :
   - Username : `admin`
   - Password : `admin`
   - Email : `admin@example.com`
   - ⚠️ **En production, changez ces credentials !** C’est une erreur typique de mettre en production des environnements avec des credentials de dév ou temporaires trop simples.

3. `superset init` : Initialise les rôles et permissions

4. `gunicorn` : Lance le serveur web
   - `--workers 4` : 4 processus parallèles (1 par CPU recommandé)
   - `--timeout 120` : Timeout de 120s pour les requêtes longues
   - Port `8088`

#### Configuration Redis

```yaml
command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

**Explication** :
- `--maxmemory 256mb` : Limite la RAM Redis à 256 MB (suffisant pour notre usage)
- `--maxmemory-policy allkeys-lru` : Quand la mémoire est pleine, supprime les clés les moins récemment utilisées (Least Recently Used)

On évite ainsi que Redis consomme toute la RAM disponible (surtout sur une machine locale). Ici nous n’allons pas avoir vraiment besoin de mettre beaucoup de requêtes en cache.

### 2.3 Créer la base de métadonnées Superset

De base Superset utilise SQLite (c’est souvent le cas : en phase de développement on utilise plutôt SQLite en local avant de configurer une « vraie » base avant de mettre en production). Ici nous avons défini une base PostgreSQL dans notre `docker-compose.yml` pour se placer en condition réelle de production.

Avant de lancer Superset, créons donc la base PostgreSQL pour ses métadonnées :

```bash
# Créer la base 'superset'
docker exec -it bi_postgres psql -U bi_user -d postgres -c "CREATE DATABASE superset;"

# Vérifier
docker exec -it bi_postgres psql -U bi_user -d postgres -c "\l" | grep superset
```

Vous devriez voir :
```
 superset  | bi_user | UTF8 | ...
```

---

## Partie 3 : Lancement de Superset

### 3.1 Démarrer les nouveaux services

Normalement quand vous démarrez ce TP vous avez déjà les conteneurs PostgreSQL et Metabase qui tournent. Il faut donc lancer individuellement les conteneurs que nous venons de configurer (Redis et Superset) :

```bash
cd ~/bi-formation

# Lancer Redis et Superset (PostgreSQL et Metabase déjà lancés)
docker compose up -d redis superset
```

Dans les autres cas (vous reprenez votre travail et venez de relancer Ubuntu p. ex.), un simple `docker compose up -d` suffit. N’oubliez pas l’option `-d` pour lancer les conteneurs en tâche de fond (en réalité vous pouvez toujours le faire après si vous avez oublié avec le raccourci `d`)

Vous devriez alors voir quelque chose comme :

```
[+] up 5/5
 ✔ Network bi-formation_bi_network Created                                                                          0.1s
 ✔ Container bi_redis              Created                                                                          0.2s
 ✔ Container bi_postgres           Healthy                                                                          6.8s
 ✔ Container bi_superset           Created                                                                          0.2s
 ✔ Container bi_metabase           Created   
```

Si vous voulez vérifier l'état des conteneurs (vérifier ce qui tourne ou pas), faire un `docker compose ps` et vous devrez voir apparaître :

```bash
NAME          IMAGE                      COMMAND                   SERVICE    CREATED         STATUS                   PORTS
bi_metabase   metabase/metabase:latest   "/app/run_metabase.sh"    metabase   4 minutes ago   Up 4 minutes             0.0.0.0:3000->3000/tcp, [::]:3000->3000/tcp
bi_postgres   postgres:15-alpine         "docker-entrypoint.s…"    postgres   4 minutes ago   Up 4 minutes (healthy)   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
bi_redis      redis:7-alpine             "docker-entrypoint.s…"    redis      4 minutes ago   Up 4 minutes             0.0.0.0:6379->6379/tcp, [::]:6379->6379/tcp
bi_superset   apache/superset:latest     "bash -c '\n  superse…"   superset   4 minutes ago   Up 4 minutes (healthy)   0.0.0.0:8088->8088/tcp, [::]:8088->8088/tcp

```

### 3.2 Suivre le démarrage de Superset

Le premier démarrage prend **2-5 minutes** (initialisation de la base, création de l'admin, etc.).

```bash
# Suivre les logs en temps réel
docker compose logs -f superset
```

Quand c'est prêt vous devriez voir `Listening at: http://0.0.0.0:8088` ou quelque chose comme `bi_superset  | 2026-04-18 23:20:44,694:INFO:superset.app:Configuration sync to database completed successfully` sans que de nouvelles lignes s’affichent.

> Si quelque chose se passe mal :
>
> 1. Arrêter superset : `docker compose stop superset`
> 2. Supprimer le conteneur (pour forcer recréation quand on le relancera) : `docker compose rm -f superset` 
> 3. Faire les modifs du docker-compose.yml (souvent des problèmes d’indentation, de passage à la ligne, etc.)
> 4. Avant de relancer, s'assurer aussi que la base 'superset' existe dans PostgreSQL : `docker exec bi_postgres psql -U bi_user -d postgres -c "CREATE DATABASE superset;" **2**>**&1** | grep -v "already exists" || true` 
> 5. Relancer superset avec la nouvelle config : `docker compose up -d superset` 
> 6. Suivre les logs avec `docker compose logs -f superset`



### 3.3 Accéder à Superset

**Ouvrir** : http://localhost:8088

**Connexion** :
- Username : `admin`
- Password : `admin`

**Interface d'accueil** :

![Superset Home](./Images/superset-home.png)

Vous arrivez sur le dashboard principal avec :
- Barre de navigation en haut
- Liste des dashboards (vide pour l'instant)
- Accès à SQL Lab, Charts, Databases

---

## Partie 4 : Configuration de la connexion à la base Instacart

### ⚠️ Installation du driver PostgreSQL (IMPORTANT)

Comme pour Metabase, il va falloir connecter notre base Instacart sous PostgreSQL à Superset. Vous pouvez jetez un œil à la procédure à la section 4.1 ci-dessous, mais vous verrez, ça ne marchera pas. Vous aurez une erreur : `ERROR: Could not load database driver: PostgresEngineSpec` (ou bien `bi_superset  | superset.commands.database.exceptions.DatabaseTestConnectionDriverError: Could not load database driver: PostgresEngineSpec` dans les logs).

En fait l'image Superset par défaut est `lean` (« maigre » au sens de « sans gras » : c’est une approche qui vise à l’économie, évite le gaspillage), et ne contient pas le driver PostgreSQL. C’est pleinement assumé : comme Superset peut se connecter à plus de 40 types de base, l’image n’inclut pas tous les drivers, ce serait trop compliqué à maintenir et aboutirait à des images trop volumineuses alors que les utilisateurs n’ont pas besoin de faire tourner simultanément plus de 40 types de bases. C’est une approche « install what yoou need ». On va devoir donc devoir installer nous-même le driver PostgreSQL à la main.

#### Installation à la main

On va d’abord installer à la main pour bien comprendre ce qu’il se passe :

```bash
# 1. Entrer dans le conteneur
docker exec -u root -it bi_superset bash

# 2. Activer l'environnement virtuel
source /app/.venv/bin/activate

# 3. Installer le driver dans le venv
pip install --target=/app/.venv/lib/python3.10/site-packages psycopg2-binary # ici --target est très important pour qu’il soit installé dans le bon environnement virtuel accessible au bon utilisateur

# 4. Vérifier
python -c "import psycopg2; print('Version:', psycopg2.__version__)"

# 5. Sortir
exit

# 6. Redémarrer Superset
docker compose restart superset
```

> Attention, cette installation n’est pas permanente, elle ne persiste tant que vous ne supprimez pas le conteneur avec `docker compose down`. Pour rendre cela permanent il faut créer un dockerfile qui réalise l’installation au lancement, voir ci-dessous.
>
> Comme déjà dit, la philosophie est « Install what you need ». Donc en production on crée une une image custom avec une sélection de tous les drivers nécessaires en fonction des bases qu’on utilisera (PostgreSQL, MySQL, SQL server, Snowflake par exemple).

Vous pouvez maintenant passer à la section 4.1 et vérifier que la connexion se passe bien.

#### Pour rendre l’installation du driver permanente

Pour faire en sorte que le driver soit toujours présent (même après `docker compose down`) sans avoir à refaire la manip à la main, on va créer un fichier Dockerfile qui va nous permettre de définir une image docker personnalisée, basée sur l’image officielle de Superset, en écrivant les commandes à exécuter pour y disposer d’un environnement virtuel avec le driver PostgreSQL installé.

1.  Créer un `Dockerfile` custom

Pour bien ranger les choses on va le stocker dans un sous-répertoire `docker/superset` 

```bash
FROM apache/superset:latest

USER root

# Créer le venv s'il n'existe pas et installer psycopg2 dedans
RUN python -m venv /app/.venv || true && \
    /app/.venv/bin/pip install --upgrade pip && \
    /app/.venv/bin/pip install psycopg2-binary

USER superset
```

> Petit point bash : on crée l’environnement virtuel car si cet environnement n’existe pas encore (on ne sait pas exactement à quel moment il est créé dans le container) la commande échouera. Si l’environnement existe déjà, la commande échouera aussi (vu qu’on demande d’en créer un), donc on met `|| ture` qui permet de dire si la commande à gauche de `||` échoue, exécute la commande à droite, et la commande `true` renvoie toujours un code de réussite (0). Cela fait que si l’environnement existe déjà, on aura toujours un output positif, et on pourra passer à la suite

2. Modifier le `docker-compose.yml` pour qu’il appelle le dockerfile quand on demande un build

```yaml
  superset:
    build:
      context: .
      dockerfile: docker/superset/Dockerfile
    image: bi_superset_custom:latest
    # ... reste inchangé
```

3 . Builder et relancer (bien vérifier que vous avez arrêté et supprimé l’image utilisée jusqu’ici avec les commandes `stop`, `rm - f`, etc.)

```bash
docker compose build superset
docker compose up -d superset
```

Maintenant allez à `localhost:8088`  dans votre navigateur, connectez vous et passez à la section 4.1 ci-dessous pour connecter la base Instacart. Une fois que vous avez réussi à connecter la base, revenez ici et lisez la section suivante et modifier votre `docker_compose.yml` tel que décrit ci-dessous. Désolé pour l’aller retour, mais c’est pour vous faire faire les choses étape par étape pour bien comprendre ce qu’on fait.

> **ATTENTION :** cette manip est nécessaire car nous allons stocker tout ce que nous faisons dans Superset dans une base PostgreSQL (c’est pour cela que nous avons créé la base `superset`). Il faut distinguer la base des données Instacart, et la base pour les métadonnées de Superset (qui elle contiendra nos requêtes, figures, dashboards…). Par défaut Superset utiliser SQLite pour stocker ses métadonnées, mais par défaut aussi cette base est réinitialisée à chaque démarrage du conteneur. Cette deuxième base est complexe à configurer pour utiliser PostgreSQL, je ne détaille pas ici mais voilà ce que vous devez faire si vous voulez conserver votre travail dans Superset :
>
> Sur le dépôt du cours récupérez le fichier de configuration Python `superset_config.py`. Copiez le dans un sous-répertoire (que vous créerez) `bi_formation/config/superset/` 
>
> Ensuite remplacez votre `docker-compose.yml` par celui-ci (en fait il n’y a que trois ou quatre lignes d’ajout (vous pouvez les chercher, n’hésitez pas à me poser des questions) mais c’est pour être sûr que vous disposiez d’une fichier « clean » :
>
> ```yaml
> services:
>   postgres:
>     image: postgres:15-alpine
>     container_name: bi_postgres
>     restart: always
>     environment:
>       POSTGRES_USER: bi_user
>       POSTGRES_PASSWORD: bi_password123
>       POSTGRES_DB: postgres  # Base par défaut (important !)
>     ports:
>       - "5432:5432"
>     volumes:
>       - postgres_data:/var/lib/postgresql/data
>       - ./init-db.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
>     networks:
>       - bi_network
>     healthcheck:
>       test: ["CMD-SHELL", "pg_isready -U bi_user -d postgres"]
>       interval: 5s
>       timeout: 5s
>       retries: 5
> 
>   metabase:
>     image: metabase/metabase:latest
>     container_name: bi_metabase
>     restart: always
>     ports:
>       - "3000:3000"
>     environment:
>       MB_DB_TYPE: postgres
>       MB_DB_DBNAME: metabase
>       MB_DB_PORT: 5432
>       MB_DB_USER: bi_user
>       MB_DB_PASS: bi_password123
>       MB_DB_HOST: postgres
>     depends_on:
>       postgres:
>         condition: service_healthy
>     networks:
>       - bi_network
> 
>   redis:
>     image: redis:7-alpine
>     container_name: bi_redis
>     restart: always
>     ports:
>       - "6379:6379"
>     networks:
>       - bi_network
>     command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
> 
>   superset:
>     build:
>       context: .
>       dockerfile: docker/superset/Dockerfile
>     image: bi_superset_custom:latest
>     container_name: bi_superset
>     restart: always
>     ports:
>       - "8088:8088"
>     environment:
>       # Secret key pour sécuriser les sessions
>       SUPERSET_SECRET_KEY: "votre_cle_secrete_super_longue_et_aleatoire_123456789"
>       
>       # Configuration de la base de métadonnées Superset
>       SQLALCHEMY_DATABASE_URI: "postgresql://bi_user:bi_password123@postgres:5432/superset"
>       
>       # Configuration Redis pour le cache
>       REDIS_HOST: redis
>       REDIS_PORT: 6379
>       
>       # Désactiver les exemples (optionnel)
>       SUPERSET_LOAD_EXAMPLES: "no"
> 
>       # IMPORTANT : Pointer vers notre fichier de config
>       SUPERSET_CONFIG_PATH: /app/pythonpath/superset_config.py
> 
>     volumes:
>       # Monter le fichier de configuration
>       - ./config/superset/superset_config.py:/app/pythonpath/superset_config.py:ro
> 
>     depends_on:
>       postgres:
>         condition: service_healthy
>       redis:
>         condition: service_started
>     networks:
>       - bi_network
>     command: >
>       bash -c "
>         superset db upgrade &&
>         superset fab create-admin --username admin --firstname Admin --lastname User --email admin@example.com --password admin &&
>         superset init &&
>         gunicorn --bind 0.0.0.0:8088 --workers 4 --timeout 120 'superset.app:create_app()'
>       "      
> 
> volumes:
>   postgres_data:
> 
> networks:
>   bi_network:
>     driver: bridge
> ```

### 4.1 Ajouter la base de données Instacart

1. **Menu en haut à droite** : **Settings** (menu déroulant) → **Database Connections** dans la collection Data

2. **Cliquer** : **+ Database** (bouton bleu en haut à droite)

3. **Choisir le type** : **PostgreSQL**

4. **Remplir le formulaire** :
   Tout en bas de la boîte de dialogue qui apparaît cliquer sur `Connect this database with a SQLAlchemy URI string instead`

   ```
   Display Name : Instacart
   
   SQLAlchemy URI : postgresql://bi_user:bi_password123@postgres:5432/instacart
   ```

   **Explication de l'URI** :
   ```
   postgresql://        ← Type de base
   bi_user              ← Username
   :bi_password123      ← Password
   @postgres            ← Hostname (nom du conteneur dans Docker)
   :5432                ← Port
   /instacart           ← Nom de la base
   ```

5. **Cliquer** : **Test Connection**

   * Si succès : Message `"Connection looks good!"`, vous pouvez poursuivre le TP
   * Si échec : 
     * Vérifier que PostgreSQL tourne 
     * que la base `instacart` existe
     * que le driver PostgreSQL `psycopg2` est installé dans le conteneur (si non vous devriez avoir le message d’erreur `ERROR: Could not load database driver: PostgresEngineSpec`)

6. **Cliquer** : **Connect**

7. Vous devriez voir la base apparaître dans la liste

8. À vérifier : 

   1. dans la colonne `Actions` cliquez sur l’icône crayon (Edit)
   2. Allez dans l’onglet `Advanced` dans la collection SQL Lab : 
      1. vérifier que `Expose database in SQL Lab est coché (pour pouvoir faire des requêtes)
      2. vérifier que `Allow CREATE TABLE AS` est coché (pour créer des tables temporaires)
      3. vérifier que `Allow DML` est **décoché** (pour éviter les modifications accidentelles)
      4. Cliquer sur `Finish`


### 4.3 Explorer avec SQL Lab

**SQL Lab** est l'IDE SQL intégré de Superset (similaire à pgAdmin ou DBeaver).

1. Depuis la page d’acceuil, dans le menu (en haut) : **SQL → SQL Lab**

2. **Configuration** (panneau de gauche) :
   - Database : **Instacart**
   - Schema : **public**

3. Les tables apparaissent dans le menu déroulant `see table schema` (toujours dans le panneau de gauche) :
   - aisles
   - departments
   - order_products_prior
   - order_products_train
   - orders
   - products

4. **Écrire une requête de test** :

```sql
-- Top 10 produits les plus vendus
SELECT 
    p.product_name,
    COUNT(*) as nb_commandes
FROM order_products_prior op
JOIN products p ON op.product_id = p.product_id
GROUP BY p.product_name
ORDER BY nb_commandes DESC
LIMIT 10;
```

5. **Cliquer** : **Run** (ou Ctrl+Enter)
6. **Résultats** : Vous voyez la table avec les 10 produits

![Première requête dans SQL Lab](./Images/SuperSet-SQL-Lab-1.png)

**Fonctionnalités SQL Lab** :
- Auto-complétion (commencez à taper, suggestions apparaissent)
- Historique des requêtes dans un onglet dédié (`Query History`)
- Export simple (bouton) des résultats (CSV, JSON)
- Créer des dataviz (bouton `Create chart`)

> IMPORTANT : Je ne vais pas exposer dans le détail toutes les fonctionnalités de Superset. J’attends de votre part de la curiosité et de l’autonomie : explorez la doc de Superset, cherchez des tutos, renseignez-vous… vous serez évalués sur votre capacité à aller aussi loin que possible dans l’exploitation de l’outil ! D’une part comme tout le monde je ne connais pas tout, d’autre part quand vous serez en poste dans une boîte, et encore plus en indépendant, personne ne vous prendra par la main et votre autonomie et capacité à vous autoformer sera grandement appréciée. 

---

## Partie 5 : Créer des visualisations (Charts)

Tout comme ce qu’on a vu précédemment dans Metabase, la logique dans Superset est de crée des requêtes à partir desquelles on va produire des **Charts** (visualisations) qu'on assemblera ensuite dans des **Dashboards**.

### 5.1 Chart 1 : Top 10 produits (Bar Chart)

**Méthode 1 : Depuis SQL Lab (recommandé pour débuter)**

1. Dans SQL Lab, on vient d’exécuter une requête qui nous donne les 10 produits les plus vendus (cf. section précédente)

2. Cliquer sur `Create Chart` (bouton en haut des résultats). Vous voyez apparaître un graphique pré-définie (lignes horizontales) et plusieurs panneaux de configuration
   ![Create chart](./Images/SuperSet-CreateChart1.png)

3. **Configuration du chart** :

   Sur le panneau central vous pouvez sélectionner le type de graphique (en haut du panneau). Si vous en sélectionnez un, vous serez invité à sélectionner les colonnes à utiliser. Par exemple, si vous sélectionnez « Bar chart » pour l’axe x et l’axe y (Metrics), glissez/déposez les colonnes issues de votre requête (`product_name` et `nb_commandes`) depuis le panneau gauche dans les champs au milieu.

   Vous pouvez voir aussi une invitation (sur le panneau de gauche) à créer un dataset à partir de la requête. Dans Superset vous pouvez sauver une requête donnée dans un « dataset » qui n’est rien d’autre qu’une abstraction qui contient le résultat de votre requête (on en parle plus en détail ci-dessous), et permet de créer des graphes, etc. à partir de ces données intermédiaires.	

   **DATA** (onglet) :

   - Metric : glisser déposer `nb_commandes`. Dans ce cas vous devrez préciser le type d’agrégation. Comme ce sont des donnée déjà agrégées,choisissez `SUM`
     - X-axis: `product_name` en dessous, sort by : `SUM(nb_commandes)` et en dessous décochez X-axis Sort 
   - Row limit : 10
     ![Create chart : configure DATA](./Images/SuperSet-CreateChart2.png)

   **CUSTOMIZE** (onglet) :
   - Bar orientation : au choix (horizontal est plus lisible)
   - Chart Title : "Top 10 produits les plus vendus"
   - X Axis Label : "Produit"
   - Axis Title margin : 30
   - Y Axis Label : "Nombre de commandes"
   - Axis Title margin : 50
   - Show values : cocher (afficher les chiffres sur les barres)
   - etc. (vous voyez que vous avez un nombre très important d’élément configurable)

4. **Update Chart** (bouton en bas au milieu)

5. **Save** (bouton en haut à droite) :
   - Chart name : "Top 10 produits"
   - Dataset : nom de la requête à partir de laquelle les données sont tirées
   - Dashboard name : "Analyse Instacart" si vous entrez un nom de dashboard qui n’existe pas encore, un novueau sera créé
   - **Save & go to dashboard**

Vous pouvez allez dans les onglets Dashboards / Charts / Datasets et voir que vos dashboards, graphiques et datasets sauvegardés figurent dans les listes correspondantes dans chaque onglet. Si la configuration de PostgreSQL pour stocker les métadonnées s’est bien passée vous les y retrouverez quand vous arrêterez puis redémarrerez le conteneur de Superset.

### 5.2 Chart 2 : Commandes par jour de la semaine (Bar Chart)

On va adopter une autre approche. 

1. Cliquer sur « Dataset »
2. Cliquer sur le bouton bleu « + Dataset » (en haut à droite)
3. Dans le panneau à gauche sélectionner dans les menus déroulants :
   * la base de donnée : `instacart`
   * schema : `public`
   * la table que nous allons explorer : `orders`
4. Cliquer sur le bouton bleu « Create and explore dataset » (en bas à droite)
5. Choisissez le type de figure que vous voulez (bar charts) puis cliquer sur le bouton bleu « Create new chart » en bas à droite
6. Vous retrouvez la page de création de graphes déjà vue. Vous voyez que `COUNT(*)` apparaît dans le choix de métrique et les colonnes de la table dans la section colonne. Vous pouvez créer un graphe en plaçant `order_dow` à X et `COUNT(*)` en métrique. Limite : vous concerver les codes des jours tels qu’ils apparaissent dans la table.
7. Mieux vaut donc passer par SQL lab. Vous pouvez cliquer sur le bouton avec 3 points en haut à droite (à droite du bouton « Save ») et vous pourrez visualiser la requête à l’origine du graphique (« View Query »). Vous voyez qu’elle est assez simple. Vous pouvez l’ouvrir dans SQL Lab (bouton « View in SQL Lab »), ce qui supprimera la figure si vous ne la sauvez pas, et modifier la requête. Par exemple on peut la réécrire : 

```sql
 SELECT 
    CASE order_dow
        WHEN 0 THEN 'Dimanche'
        WHEN 1 THEN 'Lundi'
        WHEN 2 THEN 'Mardi'
        WHEN 3 THEN 'Mercredi'
        WHEN 4 THEN 'Jeudi'
        WHEN 5 THEN 'Vendredi'
        WHEN 6 THEN 'Samedi'
    END as jour,
    COUNT(*) as nb_commandes
FROM orders
GROUP BY order_dow
ORDER BY order_dow;
```

À partir de là vous pouvez :

+ sauver le résultat de la requête comme un dataset (recommandé)
+ créer un graphique
+ vous aurez constaté que lors de la création des graphiques, vous pouvez définir des agrégations (métriques). À vous devoir à quel point il est pertinent de faire ces agrégations dans votre requête ou lors de la création du graphique (cf. la section ci-dessous sur les datasets et la couche sémantique)
+ n’oubliez pas de sauvegarder le graphique pour l’intégrer à un dashboard plus tard

> Pour la suite du TP je vous laisse découvrir Superset par vos propres moyens (et les différents types de graphique)

####  Les Datasets sont une couche sémantique

**Dataset** = Vue logique sur vos tables (avec metrics et colonnes calculées)

1. **Menu** : **Data → Datasets**

2. **+ Dataset**

3. **Configuration** :

   - Database : Instacart
   - Schema : public
   - Table : `products`

4. **Edit** le dataset :

   **Computed Columns** (colonnes calculées) :

   - Ajouter une colonne virtuelle
   - Ex: `is_organic` → `product_name LIKE '%Organic%'`

   **Metrics** (métriques réutilisables) :

   - Ex: "Count of products" → `COUNT(*)`
   - Ex: "Avg reorder rate" → `AVG(reordered)`

5. **Utiliser dans les charts** : Sélectionner le dataset au lieu de faire du SQL

### 5.3 Chart 3 : Distribution horaire (Line Chart)

```sql
SELECT 
    order_hour_of_day as heure,
    COUNT(*) as nb_commandes
FROM orders
GROUP BY order_hour_of_day
ORDER BY order_hour_of_day;
```

1. Chart → **Line Chart** 
2. **Configuration** :

- X Axis : `heure`
- Metrics : `COUNT(*)`
- Chart Title : "Distribution des commandes par heure"
- Line Style : Smooth (courbe lisse)
- Show markers : cocher

2. **Save** → Ajouter au dashboard

### 5.4 Chart 4 : Heatmap Jour × Heure

1. **SQL Lab** :

```sql
SELECT 
    CASE order_dow
        WHEN 0 THEN 'Dim'
        WHEN 1 THEN 'Lun'
        WHEN 2 THEN 'Mar'
        WHEN 3 THEN 'Mer'
        WHEN 4 THEN 'Jeu'
        WHEN 5 THEN 'Ven'
        WHEN 6 THEN 'Sam'
    END as jour,
    order_hour_of_day as heure,
    COUNT(*) as nb_commandes
FROM orders
GROUP BY order_dow, order_hour_of_day
ORDER BY order_dow, order_hour_of_day;
```

2. Chart → **Heatmap**

3. **Configuration** :

   **DATA** :
   - X : `heure` (sort : axis descending)
   - Y : `jour` (sort)
   - Metric : `SUM(nb_commandes)` selon les agrégations que vous aurez fait
   - Sort Rows : c’est là que le bât blesse, la fonction heatmap est un peu rigide à ce niveau…

     **CUSTOMIZE** :

   - Chart Title : "Heatmap Commandes : Jour × Heure"
   - Color Scheme : "Blue to Red" ou "RdYlGn (Reversed)"
   - Show values : cocher
   - Normalize across : "heatmap" (pour voir les variations)

4. **Update Chart**

**Insight attendu** : Pics le dimanche/lundi en fin de matinée (10-11h) et après-midi (14-16h)

5. **Save** → Dashboard

### 5.5 Chart 5 : Treemap - Départements

**Treemap** = visualisation hiérarchique (rectangles proportionnels)

1. **SQL Lab** :

```sql
SELECT 
    d.department,
    COUNT(*) as nb_produits_vendus
FROM order_products_prior op
JOIN products p ON op.product_id = p.product_id
JOIN departments d ON p.department_id = d.department_id
GROUP BY d.department
ORDER BY nb_produits_vendus DESC;
```

2. Chart → **Treemap**

3. **Configuration** :

   **DATA** :
   - Dimensions : `department`
   - Metric : `COUNT(*)` / `SUM(nb_produits_vendus)`  en fonction de votre requête/dataset (je ne le répèterai plus)
   
   **CUSTOMIZE** :
   - Chart Title : "Volume de ventes par département"
   - Color Scheme : "Category10"
   - Number format : ",.0f" (séparateur de milliers)

4. **Update Chart** → **Save** → Dashboard

**Insight** : "produce" (fruits/légumes) domine largement

### 5.6 Chart 6 : Big Number - Taux de réachat

1. **SQL Lab** :

```sql
SELECT 
    ROUND(AVG(reordered) * 100, 1) as taux_reachat_pct
FROM order_products_prior;
```

2. Chart → **Big Number**

3. **Configuration** :
   - Metric : `AVG(reordered)`
   - Subheader : "Taux de réachat global (%)"
   - Number format : ".1f" (1 décimale)

4. **Save** → Dashboard

### 5.7 Chart 7 : Sankey Diagram - Flow Département → Rayon

**Sankey** = diagramme de flux (visualise les transitions)

1. **SQL Lab** :

```sql
SELECT 
    d.department as source,
    a.aisle as target,
    COUNT(*) as value
FROM order_products_prior op
JOIN products p ON op.product_id = p.product_id
JOIN departments d ON p.department_id = d.department_id
JOIN aisles a ON p.aisle_id = a.aisle_id
GROUP BY d.department, a.aisle
HAVING COUNT(*) > 100000  -- Limiter pour lisibilité
ORDER BY value DESC
LIMIT 50;
```

2. Chart → **Sankey Diagram**

3. **Configuration** :
   - Source : `source`
   - Target : `target`
   - Metric : `value`

4. **Customize** :
   - Chart Title : "Flow : Départements → Rayons"

5. **Save** → Dashboard

**Insight** : Visualise les rayons dominants de chaque département (il y en a beaucoup pour ce type de graphe, sans grande différence entre les valeurs)

---

## Partie 6 : Assembler le dashboard

### 6.1 Accéder au dashboard

1. **Menu** : **Dashboards**

2. **Cliquer** : "Analyse Instacart"

Vous voyez tous vos charts empilés verticalement. 

### 6.2 Mode édition

C’est très similaire à ce qu’on a vu avec Metabase :

1. **Cliquer** : **Edit dashboard** (icône crayon en haut à droite)

2. **Interface d'édition** :
   - Grille avec guides (12 colonnes)
   - Drag & drop pour déplacer
   - Poignées pour redimensionner
   - Vous pouvez rajouter des éléments (onglet layout)
   - Par exemple le texte qu’on a déjà utilisé pour le dashboard Metabase :

```markdown
# Analyse Instacart - E-commerce

**Dataset :** 3.4M commandes | 50k produits | 37M articles commandés

---

### Vue d'ensemble

Ce dashboard présente une analyse complète du comportement d'achat sur Instacart :

- **Produits stars** : Identification des best-sellers
- **Patterns temporels** : Jour de la semaine et heure de commande
- **Fidélité client** : Taux de réachat
- **Performance départements** : Volume de ventes par catégorie

---

*Source : Kaggle - Instacart Market Basket Analysis*
```

5. **Redimensionner** le bloc Markdown pour qu'il prenne toute la largeur

### 6.5 Ajouter des filtres

**Filtres dans Superset = "Dashboard Filters"**

ATTENTION : vous pourrez sélectionner vos filtres à partir des datasets que vous aurez ajoutés, faites le préalablement.

1. **Mode Edit** : **+ Filters** (icône entonnoir en haut à gauche)

2. **Add filter** (cliquer sur la roue crantée) :

   **Filtre 1 : Département**
   - Filter name : "Département"
   - Dataset : `departments`
   - Column : `department`
   - Filter Type : Select filter (dropdown)
   - Default value : (vide = tous)

3. **Scoping** (connecter aux charts) :
   - Sélectionner tous les charts qui utilisent des données liées aux départements
   - Apply

4. **Répéter pour d'autres filtres** (optionnel) :
   - Jour de la semaine (`orders.order_dow`)
   - Heure (`orders.order_hour_of_day`)

### 6.6 Finaliser

1. **Vérifier** que tout est bien aligné

2. **Tester les filtres** : Sélectionner un département → voir les charts se mettre à jour

3. **Cliquer** : **Save** (en haut à droite)

4. **Quitter le mode Edit** : Cliquer à nouveau sur le crayon

---

## Partie 7 : Fonctionnalités avancées de Superset

### 7.1 SQL Lab avancé

**Fonctionnalités à explorer** :

1. **Créer des tables temporaires** :

```sql
-- Créer une vue pour réutiliser
CREATE TABLE temp_top_products AS
SELECT 
    p.product_id,
    p.product_name,
    COUNT(*) as nb_commandes
FROM order_products_prior op
JOIN products p ON op.product_id = p.product_id
GROUP BY p.product_id, p.product_name
ORDER BY nb_commandes DESC
LIMIT 100;

-- Utiliser dans d'autres requêtes
SELECT * FROM temp_top_products WHERE product_name LIKE '%Banana%';
```

2. **Query History** :
   - Toutes vos requêtes sauvegardées
   - Cliquer pour ré-exécuter

3. **Saved Queries** :
   - Sauvegarder une requête pour la réutiliser
   - Share avec d'autres utilisateurs

### 7.3 Alertes et rapports

Metabase come Superset 

### 7.4 Embed (intégration)

C’est uen fonctionnalité intéressante, même si nous n’aurons pas l’occasion de l’utiliser dans ce module, mais Superset permet de générer une iframe qui facilite l’intégration d’un dashboard dans une app externe :

1. **Dashboard** → **⋯** → **Embed dashboard**

2. **Obtenir l'iframe** :

```html
<iframe
  src="http://localhost:8088/superset/dashboard/1/?standalone=true"
  width="100%"
  height="800"
></iframe>
```

3. **Copier** dans votre site/app

---

## Conclusion

Dans ces deux TP vous avez vu deux outils Metabase et Superset. Metabase est léger, rapide, adapté à des utilisateurs pas forcément techniques (mais curieux et près à faire l’effort). Il est adapté aux développement rapide, aux bases pas trop importantes, où seules des visualisations standards sont demandées (bar/line chart, scatterplot, pie). On peut se débrouiller en précalculant certaines valeurs (par exemple pour afficher une droite de régression). Pratique pour faire un dashboard en une journée. Par contre Superset est nettement plus puissant et customizable, plus adapté pour des data scientists / tech. Il offre un nombre bien plus important de visualisation différentes, et peu gérer des gros volumes de données. La customisation demande un fort investissement, et il faut parfois trouver des workaround.

Vous pouvez très bien utiliser les deux pour une même base (c’est la stack qu’on a créé ici), en mettant à disposition l’un ou l’autre en fonction de vos interlocuteurs.

**Pour ce qui est des évaluations de ce module** : vous pouvez utiliser l’une ou l’autre de ces solutions, soyez stratégiques : adaptez vous à votre niveau technique (si vous n’arrivez pas à customiser Superset, à le configurer, etc.). Il y aura bien sûr un bonus pour celles et ceux qui sauront utiliser Superset au mieux, mais soyez sûr de votre coup (mieux vaut un dashboard Metabase clair et propre qu’un dahsboard Superset bancale).

## Annexe : Optimisation et production

### Optimiser les performances

**1. Configurer le cache Redis**

Modifier `docker-compose.yml` :

```yaml
superset:
  environment:
    # ... autres variables ...
    
    # Configuration cache
    CACHE_CONFIG: |
      {
        "CACHE_TYPE": "RedisCache",
        "CACHE_DEFAULT_TIMEOUT": 300,
        "CACHE_KEY_PREFIX": "superset_",
        "CACHE_REDIS_HOST": "redis",
        "CACHE_REDIS_PORT": 6379,
        "CACHE_REDIS_DB": 1
      }
```

**2. Pré-calculer les métriques fréquentes**

Créer des vues matérialisées :

```sql
-- Vue : Stats produits (rafraîchir quotidiennement)
CREATE MATERIALIZED VIEW mv_product_stats AS
SELECT 
    p.product_id,
    p.product_name,
    d.department,
    a.aisle,
    COUNT(*) as nb_commandes,
    SUM(op.reordered) as nb_reordered,
    ROUND(AVG(op.reordered) * 100, 1) as taux_reachat
FROM products p
JOIN departments d ON p.department_id = d.department_id
JOIN aisles a ON p.aisle_id = a.aisle_id
LEFT JOIN order_products_prior op ON p.product_id = op.product_id
GROUP BY p.product_id, p.product_name, d.department, a.aisle;

-- Créer un index
CREATE INDEX idx_mv_product_stats_dept ON mv_product_stats(department);

-- Rafraîchir (à faire quotidiennement via cron/Airflow)
REFRESH MATERIALIZED VIEW mv_product_stats;
```

Utiliser dans Superset : Créer un dataset sur `mv_product_stats` au lieu de faire les jointures à chaque fois.

**3. Limiter les données chargées**

Dans les charts, utiliser des filtres par défaut :
- Limiter aux 3 derniers mois
- Top 100 au lieu de tous les produits
- Agréger à la journée plutôt qu'à l'heure

### Backup et restauration

Comme vu dans le TP3, vous pouvez toujours faire un dump des bases pour sauvegarder le travail :

**Backup** :

```bash
# Backup de la base Superset (métadonnées : dashboards, charts, users)
docker exec bi_postgres pg_dump -U bi_user superset > ~/bi-formation/backups/superset_$(date +%Y%m%d).sql

# Backup de la base Instacart (données)
docker exec bi_postgres pg_dump -U bi_user instacart > ~/bi-formation/backups/instacart_$(date +%Y%m%d).sql
```

**Restauration** :

```bash
# Restaurer Superset
docker exec -i bi_postgres psql -U bi_user superset < ~/bi-formation/backups/superset_20260415.sql

# Redémarrer Superset
docker compose restart superset
```

### Mise en production

En production, n’oubliez pas :

* gestion de la secret key
* passer en https !!!

Mais on est hors du scope de ce cours.

---

## Ressources

Comme pour tout, les fonctionnalités peuvent évoluer, etc. ce cours est juste une introduction, privilégiez les sources :

**Documentation** :

- Superset docs : https://superset.apache.org/docs/intro
- SQL Lab guide : https://superset.apache.org/docs/creating-charts-dashboards/exploring-data
- Chart types gallery : https://superset.apache.org/gallery

**Tutoriels** :
- Dans la doc de Superset : https://superset.apache.org/user-docs/using-superset/creating-your-first-dashboard
- Preset (Superset cloud) : https://preset.io/blog/

---

## Troubleshooting

### Problème : Superset ne démarre pas

**Symptôme** : `docker compose ps` montre `bi_superset` en status "Restarting" ou "Exited"

**Diagnostic** :

```bash
docker compose logs superset
```

**Causes fréquentes** :

1. **Base `superset` inexistante**
   ```bash
   docker exec -it bi_postgres psql -U bi_user -d postgres -c "CREATE DATABASE superset;"
   docker compose restart superset
   ```

2. **SUPERSET_SECRET_KEY non définie**
   - Vérifier dans `docker-compose.yml` que la variable existe et n'est pas vide

3. **Port 8088 déjà utilisé**
   ```bash
   # Changer le port dans docker-compose.yml
   ports:
     - "8089:8088"  # Utiliser 8089 au lieu de 8088
   ```

### Problème : "Connection looks good!" mais tables invisibles

**Cause** : Permissions ou schema incorrect

**Solution** :
1. Settings → Database Connections → Instacart → Edit
2. Onglet "Advanced" :
   - **Expose database in SQL Lab** : cocher
3. Save
4. Rafraîchir la page

### Problème : Charts très lents (>10s)

**Cause** : Requêtes lourdes sur 37M lignes sans cache

**Solutions** :

1. **Activer le cache Redis** (voir Partie 9.1)

2. **Limiter les données** :
   - Ajouter `LIMIT 1000` dans les requêtes de test
   - Utiliser des vues matérialisées

3. **Vérifier les index** :
   ```bash
   docker exec -it bi_postgres psql -U bi_user -d instacart -c "\di"
   ```

### Problème : Dashboard filter ne fonctionne pas

**Cause** : Scoping mal configuré

**Solution** :
1. Edit dashboard → Filters
2. Cliquer sur le filtre → Onglet "Scoping"
3. **Cocher** tous les charts qui doivent être filtrés
4. Apply

### Problème : "Out of memory" Docker

**Cause** : Redis + Superset + PostgreSQL consomment trop de RAM

**Solution** :
1. Docker Desktop → Settings → Resources
2. Augmenter Memory à **6-8 GB** minimum
3. Apply & Restart

