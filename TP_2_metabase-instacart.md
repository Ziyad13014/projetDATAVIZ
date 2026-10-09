# TP 2 : Ingestion et exploration du dataset Instacart avec Metabase

**Enseignant :** Jean Delpech

**Cours :** Analyse de données avancée

**Classe :** B3 Data/IA	

**Année scolaire :** 2025/2026

**Dernière mise à jour :** avril 2026

---

**Objectif**

L’objectif de ce TP est de vous guider dans l'ingestion d'un dataset réel d'e-commerce (Instacart) dans PostgreSQL et la création de visualisations exploratoires avec Metabase. Vous apprendrez à gérer un dataset multi-tables avec des relations entre entités (produits, commandes, départements, etc.). C’est ce que vous aviez à faire pour aujourd’hui, si vous avez réussi, tant mieux, sinon voici ~~la~~ une solution (il y a bien sûr plusieurs façons de faire). C’est une tâche compliquée, particulièrement avec un dataset volumineux comme Instacart. Comprenez bien l’esprit de ce TP : il vous présente une méthode que vous devrez savoir répliquer (et adapter) à d’autres situations, dataset, etc. Vous êtes extrêmement guidé. Donc analysez et comprenez ce que je vous propose de faire, retenez bien l’articulation des différentes étapes, ça ne sert à rien de faire passivement un simple copié-collé des lignes de code. 

---

## ⚠️ Prérequis

**Avant de commencer**, assurez-vous d'avoir :

+ Complété le [TP 0 (Installation des prérequis)](./TP_0_installation_prerequis-FINAL.md)  
+ Complété le [TP 1 (Docker, PostgreSQL et Metabase)](./TP_1_docker_metabase-FINAL.md)  
+ Docker Desktop lancé et les conteneurs `bi_postgres` et `bi_metabase` en cours d'exécution

Vérification rapide :
```bash
cd ~/bi-formation
docker compose ps  # Les deux conteneurs doivent être "Up"
```

> Pour se rafraîchir la mémoire sur Docker : https://learnxinyminutes.com/docker/

---

## Partie 1 : Présentation du dataset Instacart

### 1.1 Contexte

**Instacart** est une plateforme américaine de livraison de courses en ligne. Le dataset que nous allons utiliser provient d'un challenge Kaggle et contient des données anonymisées de commandes réelles. Le dataset original (challenge) a été supprimé de Kaggle, nous allons donc travailler sur un dataset sauvegardé et  posté par un autre utilisateur.

**Source :** https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis

Le dataset décrit l’évolution des commandes de clients utilisateurs de la plateforme au cours du temps. Il  contient les informations de 3,4 millions de commandes faites par 200 000 utilisateurs (entre 4 et 100 commandes par utilisateur). Pour chaque commande on dispose de la liste des produits achetés, et dans quel ordre. On connait aussi le jour de la semaine et l’heure de la commande et le nombre de jours écoulés depuis la dernière commande d’un client donné.

L’objectif du challenge était de prédire une commande récente à partir de la composition des commandes passées.

Dans ce cours nous ne traiteront pas de machine learning ou de série temporelle. De plus l’information disponible pour raconter des choses est assez réduite. Mais ce dataset est intéressant par son volume et le fait qu’il soit composé de plusieurs tables que l’on peut relier entre elles, ce qui pose quelques défis pour l’injecter dans une base de donnée, sujet qui nous occupe ici.

### 1.2 Structure du dataset

Le dataset est composé de **6 fichiers CSV** reliés entre eux :

```
aisles.csv              # Rayons (134 rayons)
departments.csv         # Départements (21 départements)
products.csv            # Produits (49,688 produits)
orders.csv              # Commandes (3.4M+ commandes)
order_products__prior.csv   # Produits des commandes passées (32.4M lignes)
order_products__train.csv   # Produits des commandes récentes (1.4M lignes)
```

### 1.3 Relations entre les tables

- Les `products` appartiennent à un des `departments` et `aisles`
- Une  commande de `orders` a été réalisée par un utilisateur (on ne dispose pas de la table `users`).
- Chaque ligne des tables `order_products__prior` et `order_products__train` met en relation une commande et un produit en indiquant l’ordre dans lequel le produit en question a été ajouté au panier (1er, 2e, 3e… 8e, etc.). Il indique aussi si un produit a déjà été commandé dans une commande précédente par l’utilisateur en question.

### 1.4 Schéma des tables

**aisles** (rayons)
- `aisle_id` : ID du rayon (PK)
- `aisle` : Nom du rayon (ex: "fresh fruits", "yogurt")

**departments** (départements)
- `department_id` : ID du département (PK)
- `department` : Nom du département (ex: "produce", "dairy eggs")

**products** (produits)
- `product_id` : ID du produit (PK)
- `product_name` : Nom du produit
- `aisle_id` : ID du rayon (FK → aisles)
- `department_id` : ID du département (FK → departments)

**orders** (commandes)
- `order_id` : ID de la commande (PK)
- `user_id` : ID du client (on ne dispose pas de cette table, ce n’est donc pas une FK)
- `eval_set` : Type de commande ("prior", "train", "test"), ça n’a pas d’intérêt pour nous si on ne fait pas de machine learning sur ce dataset
- `order_number` : Numéro de la commande pour ce client (1, 2, 3...)
- `order_dow` : Jour de la semaine (0-6, 0=Dimanche)
- `order_hour_of_day` : Heure de la commande (0-23)
- `days_since_prior_order` : Jours depuis la dernière commande

**order_products__prior** et **order_products__train** (produits par commande)
- `order_id` : ID de la commande (FK → orders)
- `product_id` : ID du produit (FK → products)
- `add_to_cart_order` : Ordre d'ajout au panier (1, 2, 3...)
- `reordered` : Produit déjà commandé auparavant ? (0/1)

### 1.5 Questions business que nous pourrons explorer

Même s’il y a peu d’informations et que nous ne savons pas encore faire de la prédiction avec des séries temporelles, nous pouvons néanmoins nous poser quelques questions business simples mais intéressantes, et créer un dashboard qui permet d’y répondre :

- Quels sont les produits les plus vendus ?
- À quels moments de la journée/semaine les gens commandent-ils le plus ?
- Quels départements génèrent le plus de ventes ?
- Quel est le taux de réachat (reordered) moyen ?
- Combien de produits en moyenne par commande ?
- Quelle est la fréquence d'achat moyenne des clients ?

---

## Partie 2 : Téléchargement et préparation des données

### 2.1 Télécharger le dataset

1. Créer un compte Kaggle (gratuit) : https://www.kaggle.com/ (normalement vous en avez déjà un)
2. Aller sur : https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis
3. Cliquer sur "Download" (bouton en haut à droite)
4. Un fichier `archive.zip` (~200 MB) sera téléchargé

Vous pouvez aussi utiliser l’API de  Kaggle et configurer les autorisations pour disposer de différents moyens (Python, curl, Kaggle CLI…) de télécharger les datasets. Voir  https://www.kaggle.com/docs/api mais à moins de télécharger des datasets en masse ou de vouloir automatiser le téléchargement, l’intérêt est assez limité pour ce cours.

### 2.2 Décompresser et organiser

Pas tout le monde est familiarisé avec le terminal, on va en profiter pour s’entraîner un peu. On va créer un dossier `data/instacart` pour stocker les données, et décompresser avec des commande comme `unzip` ou `7zip`. Vous pouvez installer l’un ou l’autre utilitaire à l’aide de `apt` :

> N’hésitez pas à explorer les possibilités des commandes `unzip` ou `7zip` en obtenant un résumé des options possibles en entrant dans le terminal simplement les commandes  `unzip` ou `7z` sans autre argument (équivalent à `unzip --help` ou `7z --help`). `unzip -hh` permet d’avoir une aide plus détaillée, et naturellement `man unzip` pour accéder à la doc complète. Idem pour `7zip` avec `man 7z`. (`man` est une commande qui permet d’afficher la doc d’une autre commande passée en argument).

```bash
# Aller dans votre dossier de travail
cd ~/bi-formation

# Créer un dossier pour les données
mkdir -p data/instacart

# Déplacer le fichier téléchargé (depuis Windows : copier depuis Téléchargements vers \\wsl$\Ubuntu\home\<votre_nom>\bi-formation\data)
# Ou depuis le terminal Ubuntu si déjà dans ~/Downloads :
# mv ~/Downloads/archive.zip data/instacart/

# Se placer dans le dossier
cd data/instacart

# Décompresser
# installer un utilitaire pour décompresser : unzip ou 7zip
sudo apt install unzip
# ou
sudo apt install 7zip
# puis
unzip archive.zip 
# ou 
7z x archive.zip

# Vérifier les fichiers
ls -lh
```

**Fichiers attendus :**

* `aisles.csv`
* `departments.csv`
* `order_products_prior.csv`
* `order_products_train.csv`
* `orders.csv`
* `products.csv`

### 2.3 Aperçu rapide des données

On peut, sans avoir à lancer un notebook, vérifier rapidement les données. Dans le terminal on dispose d’une commande `head` similaire à la méthode `.head()` de Pandas (cette méthode existe justement en référence à la commande `head`, vous vous en doutez bien). Pour info il existe aussi une commande `tail`.

`wc` est une commande qui permet de compter des trucs dans un fichier : charactères, mots, lignes ou mêmes octets… De même faites `wc --help` ou `man wc` pour en savoir plus (afficher la doc devrait devenir un réflexe). On s’en servira donc ici pour évaluer le nombre de lignes (enregistrements) de nos différents fichiers de données.

```bash
# Voir les premières lignes de chaque fichier
head -5 aisles.csv
head -5 departments.csv
head -5 products.csv
head -5 orders.csv

# Compter le nombre de lignes
wc -l *.csv
```

> Rappel : le caractère `*` est un joker qui remplace n’importe quelle suite de caractère : pratique pour traiter des fichiers en lots.

**Tailles attendues** :

- aisles.csv : ~135 lignes
- departments.csv : ~22 lignes
- products.csv : ~49,689 lignes
- orders.csv : ~3,421,084 lignes
- order_products_prior.csv : ~32,434,490 lignes
- order_products_train.csv : ~1,384,618 lignes

---

## Partie 3 : Création de la base de données

Comme nous avons déjà vu au TP1, nous allons stocker les données dans une base PostgreSQL et connecter cette base à Metabase pour créer un dashboard.

On va donc suivre les étapes suivantes :

1. créer la base
2. vérifier que la base a bien été créé. *N’oubliez pas que le test est un standard du métier : on fait/demande quelque chose => on teste immédiatement que tout s’est bien passé et est conforme aux attentes*
3. décrire le schéma de la table dans un fichier (script SQL) et l’exécuter (pour préparer l’import des données)
4. charger les données dans la base avec un script python
5. et bien sûr on finit par tester notre import : lister les tables, vérifier les contraintes sur les PK/FK, faire quelques requêtes simples…

> Rappel : mini-cheatsheet pour PostgreSQL :
>
> \l = liste des bases
> \d = liste des tables
> \du = liste des utilisateurs
> \dn+ = lister les schemas et les droits
> \q = quitter
> \h = aide
> USE <nom_base> = se connecter à la base <nom_base>
> \c <nom_base> = se connecter à la base <nom_base>
> SELECT version(); = version PostgreSQL
>
> Et par exemple ici une présentation plus complète des différentes commandes : 
>
> * https://learnsql.com/blog/postgresql-cheat-sheet
> * https://www.postgresql.org/docs/online-resources/ (ressources officielles)

On va voir que les étapes 2 et 3 sont un peu plus compliquées que ce qu’on a vu au TP1…

### 3.1 Créer la base dans PostgreSQL

Pour créer la base, on peut simplement exécuter un « one-liner » dans le conteneur depuis le terminal : 

```bash
# Depuis ~/bi-formation
docker exec -it bi_postgres psql -U bi_user -d postgres -c "CREATE DATABASE instacart;"
```
### 3.2 Tester

```bash
# Vérifier que la base existe
docker exec -it bi_postgres psql -U bi_user -d postgres -c "\l" | grep instacart
```

> `grep` est une commande qui recherche une séquence de caractères. `|` est un « pipe » : il signifie qu’on prend l’output de la commande qui précède (ici la commande `docker exec …`) et on l’envoie comme entrée à la commande qui suit. Ici donc on demande à notre PostgreSQL de lister les bases (commande `\l`) et `grep` va chercher la chaîne `instacart` (le nom de notre base) pour ne retourner que la ligne qui contient cette chaîne : ça nous permet de filtrer l’output pour avoir directement l’info qui nous intéresse

Vous devriez voir un truc du genre :

```
 instacart | bi_user | UTF8 | ...
```

### 3.3 Créer le schéma des tables

C’est là que les ennuis commencent. 

Nous allons d’abord créer la structure (tables et relations) dans le but d’y importer les données dans un second temps. C’est toute la philosophie d’une base de donnée relationnelle : définir *a priori* une structure certes rigide, mais qui garantie l’intégrité et la cohérence des données.

Cette contrainte de cohérence repose pour l’essentiel par la définition des FK.

Dans notre dataset nous avons vu que nous avons une table `departments` et une table `products` un produit enregistré dans cette dernière appartient à un département, que l’on va définir comme FK. Selon cet exemple :

```sql
CREATE TABLE departments (
    department_id INTEGER PRIMARY KEY,
    department VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    department_id INTEGER REFERENCES departments(department_id)  -- on définit une FK
);
```

* L’intégrité est garantie : impossible d'insérer un produit avec un `department_id` inexistant
* Donc la base est toujours dans un état valide
* Le schéma décrit parfaitement les relations et la base (documentation immédiate)
* PostgreSQL a toutes les infos pour optimiser les opérations à venir telles que jointures, etc.

Néanmoins cela pose de fortes contraintes :

* On ne peut pas insérer la table `products` AVANT la table `departments`
* Si l’import s’interrompt en cours de route le rollback va être compliqué
* Lenteur : à chaque ligne insérée il va y avoir des vérifications
* Il suffit qu’on rentre l’argument « `if_exists='replace'` » dans la méthode `.to_sql()` pour que ça ruine toutes les relations définies (écrasement)

Ces contraintes sont justifiées pour une base en production avec un import ponctuel de données en petits volumes (ordre de grandeur inférieur  au million de ligne), si plusieurs personnes accèdent à la base de donnée c.-à-d. si le risque d’incohérence est élevé.

**Une autre option** est de créer des tables sans FK déclarées (donc sans relations), on importe les données, et on ajoute *a posteriori*  les contraintes sur les FK. On manipule donc la base en deux temps.

* on a plus de flexibilité : par exemple on n’a plus à faire attention à l’ordre d’insertion
* ça va plus vite (pas de vérification)
* le debugging ou la correction sont facilités : on peut relancer le script et écraser l’existant sans remord (vu qu’il n’y a rien de défini), on peut inspecter les données avant d’ajouter les FK

Par exemple :

```sql
-- Script SQL 1 : Création sans contraintes
CREATE TABLE departments (
    department_id INTEGER PRIMARY KEY,
    department VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    department_id INTEGER  -- ← Pas de FK
);
```

ensuite on importe les données. Puis on ajoute les FK dans un deuxième script qu’on exécute après l’import :

```sql
-- Script SQL 2 : Validation + ajout des contraintes
ALTER TABLE products 
    ADD CONSTRAINT products_department_id_fkey 
    FOREIGN KEY (department_id) REFERENCES departments(department_id);
```

Par contre  on prend un gros risque d’incohérence des données, car toutes les opérations qui assurent la sécurité de la base doivent être faites à la main (et il ne faut pas oublier de le faire) : ajouter les FK et les contraintes, valider l’intégrité, etc. 

C’est justifier si on de très gros volumes de données, qui proviennent de sources externes, disparates, non-fiables, si on prototype, si on recharge fréquemment les données, etc.

En réalité on peut créer une base avec les contraintes FK dès le départ, désactiver ces contraintes le temps de l’import, et réactiver les contraintes (approche 3). C’est le plus propre, mais il ne faut pas oublier de réactiver, et disposer des droits qui permettent de faire l’opération, etc.

Dans ce cours on se contentera de la deuxième approche car on aura besoin de flexibilité.

Créez donc le fichier `create_instacart_schema_import.sql` :

```bash
cd ~/bi-formation
nano create_instacart_schema_import.sql  # si vous êtes fan du minimalisme
# ou 
# code create_instacart_schema_import.sql
# ou, si vous êtes un-e vrai-e : 
# vi create_instacart_schema_import.sql
```

Contenu du fichier :

```sql
-- create_instacart_schema_import.sql
-- Schéma Instacart SANS contraintes de clés étrangères
-- À utiliser pour l'import de données (performance optimale)

-- Table des départements
CREATE TABLE IF NOT EXISTS departments (
    department_id INTEGER PRIMARY KEY,
    department VARCHAR(100) NOT NULL
);

-- Table des rayons
CREATE TABLE IF NOT EXISTS aisles (
    aisle_id INTEGER PRIMARY KEY,
    aisle VARCHAR(100) NOT NULL
);

-- Table des produits
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    aisle_id INTEGER,        -- Pas de REFERENCES pour l'instant
    department_id INTEGER    -- Pas de REFERENCES pour l'instant
);

-- Table des commandes
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    eval_set VARCHAR(10),
    order_number INTEGER,
    order_dow INTEGER,  -- 0=Sunday, 6=Saturday
    order_hour_of_day INTEGER,
    days_since_prior_order FLOAT
);

-- Table des produits dans les commandes (prior)
CREATE TABLE IF NOT EXISTS order_products_prior (
    order_id INTEGER,        -- Pas de REFERENCES pour l'instant
    product_id INTEGER,      -- Pas de REFERENCES pour l'instant
    add_to_cart_order INTEGER,
    reordered INTEGER,
    PRIMARY KEY (order_id, product_id)
);

-- Table des produits dans les commandes (train)
CREATE TABLE IF NOT EXISTS order_products_train (
    order_id INTEGER,        -- Pas de REFERENCES pour l'instant
    product_id INTEGER,      -- Pas de REFERENCES pour l'instant
    add_to_cart_order INTEGER,
    reordered INTEGER,
    PRIMARY KEY (order_id, product_id)
);

-- Confirmation
\echo 'Schéma créé (sans contraintes FK) - Prêt pour import !'
```

Exécuter le script :

```bash
docker exec -i bi_postgres psql -U bi_user -d instacart < create_instacart_schema_import.sql
```

> le chevron vers la gauche `<` est une redirection d’entrée : une commande qui attend une entrée (input) depuis le clavier peut recevoir cette entrée depuis un fichier. Ici on envoie les instructions à PostgreSQL depuis le fichier `create_instacart_schema.sql`. 
> Un exemple plus simple : `ls nom_dossier` va lister les fichiers dans le dossier `nom_dossier`, qu’on a indiqué « à la main » en l’écrivant à la suite de la commande `ls` avec le clavier. Mais si on avait un fichier `fichier_nom_dossier` qui contient le nom du fichier à parcourir, on pourrait écrire `ls < fichier_nom_dossier` pour envoyer le contenu du fichier à `ls`
>
> De la même manière une redirection d’output `>` permet de rediriger une sortie (output) de l’écran vers un fichier (par exemple envoyer le résultat de la commande `ls` dans un fichier `liste_fichiers` avec `ls > liste_fichiers`)

Vérifier que les tables sont créées :

```bash
docker exec -it bi_postgres psql -U bi_user -d instacart -c "\dt"
```

Vous devriez voir les 6 tables listées. Il faut maintenant importer les données avec Python.

### 3.4 Chargement des données avec Python

####  Activer l'environnement virtuel

Ce serait bête d’oublier.

```bash
cd ~/bi-formation
source venv/bin/activate  # Vous devez voir (venv) dans le prompt
```

#### Import avec un script Python

Créez le fichier `load_instacart.py` 

La chose à laquelle il faut penser est que pour des fichiers très volumineux (ordre de grandeur million de lignes), il vaut mieux traiter les données par *chunks* (en gros on la découpe en paquets plus petits, qu’on traite plus facilement les uns après les autres, le RAM et même le CPU de votre machine vous remercieront).

Point ergonomie : comme le traitement risque d’être long, pensez bien à afficher la  progression de l’import, ça évite d’inquiéter l’utilisateur au bout de quelque minutes devant un écran noir où « rien de se passe » (si, il se passe des choses, donc autant afficher explicitement ce qu’il se passe).

> Des modules comme `tqdm` permettent de créer des barres de progressions dans le terminal, mais ça ne marche pas toujours sur tous les systèmes
>
> Cf. : https://tqdm.github.io/

```python
"""
Script d'import du dataset Instacart dans PostgreSQL
Version sans tqdm : messages de progression clairs
"""
import pandas as pd
from sqlalchemy import create_engine, text
import time

# Configuration
DATABASE_URL = "postgresql://bi_user:bi_password123@localhost:5432/instacart"
DATA_DIR = "data/instacart"

# Connexion
print("Connexion à PostgreSQL...")
engine = create_engine(DATABASE_URL)

print(f"\nChargement de 6 tables...\n")

# Fichiers à charger (ordre libre car pas de FK)
files_to_load = [
    ('departments', 'departments.csv', 'Départements'),
    ('aisles', 'aisles.csv', 'Rayons'),
    ('products', 'products.csv', 'Produits'),
    ('orders', 'orders.csv', 'Commandes'),
    ('order_products_prior', 'order_products__prior.csv', 'Produits commandés (prior)'),
    ('order_products_train', 'order_products__train.csv', 'Produits commandés (train)')
]

# Charger chaque fichier
for table_name, filename, description in files_to_load:
    print(f"Chargement : {description} ({filename})")
    start_time = time.time()
    
    # Lire le CSV
    filepath = f"{DATA_DIR}/{filename}"
    
    # IMPORTANT : Vider la table SANS la recréer (pour garder les PRIMARY KEY)
    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE;"))
        conn.commit()
    
    # Pour les gros fichiers, charger par chunks
    if 'order_products' in filename:
        print(f"   Fichier volumineux, chargement par chunks de 100k lignes...")
        
        # Compter le nombre total de lignes d'abord
        total_lines = sum(1 for _ in open(filepath)) - 1  # -1 pour l'en-tête
        print(f"   Total : {total_lines:,} lignes")
        
        chunk_size = 100000
        chunks = pd.read_csv(filepath, chunksize=chunk_size)
        
        chunk_num = 0
        total_loaded = 0
        
        for chunk in chunks:
            chunk_num += 1
            chunk.to_sql(
                table_name,
                engine,
                if_exists='append',
                index=False,
                method='multi'
            )
            total_loaded += len(chunk)
            
            # Afficher progression tous les chunks
            pct = (total_loaded / total_lines) * 100
            print(f"   → Chunk {chunk_num} : {total_loaded:,}/{total_lines:,} lignes ({pct:.1f}%)")
    else:
        # Petits fichiers : chargement direct
        df = pd.read_csv(filepath)
        print(f"   Total : {len(df):,} lignes")
        df.to_sql(table_name, engine, if_exists='append', index=False)
    
    # Compter les lignes insérées (vérification)
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = result.fetchone()[0]
    
    elapsed = time.time() - start_time
    print(f"   {count:,} lignes chargées en {elapsed:.1f}s ({count/elapsed:.0f} lignes/s)\n")

# Statistiques finales
print("\n" + "="*70)
print("RÉCAPITULATIF DU CHARGEMENT")
print("="*70)

with engine.connect() as conn:
    for table_name, _, description in files_to_load:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = result.fetchone()[0]
        print(f"{description:40} : {count:>12,} lignes")

print("\nImport terminé avec succès !")
print("\nProchaine étape :") # c’est pas mal de mettre un pense bête :)
print("   Exécuter : docker exec -i bi_postgres psql -U bi_user -d instacart < finalize_instacart_schema.sql")
print("   Pour ajouter les contraintes FK et les index")
```

Bien sûr, exécutez ce script :

```bash
python load_instacart.py
```

**Durée estimée :** ça a pris un peu plus de 30 minutes chez moi, ça peut varier selon votre machine (les tables `order_products` sont volumineuses). Si vous êtes sous WSL, surtout ne copiez pas les données depuis une partition Windows ! ce serait encore plus lent (cf. section « Troubleshoutings » en fin de document).

Vous devriez voir quelque chose comme :

```
Connexion à PostgreSQL...

Chargement de 6 tables...

Chargement : Départements (departments.csv)
   21 lignes chargées en 0.2s

Fichier volumineux, chargement par chunks de 100k lignes...
   Total : 32,434,489 lignes
   → Chunk 1 : 100,000/32,434,489 lignes (0.3%)
   → Chunk 2 : 200,000/32,434,489 lignes (0.6%)
   → Chunk 3 : 300,000/32,434,489 lignes (0.9%)
   ...
   → Chunk 324 : 32,400,000/32,434,489 lignes (99.9%)
   → Chunk 325 : 32,434,489/32,434,489 lignes (100.0%)
   32,434,489 lignes chargées en 523.4s (61,982 lignes/s)

============================================================
RÉCAPITULATIF DU CHARGEMENT
============================================================
Départements                             :         21 lignes
Rayons                                   :        134 lignes
Produits                                 :     49,688 lignes
Commandes                                :  3,421,083 lignes
Produits commandés (prior)               : 32,434,489 lignes
Produits commandés (train)               :  1,384,617 lignes

Import terminé avec succès !
```

### 3.5 Finalisation : clefs étrangères

Maintenant que nous avons nos tables avec leurs clefs primaires remplies avec des données, définissons les clefs étrangères :

```sql
-- finalize_instacart_schema.sql
-- Finalisation du schéma : ajout des foreign keys et index
-- À exécuter APRÈS l'import des données

\echo 'Ajout des contraintes de clés étrangères...'

-- Products → Aisles
ALTER TABLE products 
    DROP CONSTRAINT IF EXISTS products_aisle_id_fkey;
    
ALTER TABLE products 
    ADD CONSTRAINT products_aisle_id_fkey 
    FOREIGN KEY (aisle_id) REFERENCES aisles(aisle_id);

-- Products → Departments
ALTER TABLE products 
    DROP CONSTRAINT IF EXISTS products_department_id_fkey;
    
ALTER TABLE products 
    ADD CONSTRAINT products_department_id_fkey 
    FOREIGN KEY (department_id) REFERENCES departments(department_id);

-- Order_products_prior → Orders
ALTER TABLE order_products_prior 
    DROP CONSTRAINT IF EXISTS order_products_prior_order_id_fkey;
    
ALTER TABLE order_products_prior 
    ADD CONSTRAINT order_products_prior_order_id_fkey 
    FOREIGN KEY (order_id) REFERENCES orders(order_id);

-- Order_products_prior → Products
ALTER TABLE order_products_prior 
    DROP CONSTRAINT IF EXISTS order_products_prior_product_id_fkey;
    
ALTER TABLE order_products_prior 
    ADD CONSTRAINT order_products_prior_product_id_fkey 
    FOREIGN KEY (product_id) REFERENCES products(product_id);

-- Order_products_train → Orders
ALTER TABLE order_products_train 
    DROP CONSTRAINT IF EXISTS order_products_train_order_id_fkey;
    
ALTER TABLE order_products_train 
    ADD CONSTRAINT order_products_train_order_id_fkey 
    FOREIGN KEY (order_id) REFERENCES orders(order_id);

-- Order_products_train → Products
ALTER TABLE order_products_train 
    DROP CONSTRAINT IF EXISTS order_products_train_product_id_fkey;
    
ALTER TABLE order_products_train 
    ADD CONSTRAINT order_products_train_product_id_fkey 
    FOREIGN KEY (product_id) REFERENCES products(product_id);

\echo 'Contraintes FK ajoutées'

-- Créer les index pour améliorer les performances
\echo 'Création des index...'

CREATE INDEX IF NOT EXISTS idx_products_aisle ON products(aisle_id);
CREATE INDEX IF NOT EXISTS idx_products_dept ON products(department_id);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_dow ON orders(order_dow);
CREATE INDEX IF NOT EXISTS idx_orders_hour ON orders(order_hour_of_day);
CREATE INDEX IF NOT EXISTS idx_op_prior_order ON order_products_prior(order_id);
CREATE INDEX IF NOT EXISTS idx_op_prior_product ON order_products_prior(product_id);
CREATE INDEX IF NOT EXISTS idx_op_train_order ON order_products_train(order_id);
CREATE INDEX IF NOT EXISTS idx_op_train_product ON order_products_train(product_id);

\echo 'Index créés'
```

Vous avez certainement compris désormais comment on lance un script ? Allez-y !

### 3.6 Vérification

#### FK / relations (intégrité référentielle)

On vient de faire des opérations assez critiques où l’on a privilégier la flexibilité et la rapidité au prix de risques pour l’intégrité des données, il faut donc vérifier ce qu’il se passe niveau FK. Le minimum est de vérifier qu’on ne se retrouve pas avec des FK invalides : par exemple des produits qui pointe vers un `department` qui n’existe pas. Pour voir cela, intuitivement on peut chercher à dénombrer le nombre de produits dont le  `department_id` ne figure pas dans la table :

```sql

-- Produits avec department_id invalide
SELECT COUNT(*) as produits_department_invalide 
FROM products 
WHERE department_id NOT IN (SELECT department_id FROM departments);

-- Produits avec aisle_id invalide
SELECT COUNT(*) as produits_aisle_invalide 
FROM products 
WHERE aisle_id NOT IN (SELECT aisle_id FROM aisles);

-- Order_products avec order_id invalide
SELECT COUNT(*) as order_products_order_invalide 
FROM order_products_prior 
WHERE order_id NOT IN (SELECT order_id FROM orders);

-- Order_products avec product_id invalide
SELECT COUNT(*) as order_products_product_invalide 
FROM order_products_prior 
WHERE product_id NOT IN (SELECT product_id FROM products);
```

**Ne lancez pas cette requête**

On a ici un problème d’optimisation classique. Ça va aller pour vérifier les `department_id`et les `aisle_id` car il s’agit de petites tables de quelques centaines de lignes. Mais pour les commandes, chercher les  `order_id` invalides dans la table  `order_products_prior` signifie tester  chaque ligne d’une table de 32 millions de ligne pour voir si une valeur est bien présente dans une table de 3 million de lignes à *chaque fois* ! ça va prendre un temps infini.

À la place on va vérifier avec un `LEFT JOIN` (on va isoler les valeurs présentes dans une table mais pas dans l’autre), cela permettra d’utiliser l’index construit et sous le capot un hash join fera le travail beaucoup plus rapidement (en quelques dizaines de secondes) :

```sql
-- validate_ref_instacart.sql
-- Vérifier l'intégrité des données (VERSION RAPIDE avec LEFT JOIN)

\echo 'Validation des données Instacart'
\echo '=================================='
\echo ''

\echo ''
\echo 'Vérification de l''intégrité référentielle...'
\echo ''

-- Produits avec department_id invalide
\echo 'Produits avec department_id invalide :'
SELECT COUNT(*) as count
FROM products p
LEFT JOIN departments d ON p.department_id = d.department_id
WHERE p.department_id IS NOT NULL 
  AND d.department_id IS NULL;

-- Produits avec aisle_id invalide
\echo 'Produits avec aisle_id invalide :'
SELECT COUNT(*) as count
FROM products p
LEFT JOIN aisles a ON p.aisle_id = a.aisle_id
WHERE p.aisle_id IS NOT NULL 
  AND a.aisle_id IS NULL;

-- Order_products_prior avec order_id invalide (VERSION RAPIDE)
\echo 'Order_products_prior avec order_id invalide :'
SELECT COUNT(*) as count
FROM order_products_prior op
LEFT JOIN orders o ON op.order_id = o.order_id
WHERE o.order_id IS NULL;

-- Order_products_prior avec product_id invalide (VERSION RAPIDE)
\echo 'Order_products_prior avec product_id invalide :'
SELECT COUNT(*) as count
FROM order_products_prior op
LEFT JOIN products p ON op.product_id = p.product_id
WHERE p.product_id IS NULL;

\echo ''
\echo 'Finalisation terminée !'
\echo ''
\echo 'Note : Si tous les compteur ci-dessus = 0, l’intégrité est parfaite.'
\echo ''
```

#### Vérification basique

On peut très basiquement vérifier la base en affichant le nombre de lignes des tables, et afficher quelques statistiques simples. Ici par exemple les 5 départements qui vendent le plus de produit (ce qui demande de faire une jointure)

```sql
-- validate_basic_instacart.sql
-- Vérification de l'intégrité des données Instacart

\echo 'Validation des données Instacart'
\echo '=================================='
\echo ''

-- Nombre de lignes par table
\echo 'Nombre de lignes par table :'
\echo ''

SELECT 'departments' as table_name, COUNT(*) as rows FROM departments
UNION ALL
SELECT 'aisles', COUNT(*) FROM aisles
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'order_products_prior', COUNT(*) FROM order_products_prior
UNION ALL
SELECT 'order_products_train', COUNT(*) FROM order_products_train
ORDER BY table_name;

\echo ''
\echo 'Statistiques basiques :'
\echo ''

-- Top 5 départements par nombre de produits
\echo 'Top 5 départements par nombre de produits :'
SELECT 
    d.department,
    COUNT(*) as nb_products
FROM products p
JOIN departments d ON p.department_id = d.department_id
GROUP BY d.department
ORDER BY nb_products DESC
LIMIT 5;
```

Vérification : chez moi j’ai obtenu le résultat suivant :

```
Validation des données Instacart
==================================

Nombre de lignes par table :

      table_name      |   rows
----------------------+----------
 aisles               |      134
 departments          |       21
 order_products_prior | 32434489
 order_products_train |  1384617
 orders               |  3421083
 products             |    49688
(6 rows)


Statistiques basiques :

Top 5 départements par nombre de produits :
  department   | nb_products
---------------+-------------
 personal care |        6563
 snacks        |        6264
 pantry        |        5371
 beverages     |        4365
 frozen        |        4007
(5 rows)


```

On peut créer d’autres tests, comme par exemple un test de jointures :

```sql
-- test_join_instacart.sql
-- Tests de validation des relations Instacart

\echo 'TESTS DE VALIDATION INSTACART'
\echo '================================'
\echo ''

\echo 'Test jointure Products → Departments :'
SELECT d.department, COUNT(*) as nb_products
FROM products p
JOIN departments d ON p.department_id = d.department_id
GROUP BY d.department
ORDER BY nb_products DESC
LIMIT 3;

\echo ''
\echo 'Test jointure Products → Aisles → Departments :'
SELECT d.department, a.aisle, COUNT(*) as nb_products
FROM products p
JOIN aisles a ON p.aisle_id = a.aisle_id
JOIN departments d ON p.department_id = d.department_id
GROUP BY d.department, a.aisle
ORDER BY nb_products DESC
LIMIT 5;

\echo ''
\echo 'Test top 5 produits commandés :'
SELECT p.product_name, COUNT(*) as nb_commandes
FROM order_products_prior op
JOIN products p ON op.product_id = p.product_id
GROUP BY p.product_name
ORDER BY nb_commandes DESC
LIMIT 5;

\echo ''
\echo 'Vérification intégrité (doit être tout à 0) :'
SELECT 
    'Produits orphelins (dept)' as test,
    COUNT(*) as problemes
FROM products p
LEFT JOIN departments d ON p.department_id = d.department_id
WHERE p.department_id IS NOT NULL AND d.department_id IS NULL

UNION ALL

SELECT 'Produits orphelins (aisle)', COUNT(*)
FROM products p
LEFT JOIN aisles a ON p.aisle_id = a.aisle_id
WHERE p.aisle_id IS NOT NULL AND a.aisle_id IS NULL;

\echo ''
\echo 'Tests terminés !'
```

Toujours chez moi, j’ai obtenu le résultat suivant :

```
TESTS DE VALIDATION INSTACART
================================

Test jointure Products → Departments :
  department   | nb_products
---------------+-------------
 personal care |        6563
 snacks        |        6264
 pantry        |        5371
(3 rows)


Test jointure Products → Aisles → Departments :
  department   |        aisle         | nb_products
---------------+----------------------+-------------
 missing       | missing              |        1258
 snacks        | candy chocolate      |        1246
 frozen        | ice cream ice        |        1091
 personal care | vitamins supplements |        1038
 dairy eggs    | yogurt               |        1026
(5 rows)


Test top 5 produits commandés :
      product_name      | nb_commandes
------------------------+--------------
 Banana                 |       472565
 Bag of Organic Bananas |       379450
 Organic Strawberries   |       264683
 Organic Baby Spinach   |       241921
 Organic Hass Avocado   |       213584
(5 rows)


Vérification intégrité (doit être tout à 0) :
            test            | problemes
----------------------------+-----------
 Produits orphelins (aisle) |         0
 Produits orphelins (dept)  |         0
(2 rows)


Tests terminés !
```

Vous pouvez aussi créer d’autres requêtes :

- jointures simples
- jointures triples
- jointures en toutes les tables
- vérifier les orphelins (produits sans rayon, sans département, avec département invalide, commandes avec produit invalide) : on en a fait quelques unes

Par exemple, une requête pour afficher 20 commandes du dimanche matin à 10h, avec toutes les infos disponibles

```sql
-- test_all_tables_join_instacart.sql
-- Jointures complètes : commandes du dimanche matin avec détails produits
SELECT 
    o.order_id,
    o.order_dow,
    o.order_hour_of_day,
    p.product_name,
    a.aisle,
    d.department
FROM orders o
JOIN order_products_prior op ON o.order_id = op.order_id
JOIN products p ON op.product_id = p.product_id
JOIN aisles a ON p.aisle_id = a.aisle_id
JOIN departments d ON p.department_id = d.department_id
WHERE o.order_dow = 0  -- Dimanche
  AND o.order_hour_of_day = 10  -- 10h du matin
LIMIT 20;
```

Ce qui donne, toujours chez moi :

```
 order_id | order_dow | order_hour_of_day |   product_name         |         aisle        |  department
----------+-----------+-------------------+------------------------+----------------------+--------------
     7280 |         0 |                10 | Mini Cucumbers         | packaged veget…      | produce
     7280 |         0 |                10 | Red Wine Vinegar       | oils vinegars        | pantry
     7280 |         0 |                10 | Green Beans            | fresh vegetables     | produce
     7280 |         0 |                10 | Strawberries           | fresh fruits         | produce
     7280 |         0 |                10 | Honeycrisp Apples      | fresh fruits         | produce
     7280 |         0 |                10 | Banana                 | fresh fruits         | produce
     7280 |         0 |                10 | Pure Canola Oil        | oils vinegars        | pantry
     7280 |         0 |                10 | Hass Avocado           | fresh vegetables     | produce
     7280 |         0 |                10 | Carrot Sticks          | fresh vegetables     | produce
     7280 |         0 |                10 | Roasted Turkey Breast  | lunch meat           | deli
     7280 |         0 |                10 | Cherubs Heavenly Sal…  | fresh vegetables     | produce
     7280 |         0 |                10 | Steak Sauce            | marinades meat prep… | pantry
  2820099 |         0 |                10 | Organic Turkey Bacon   | hot dogs bacon sau…  | meat seafood
  2820099 |         0 |                10 | Organic Ground Turkey  | poultry counter      | meat seafood
  2820099 |         0 |                10 | Bag of Organic Bananas | fresh fruits         | produce
  2820099 |         0 |                10 | Organic Large Brown…   | eggs                 | dairy eggs
  2820099 |         0 |                10 | Protein Bar, High, W…  | energy granola bars  | snacks
  2820099 |         0 |                10 | Lean Protein & Fiber … | energy granola bars  | snacks
  2820099 |         0 |                10 | Organic Baby Spinach   | packaged vegetables… | produce
  2820099 |         0 |                10 | Green Bell Pepper      | fresh vegetables     | produce
(20 rows)
```

### 3.7 Si ça ne marche pas

#### Diagnostic de la base

Première chose à faire : créer un fichier `diagnose_instacart.sql` qui permet de vérifier :

* si la base existe
* quelles sont les tables présentes
* combien y a-t-il d’enregistrement dans chaque table
* si des clefs étrangères ont été définie et les contraintes associées
* s’il y a une connexion active à la base

On désire vérifier l’existence de la base, des tables, des clefs… mais également, ne pas perdre de vue que si par exemple on cherche à effacer la base ou modifier des tables, l’existence d’une connexion ou de clefs étrangères peut être bloquante. À vous d’utiliser ces informations à bon escient !

```sql
-- diagnose_instacart.sql
-- Diagnostic complet de la base Instacart

\echo 'DIAGNOSTIC DE LA BASE INSTACART'
\echo '=================================='
\echo ''

-- 1. Vérifier que la base existe
\echo '(1)  Bases de données présentes :'
\echo ''
SELECT datname FROM pg_database WHERE datname IN ('postgres', 'instacart', 'metabase', 'superset', 'restaurant');

\echo ''
\echo '---'
\echo ''

-- Se connecter à instacart (si elle existe)
\c instacart

\echo '(2)  Tables présentes dans instacart :'
\echo ''
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

\echo ''
\echo '---'
\echo ''

\echo '(3)  Nombre de lignes par table :'
\echo ''
DO $$
DECLARE
    r RECORD;
    row_count INTEGER;
BEGIN
    FOR r IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename
    LOOP
        EXECUTE 'SELECT COUNT(*) FROM ' || quote_ident(r.tablename) INTO row_count;
        RAISE NOTICE '  % : % lignes', RPAD(r.tablename, 30), row_count;
    END LOOP;
END $$;

\echo ''
\echo '---'
\echo ''

\echo '(4)  Contraintes de clés étrangères (FK) présentes :'
\echo ''
SELECT
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_name;

\echo ''
\echo '---'
\echo ''

\echo '(5)  Index présents :'
\echo ''
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

\echo ''
\echo '---'
\echo ''

\echo '(6)  Connexions actives à la base instacart :'
\echo ''
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    LEFT(query, 50) as query_preview
FROM pg_stat_activity
WHERE datname = 'instacart';

\echo ''
\echo '---'
\echo ''

\echo '*** Diagnostic terminé ! ***'
\echo ''
\echo 'Ce qu''il faut vérifier :'
\echo '   - Section 2 : Si des tables existent, noter lesquelles'
\echo '   - Section 4 : Si des FK existent, elles bloquent le DROP TABLE'
\echo '   - Section 6 : Si des connexions actives, elles bloquent le DROP DATABASE'
```

Pour lancer le diagnostic :

```bash
docker exec -i bi_postgres psql -U bi_user -d postgres < diagnose_instacart.sql
```

### Faire un reset

Si quelque chose se passe mal, il est naturel de tout supprimer et de repartir à zéro (un *reset*) . On peut créer un script qui réalise ce reset et qu’on lancera quand on veut tout reprendre à zéro :

```sql 
-- reset_instacart.sql 
-- Reset complet de la base Instacart
-- Usage: docker exec -i bi_postgres psql -U bi_user -d postgres < reset_instacart.sql

-- IMPORTANT : On se connecte à 'postgres', PAS à 'instacart' !
-- on ne peut pas supprimer une base si on y est connecté
-- on se connecte donc à la base de PostgreSQL lui-même
\c postgres

\echo 'Reset complet de la base Instacart'
\echo '======================================'
\echo ''

-- Terminer toutes les connexions actives à la base instacart
\echo 'Terminaison des connexions actives...'
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'instacart'
  AND pid <> pg_backend_pid();

\echo 'Connexions actives terminées'
\echo ''

-- Supprimer la base (maintenant on est connecté à 'postgres', pas à 'instacart')
\echo 'Suppression de la base instacart...'
DROP DATABASE IF EXISTS instacart;

\echo 'Ancienne base supprimée'
\echo ''

-- Recréer la base
\echo 'Création d''une nouvelle base...'
CREATE DATABASE instacart;

\echo 'Nouvelle base créée'
\echo ''

-- Vérification
\echo 'Vérification :'
\l instacart

\echo ''
\echo 'Reset terminé avec succès !'
\echo ''
\echo 'Prochaines étapes :'
\echo '   1. Créer le schéma : docker exec -i bi_postgres psql -U bi_user -d instacart < create_instacart_schema_import.sql'
\echo '   2. Importer les données : python load_instacart.py'
\echo '   3. Finaliser : docker exec -i bi_postgres psql -U bi_user -d instacart < finalize_instacart_schema.sql'

```

Et relancer les scripts (en corrigeant entre temps, inutile de relancer un script qui n’a déjà pas marché une première fois).

Voir la section « Troubleshoutings » à la fin de ce document (et n’hésitez pas à l’enrichir).

### 3.8 Un makefile, comme les vrai-e-s

Vous constatez qu’on utilise beaucoup de scripts, que l’on enchaîne dans un ordre précis selon ce qu’on veut faire (import), ou pour réaliser des tâches particulières : tests, diagnostic de la base, reset de la base, etc.

Retrouver le bon nom de fichier pour chaque script et entrer des commandes avec beaucoup d’arguments pour les exécuter peut vite devenir fastidieux. La console nous propose une commande particulièrement utile dans ce contexte : `make`.

`make` a précisément été créée pour exécuter automatiquement une séquence de commandes. Son usage le plus connu est de piloter la compilation dans le développement d’un projet, vous vous y êtes certainement confronté si vous avez développé en C/C++. `make` est aussi particulièrement utilisée pour les tâches de DevOps, où il y a beaucoup d’automatisation (c’est un peu le but).

Le principe est simple : `make` applique des règles pour exécuter des commandes (spécifiées dans ces règles), il va trouver ces règles dans un fichier `Makefile`. De manière simplifiée, la structure d’un `Makefile` est la suivante :

```makefile
target: dependancy
	commands
```

Une `target` est donc le nom de la règle. Par exemple une règle qui va lancer des commandes pour tester une opération va s’appeler `test`. `dependancy`est une dépendance, généralement ce sera un ou des fichiers nécessaires à l’application de la règle, `make` va vérifier si le fichier est à jour depuis la dernière application de la règle. C’est souvent utilisé quand on compile.  Ce n’est pas trop notre cas d’usage ici et ce n’est ni un cours sur `make` ni un cours sur la compilation donc je ne m’attarderai pas sur le sujet. Par contre, et c’est plus intéressant pour nous, une dépendance peut aussi être une règle qu’on a défini : on peut ainsi créer des règles qui appellent d’autres règles. Enfin on a une série de commandes déclenchées à l’appel de la cible (en faisant `make target`). Les commandes doivent être précédées d’une tabulation et `make` est très pointilleux sur ce point (comme Python).

Nous allons créer un fichier `Makefile` qui va nous permettre de tout bien ranger et de tout garder à portée de main en définissant donc des *targets*  et en y associant des *commandes*. Observez bien comment il est construit, ça vous éclairera peut-être pour comprendre le paragraphe précédent s’il est trop abstrait. De plus sentez-vous libre de le modifier ce `Makefile` à votre convenance.

Par exemple la commande `make help` affichera la liste des targets (règles) qu’on a défini dans notre `Makefile` (rentrez-vous bien ça dans le crâne : la documentation est comme le test un standard du métier, ça doit devenir un réflexe), `make all` lancera le pipeline complet (création de la base, création du schéma, import des données, création des FK), c’est nettement plus simple ! 

`make clean` détruira la base, et `make reset` l’effacera et en recréera une (attention ne pas lancer ces dernières commandes inconsidérément).Vous remarquerez que pour la règle `validate` j’appelle un seul script, alors que nous en avons écrit plusieurs (validation des références, différents types de requêtes…), à titre d’exercice, créez des règles pour chacun de ces scripts, et transformez la règle `validate` pour qu’elle appelle successivement toutes ces règles pour faire un test complet de votre import.

```makefile
# Makefile pour gérer l'import Instacart
# Usage: make help

# de base un makefile applique les commandes sur un fichier (dependancy)
# par défaut il va considérer que le nom de la target correspond au nom d’un fichier
# .PHONY permet de bien lui faire comprendre que ces targets 
# ne sont pas des fichiers, ça évite des confusions si d’aventure
# un fichier aurait le même nom que vos targets :
.PHONY: help reset schema import finalize validate all clean diagnose

# en réalité il y a une manière plus élégante de créer une documentation (voir note ci-dessous)
help:
	@echo "Gestion de la base Instacart"
	@echo "================================"
	@echo ""
	@echo "Commandes disponibles :"
	@echo "  make reset      - Supprimer et recréer la base"
	@echo "  make schema     - Créer le schéma (sans FK)"
	@echo "  make import     - Importer les données CSV"
	@echo "  make finalize   - Ajouter FK et index"
	@echo "  make validate   - Vérifier l'intégrité"
	@echo "  make diagnose   - Diagnostic de la base"
	@echo "  make all        - Tout faire (reset + schema + import + finalize)"
	@echo "  make clean      - Supprimer la base"
	@echo ""
	@echo "Workflow complet :"
	@echo "  make reset && make schema && make import && make finalize"

reset:
	@echo "Reset de la base..."
	@docker exec -i bi_postgres psql -U bi_user -d instacart < reset_instacart.sql

schema:
	@echo "Création du schéma..."
	@docker exec -i bi_postgres psql -U bi_user -d instacart < create_instacart_schema_import.sql

import:
	@echo "Import des données..."
	@source venv/bin/activate && python load_instacart.py

finalize:
	@echo "Finalisation (FK + index)..."
	@docker exec -i bi_postgres psql -U bi_user -d instacart < finalize_instacart_schema.sql

validate:
	@echo "Validation..."
	@docker exec -i bi_postgres psql -U bi_user -d instacart < validate_instacart.sql

all: reset schema import finalize validate
	@echo ""
	@echo "Pipeline complet terminé !"

clean:
	@docker exec bi_postgres psql -U bi_user -d postgres -c "DROP DATABASE IF EXISTS instacart;"
	@echo "Base supprimée"
	
diagnose:
	@echo "Diagnostic…"
	@docker exec -i bi_postgres psql -U bi_user -d postgres < diagnose_instacart.sql
```

Note :

> Il existe deux options très utiles de `make` :
>
> * -n : avec cette option `make` affiche sans les exécuter les commandes qu’il lancerait (permet de vérifier avant de lancer une règle)
> * -p : affiche toutes les variables et règles 
>
> Par exemple :
>
> ```makefile
> make -n clean
> 
> # affichera
> #
> # docker exec bi_postgres psql -U bi_user -d postgres -c "DROP DATABASE IF EXISTS instacart;"
> # echo "Base supprimée"
> ```
>
> 

Astuce sympa :

> Avec des expressions régulières on peut créer une documentation auto-générée avec des balises ## :
>
> ```makefile
> .DEFAULT_GOAL := help
> 
> help: ## Affiche cette aide
>   @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
>     awk 'BEGIN {FS = ":.*?## "}; {printf "%-15s %s\n", $$1, $$2}'
> 
> clean: ## Supprimela base instacart
> 	@docker exec bi_postgres psql -U bi_user -d postgres -c "DROP DATABASE IF EXISTS instacart;"
> 	@echo "Base supprimée"
> ```
>
> ```bash
> make help
> 
> # affichera :
> #
> # help            Affiche cette aide
> # clean			  Supprime la base instacart
> ```
>
> Cette astuce est tirée du billet qui présente ̀make` de manière assez complète : https://blog.stephane-robert.info/docs/developper/autres-outils/build/makefile/

Tout roule ! On peut connecter la base à Metabase et commencer à créer un dashboard

---

## Partie 4 : Connexion Metabase à Instacart

### 4.1 Ajouter la base de données dans Metabase

1. **Ouvrir Metabase** : http://localhost:3000

2. **Se connecter** avec vos identifiants (créés au TP 1)

3. Aller à `localhost:3000/admin/databases` (sinon via l’accès Admin en cliquant sur votre profil)

4. Cliquer sur `Add  database`

5. **Configuration** :

   ```
   Database type : PostgreSQL
   
   Name : Instacart
   Host : postgres
   Port : 5432
   Database name : instacart
   Username : bi_user
   Password : bi_password123
   ```

6. Cliquer sur le bouton pour sauvegarder, puis sur le bouton pour synchroniser sur la page qui apparaît 

7. **Attendre la synchronisation** (peut prendre 1-2 minutes pour analyser les 37M+ lignes)

8. **Vérifier** : Retourner sur l’accueil (`localhost:3000`) → Bases de données → Vous devez voir "Instacart"

### 4.2 Explorer les tables

Cliquez sur "Instacart" → Vous voyez les 6 tables

Cliquez sur une table (ex: `products`) pour voir :
- Aperçu des données
- Types de colonnes
- Statistiques basiques

---

## Partie 5 : Créer des visualisations exploratoires

### 5.1 Visualisation 1 : Top 10 des produits les plus vendus

**Objectif** : Identifier les produits stars

1. **+ New → Question**

2. **Instacart → order_products_prior**

3. **Configuration** :
   - Résumé : Nombre de lignes
   - Grouper par : Product → Product name
   - Trier par : Nombre de lignes, décroissant
   - Nombre de lignes : 10

   Note : cette table est la plus grande, cela peut prendre un peu de temps…
   
4. **Visualiser** : le résultat attendu est Bananas, Organic bananas, etc. positionnées en tête

5. **Changer en Bar chart** (horizontal de préférence)

6. **Personnaliser** :
   - Titres des axes : "Nombre de commandes" et "Produit"
   - Afficher les valeurs sur les barres

7. **Sauvegarder** :
   - Nom : "Top 10 produits les plus vendus"
   - Créer un nouveau dashboard (collection, cliquer sur les trois petits points dans la boîte « où sauvegarder… ») : "Analyse Instacart"

Vous devriez obtenir quelque chose comme ça :

![Visualisation 1 top 10 des produits les plus vendus](./Images/Instacart-Metabase-1.png)

### 5.2 Visualisation 2 : Commandes par jour de la semaine

**Objectif** : Comprendre les patterns hebdomadaires

1. **+ New → Requête SQL**

2. Bien sélectionner `Instacart` dans le menu déroulant au dessus de la zone de saisie de la requête

3. Dans la base les jours de la semaine sont codés par des entiers de 0 à 6 (0 = dimanche). On  va donc utiliser un `CASE … WHEN …` pour afficher le nom des jours :

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
ORDER BY order_dow
```

4. **Visualiser → Bar chart**
5. Changez les labels des axes (« Nombre de commandes » et « Jour »)
6. **Sauvegarder** : "Commandes par jour de la semaine" → Dashboard "Analyse Instacart"

**Insight attendu** : Pic le dimanche/lundi (courses de début de semaine)

![Visualisation 2 : commandes par jour de la semaine](./Images/Instacart-Metabase-2.png)

### 5.3 Visualisation 3 : Commandes par heure de la journée

**Objectif** : Identifier les heures de pointe

Pour la suite on va indiquer ici les requêtes SQL produisant les visualisations voulues (plus lisible que décrire l’interface)

1. **+ New → Question SQL**

```sql
SELECT 
    order_hour_of_day as heure,
    COUNT(*) as nb_commandes
FROM orders
GROUP BY order_hour_of_day
ORDER BY order_hour_of_day
```

2. **Visualiser → Line chart**
   Note : on voit que par défaut Metabase prend les deux variables comme variables dépendantes, on va régler ça avec la personnalisation

3. **Personnaliser** :

   Changer les labels des axes et associer les données aux bons axes :

   - X-axis : "Heure de la journée (0-23h)"
   - Y-axis : "Nombre de commandes"

4. **Sauvegarder** ("Distribution des commandes par heure") → Ajouter à la collection « Analyse Instacart » 

  **Insight attendu** : Pics en matinée (10-11h) et après-midi (14-16h)

![Visualisation 3 : Commandes par heure de la journée](./Images/Instacart-Metabase-3.png)

### 5.4 Visualisation 4 : Top départements par ventes

**Objectif** : Quels départements génèrent le plus de volume ?

1. **+ New → Question SQL**

```sql
SELECT 
    d.department,
    COUNT(*) as nb_produits_vendus
FROM order_products_prior as op
JOIN products as p ON op.product_id = p.product_id
JOIN departments as d ON p.department_id = d.department_id
GROUP BY d.department
ORDER BY nb_produits_vendus DESC
LIMIT 10
```

La aussi la requête peut être un peu longue à exécuter.

2. **Visualiser → Bar chart (horizontal)**

3. Personnaliser (vous commencez à avoir l’habitude…)

4. **Sauvegarder** : "Top 10 départements" → Dashboard

  **Insight attendu** : "produce" (fruits/légumes) largement en tête

![Visualisation 4 : Top 10 départements](./Images/Instacart-Metabase-4.png)

### 5.5 Visualisation 5 : Taux de réachat moyen

**Objectif** : Fidélité des clients (produits déjà commandés)

1. **+ New → Question SQL**

```sql
SELECT 
    ROUND(AVG(reordered), 2) as taux_reachat_pct
FROM order_products_prior
```

2. **Visualiser → Nombre**

3. **Personnaliser** :
   - Formatage : Style -> pourcentage (vous pouvez aussi définir un formatage conditionnel pour changer la couleur en fonction de la valeur)
   - Titre : "Taux de réachat moyen"
   - Description : "Pourcentage de produits déjà commandés auparavant"

4. **Sauvegarder** 

**Résultat attendu** : ~59% (forte fidélité produit)

![Visualisation 5 : Taux de réachat moyen](./Images/Instacart-Metabase-5.png)

### 5.6 Visualisation 6 : Distribution du nombre de produits par commande

**Objectif** : Taille moyenne du panier

1. **+ New → Question SQL**

```sql
WITH products_per_order AS (
    SELECT 
        order_id,
        COUNT(*) as nb_products
    FROM order_products_prior
    GROUP BY order_id
)
SELECT 
    nb_products,
    COUNT(*) as nb_commandes
FROM products_per_order
WHERE nb_products <= 30  -- Limiter pour la lisibilité
GROUP BY nb_products
ORDER BY nb_products
```

2. **Visualiser → Bar chart**

3. **Personnaliser** :
   - X-axis : "Nombre de produits"
   - Y-axis : "Nombre de commandes"

4. **Sauvegarder** : "Distribution taille panier" (mettre une description plus explicte) 

  **Insight attendu** : Distribution autour de 5-10 produits/commande

![Visualisation 6 : Distribution taille panier](./Images/Instacart-Metabase-6.png)

---

## Partie 6 : Assembler le dashboard

### 6.1 Organiser le dashboard

1. **Créer un nouveau dashboard** : Collections → "Analyse Instacart" → Nouveau → Nouveau tableau de bord 
   (Nom :« Dashboard Instacart - Analyse e-Commerce)

2. Cliquer sur « ajouter un graphique » et sélectionner dans la liste sur le panneau latéral droit

3. **Organiser les visualisations** sur la grille :

   ![Dashboard](./Images/Instacart-Metabase-Dashboard.png)

4. **Redimensionner et placer** chaque élément par glisser-déposer

### 6.2 Ajouter un titre et description

1. **Ajouter un texte** (icône "T")
   - Vous pouvez mettre en forme le texte avec du markdown
   - Pour aller plus loin, vous pouvez chercher dans la doc comment on insère des variables dans le texte (plutôt que de les « hardcoder »)

```
# 🛒 Analyse Instacart - E-commerce

Dataset : 3.4M commandes, 50k produits, 37M articles commandés

**Insights clés :**
- Produits les plus populaires
- Patterns temporels (jour/heure)
- Comportement d'achat (taille panier, réachat)
- Performance par département

---
*Source : Kaggle Instacart Market Basket Analysis*
```

2. **Placer en haut du dashboard**
2. Vous pouvez aussi ajouter des filtres (voir TP 1)

### 6.4 Sauvegarder

**Cliquer "Sauvegarder"** en haut à droite

---

## Partie 7 : Analyses avancées (pour aller plus loin)

Voici quelques requêtes qui peuvent vous inspirer pour créer des indicateurs plus élaborées. Tester les, créez les vôtres en fonction des questions que vous vous posez !

### 7.1 Analyse de cohorte : Fréquence de commande

```sql
SELECT 
    days_since_prior_order as jours_entre_commandes,
    COUNT(*) as nb_commandes
FROM orders
WHERE days_since_prior_order IS NOT NULL
  AND days_since_prior_order <= 30
GROUP BY days_since_prior_order
ORDER BY days_since_prior_order
```

**Visualisation** : Line chart

**Insight** : Pics à 7, 14, 30 jours (habitudes hebdomadaires/mensuelles)

### 7.2 Top produits réachetés

```sql
SELECT 
    p.product_name,
    COUNT(*) as nb_fois_rachete
FROM order_products_prior op
JOIN products p ON op.product_id = p.product_id
WHERE op.reordered = 1
GROUP BY p.product_name
ORDER BY nb_fois_rachete DESC
LIMIT 10
```

**Insight** : Produits de base (lait, bananes, pain) vs produits occasionnels

### 7.3 Analyse par rayon (aisle)

```sql
SELECT 
    a.aisle,
    COUNT(DISTINCT op.order_id) as nb_commandes,
    COUNT(*) as nb_produits_vendus,
    ROUND(AVG(op.reordered) * 100, 1) as taux_reachat
FROM order_products_prior op
JOIN products p ON op.product_id = p.product_id
JOIN aisles a ON p.aisle_id = a.aisle_id
GROUP BY a.aisle
ORDER BY nb_produits_vendus DESC
LIMIT 15
```

**Visualisation** : Table avec tri interactif

### 7.4 Heatmap Jour × Heure (avancé)

Là c’est une question de transition pour introduire Superset : Metabase ne dispose pas de ce type de graphique.

On peut déjà créer un tableau, pour cela il faut déjà une requête qui produise des données intéressantes à afficher sous cette forme. Par exemple :

```sql
SELECT 
    order_dow as jour,
    order_hour_of_day as heure,
    COUNT(*) as nb_commandes
FROM orders
GROUP BY order_dow, order_hour_of_day
ORDER BY order_dow, order_hour_of_day
```

**Note** : comment l’afficher ? On peut créer d’autres types de figures à la place :

- Pivot Table (jour × heure) → Tableau croisé des volumes (vous pouvez ensuite créer un formatage conditionnel pour afficher des couleurs, c’est un « *workaround*)
- Bar Chart groupé → Commandes par heure, coloré par jour
- Line Chart multiple → Une ligne par jour de la semaine

Mais le mieux est de passer à Superset !

---

## Partie 8 : Optimisation et bonnes pratiques

### 8.1 Requêtes lentes ?

**Symptômes** : Visualisations prennent >10 secondes à charger

**Solutions** :

1. **Vérifier les index** (déjà créés dans le schéma)

2. **Limiter les jointures** : Éviter de joindre les 37M lignes à chaque fois

3. **Créer des vues matérialisées** pour les agrégations fréquentes :

```sql
-- Vue matérialisée : Produits avec stats
CREATE MATERIALIZED VIEW mv_product_stats AS
SELECT 
    p.product_id,
    p.product_name,
    a.aisle,
    d.department,
    COUNT(*) as nb_fois_commande,
    SUM(op.reordered) as nb_fois_rachete,
    ROUND(AVG(op.reordered) * 100, 1) as taux_reachat
FROM products p
LEFT JOIN aisles a ON p.aisle_id = a.aisle_id
LEFT JOIN departments d ON p.department_id = d.department_id
LEFT JOIN order_products_prior op ON p.product_id = op.product_id
GROUP BY p.product_id, p.product_name, a.aisle, d.department;

-- Rafraîchir la vue (à faire périodiquement)
REFRESH MATERIALIZED VIEW mv_product_stats;
```

Puis utiliser `mv_product_stats` au lieu de faire les jointures à chaque fois.

### 8.2 Tester les performances

```bash
# Voir le plan d'exécution d'une requête
docker exec -it bi_postgres psql -U bi_user -d instacart << 'EOF'
EXPLAIN ANALYZE
SELECT 
    p.product_name,
    COUNT(*) as nb_commandes
FROM order_products_prior op
JOIN products p ON op.product_id = p.product_id
GROUP BY p.product_name
ORDER BY nb_commandes DESC
LIMIT 10;
EOF
```

**Temps acceptable** : < 3 secondes pour la plupart des requêtes

---

## Sauvegarder votre travail

Tout est automatiquement sauvegardé dans PostgreSQL (volume `postgres_data`).

Si néanmoins vous voulez réaliser une sauvegarde manuelle, vous pouvez toujours faire des dumps des bases contenant les données et les métadonnées de Metabase

```bash
# Backup de la base Instacart
docker exec bi_postgres pg_dump -U bi_user instacart > ~/bi-formation/backups/instacart_$(date +%Y%m%d).sql

# Backup du dashboard Metabase (dans la base metabase)
docker exec bi_postgres pg_dump -U bi_user metabase > ~/bi-formation/backups/metabase_$(date +%Y%m%d).sql
```

---

## Ressources

**Documentation** :
- Metabase SQL : https://www.metabase.com/docs/latest/questions/native-editor/writing-sql
- PostgreSQL Window Functions : https://www.postgresql.org/docs/current/tutorial-window.html

**Inspiration** :
- Kaggle Kernels Instacart : https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis/code


---

## Troubleshootings

### Problème : Import Python très lent

**Cause** : Fichiers dans `/mnt/c/` (Windows)

**Solution** :
```bash
# Vérifier que data/ est bien dans le système Linux
pwd  # Doit afficher /home/<user>/bi-formation
ls -la data/instacart/  # Fichiers doivent être là
```

### Problème : "Out of memory" pendant l'import

**Cause** : Pas assez de RAM allouée à Docker

**Solution** :
- Docker Desktop → Settings → Ressources
- Regarder si vous avez l’économie de ressources activités (Il faudrait 4-6 GB minimum)
- Redémarrer Docker

### Problème : Metabase ne voit pas les tables

**Cause** : Synchronisation pas terminée ou base mal connectée

**Solution** :
1. Settings → Admin → Databases → Instacart
2. "Sync database schema now"
3. Attendre 2-3 minutes
4. Rafraîchir la page

### Problème : Requêtes timeout (>30s)

**Cause** : Pas d'index sur colonnes jointes

**Solution** : Vérifier que les index ont bien été créés :

```bash
docker exec -it bi_postgres psql -U bi_user -d instacart -c "\di"
```

Vous devriez voir 7-8 index. Si absents, relancer `create_instacart_schema.sql`.

