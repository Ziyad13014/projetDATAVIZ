# TP 0 / Guide d'installation - Prérequis pour la formation BI

**Enseignant :** Jean Delpech

**Cours :** Analyse de données avancée

**Classe :** B3 Data/IA	

**Année scolaire :** 2025/2026

**Dernière mise à jour :** avril 2026

---

Objectif :

Ce guide vous accompagne dans l'installation des outils nécessaires pour la semaine de formation **Analyse de données avancée** (Business Intelligence). Suivez attentivement les instructions correspondant à votre système d'exploitation.

---

## Vue d'ensemble des outils à installer

En cours nous avons vu les bases de la containerisation avec Docker, dans l’objectif de créer un pipeline BI. Nous allons utiliser Metabase, PostgreSQL et bien sûr python. Le présent document vous guide donc pour installer : 

1. dans un premier temps :

- **Docker** : Plateforme de conteneurisation (obligatoire)
- **Docker Compose** : Orchestration de conteneurs (inclus avec Docker Desktop)
- **Python 3.8+** : Pour les scripts d'import de données
- **Éditeur de texte** : celui que vous voulez, mais je vous indique comment installer VS Code qui fonctionne très bien avec 

> Pour les système d’exploitation Windows on passera par un environnement WSL2 (Ubuntu) qu’on installera préalablement.

2. Dans un second temps (dans des containers) :

- **PostgreSQL**
- **Metabase**
- **Superset**

Dans le présent document on ne s’occupe que de la partie (1), vous procéderez à l’installation du reste (2) via un fichier docker compose dans le guide suivant.

---

## Installation pour Windows

### Étape 1 : Activer WSL2 (Windows Subsystem for Linux)

WSL2 permet d'exécuter un environnement Linux directement sous Windows. C'est la méthode recommandée pour Docker.

**Prérequis** :
- Windows 10 version 2004+ (Build 19041+) ou Windows 11
- Droits administrateur sur votre machine

**Installation** :

1. **Ouvrir PowerShell en tant qu'administrateur** :
   - Clic droit sur le menu Démarrer → "Windows PowerShell (Admin)" ou "Terminal (Admin)"

2. **Installer WSL2** :
   ```powershell
   wsl --install
   ```
   
   Cette commande va :
   - Activer les fonctionnalités nécessaires
   - Installer la distribution Ubuntu par défaut
   - Configurer WSL2 comme version par défaut

3. **Redémarrer votre ordinateur** (obligatoire)

4. **Premier lancement d'Ubuntu** :
   - Cherchez "Ubuntu" dans le menu Démarrer et lancez l'application
   - Lors du premier lancement, vous devrez :
     - Attendre l'installation (quelques minutes)
     - Créer un nom d'utilisateur Linux (minuscules, pas d'espaces)
     - Créer un mot de passe (il ne s'affichera pas quand vous tapez - c'est normal)
   
   **IMPORTANT** : Notez bien ces identifiants, vous en aurez besoin !

5. **Mettre à jour Ubuntu** :
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

**Vérification WSL2** :
```powershell
# Dans PowerShell
wsl --list --verbose
```

Vous devriez voir :
```
  NAME      STATE           VERSION
* Ubuntu    Running         2
```

Si VERSION = 1, mettez à jour :
```powershell
wsl --set-version Ubuntu 2
```

### Étape 2 : Installer Docker Desktop pour Windows

1. **Télécharger Docker Desktop** :
   - Allez sur https://www.docker.com/products/docker-desktop
   - Téléchargez "Docker Desktop for Windows"

2. **Installer Docker Desktop** :
   - Exécutez l'installateur
   - **Cochez** "Use WSL 2 instead of Hyper-V" (doit être <u>coché</u> par défaut)
   - Pensez à cocher "Add shortcut to desktop" si vous aimez avoir des icônes de lancement sur votre bureau (optionnel)
   - Suivez l'assistant d'installation
   - Redémarrez si demandé

3. **Configuration Docker Desktop** :
   
   - Lancez Docker Desktop
   - **Première fois** : Acceptez les conditions d'utilisation
   - **Settings** (icône engrenage) → **General** :
     - "Use the WSL 2 based engine" doit être <u>coché</u>
   - **Settings** → **Resources** → **WSL Integration** :
     - "Enable integration with my default WSL distro" <u>coché</u>
     - Activez "Ubuntu" dans la liste
   
4. **Vérification Docker dans WSL** :
   
   - Ouvrez Ubuntu (depuis le menu Démarrer)
   ```bash
   docker --version
   docker compose version
   docker run hello-world
   ```
   
   Vous devriez voir :
   ```
   Docker version 24.x.x
   Docker Compose version v2.x.x
   
   Hello from Docker!
   This message shows that your installation appears to be working correctly.
   ```

### Étape 3 : Installer Python dans WSL

À priori Python est installé sous Ubuntu par défaut, mais ce n’est pas toujours le cas de `pip` et `venv` qui requièrent des packages spécifiques :

```bash
# Dans le terminal Ubuntu
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Vérification
python3 --version  # Doit afficher Python 3.10+
pip3 --version
```

### Étape 4 : Configuration de l'espace de travail

**TRÈS IMPORTANT - Emplacement des fichiers** :

Docker dans WSL2 a besoin d'accéder aux fichiers dans le système de fichiers Linux pour avoir de bonnes performances. Vous pouvez accéder à vos dossiers et fichiers Windows depuis WSL2 (vous pouvez accéder à vos volumes depuis `/mnt/`, mais il y a un protocole de « conversion » durant l’accès qui ralentit énormément ce dernier (j’en ai fait l’amère expérience en traitant des Go de données) : importez donc vos dataset dans le système de fichier de WSL.

On va donc créer un répertoire pour stocker les données de la formation, les scripts et environnements virtuels…

**À FAIRE** :

```bash
# Dans Ubuntu, créez votre dossier de travail dans votre home Linux
cd ~
mkdir bi-formation
cd bi-formation
pwd  # Doit afficher /home/votre_nom/bi-formation
```

**À NE PAS FAIRE** :

```bash
# Ne travaillez PAS dans /mnt/c/ (système Windows monté = très lent)
cd /mnt/c/Users/VotreNom/Documents  # NON !
```

**Accéder à vos fichiers depuis Windows** :

Vous allez certainement manipuler les fichiers, etc. depuis votre explorateur de fichier Windows ou d’autres applications. Pour éditer vos fichiers avec un éditeur Windows ou copier des données :

- Ouvrez l'explorateur Windows
- Dans la barre d'adresse, tapez : `\\wsl$\Ubuntu\home\<votre_nom>\bi-formation` (convention : on met entre chevrons `< >` les éléments d’une ligne de commande qu’il faut adapter à votre environnement/situation)
- Conseillé : vous pouvez créer un raccourci pour y accéder facilement

Pour l’édition de fichier, si vous lancez VS Code dans le répertoire où se trouvent les scripts que vous voulez éditer, il s’ouvrira de manière totalement transparente (d’où l’intérêt d’utiliser VS Code pour l’édition de fichiers) :

```bash
# Installer VS Code dans Windows, puis dans Ubuntu :
cd ~/bi-formation
code .  # Ouvre VS Code directement dans le dossier WSL
```

### Étape 5 : Test complet de l'environnement

```bash
# Dans Ubuntu
cd ~/bi-formation

# Créer un fichier docker-compose de test
cat > docker-compose-test.yml << 'EOF'
version: '3.8'
services:
  test:
    image: hello-world
EOF

# Lancer le test
docker compose -f docker-compose-test.yml up

# Nettoyer
docker compose -f docker-compose-test.yml down
rm docker-compose-test.yml
```

**Si tout fonctionne on est paré pour suivre le premier tuto (installer metabase, superset et jouer avec un premier dataset) !**

---

## Installation pour MacOS

> Disclaimer : je ne dispose hélas pas de machine sous MacOS, il s’agit donc d’une procédure que je n’ai pas personnellement testée, n’hésitez pas à me faire par de vos retours sur le sujet.

### Étape 1 : Vérifier la compatibilité

**Vérifiez votre processeur** :

- Menu Pomme → "À propos de ce Mac"
- Notez si vous avez :
  - **Apple Silicon** (M1, M2, M3, M4) → Téléchargez la version Apple Silicon
  - **Intel** → Téléchargez la version Intel

### Étape 2 : Installer Docker Desktop

1. **Télécharger Docker Desktop** :
   - Allez sur https://www.docker.com/products/docker-desktop
   - Choisissez la bonne version (Apple Silicon ou Intel)

2. **Installer** :
   - Ouvrez le fichier `.dmg` téléchargé
   - Glissez Docker.app dans le dossier Applications
   - Lancez Docker depuis Applications
   - **Première fois** :
     - Autorisez l'installation des composants système (mot de passe requis)
     - Acceptez les conditions d'utilisation

3. **Configuration recommandée** :
   - Docker Desktop → **Settings** (icône engrenage)
   - **Resources** → **Advanced** :
     - Memory : 4 GB minimum (8 GB recommandé si vous avez 16 GB+ de RAM)
     - CPU : 2 minimum (4 recommandé)
   - Cliquez sur "Apply & Restart"

### Étape 3 : Vérifier l'installation

Ouvrez le Terminal (Applications → Utilitaires → Terminal) :

```bash
docker --version
docker compose version
docker run hello-world
```

Vous devriez voir les versions et le message "Hello from Docker!"

### Étape 4 : Installer Python

**Python 3 est préinstallé sur macOS**, mais vérifions :

```bash
python3 --version  # Doit afficher Python 3.9+
pip3 --version
```

Si Python n'est pas installé ou version < 3.8 :

**Option A : Via Homebrew (recommandé)**
```bash
# Installer Homebrew si pas déjà fait
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installer Python
brew install python
```

**Option B : Via python.org**
- Téléchargez depuis https://www.python.org/downloads/
- Installez le package

### Étape 5 : Configuration de l'espace de travail

```bash
# Créer votre dossier de travail
cd ~
mkdir bi-formation
cd bi-formation
pwd  # Doit afficher /Users/votre_nom/bi-formation
```

### Étape 6 : Test complet

```bash
cd ~/bi-formation

# Test Docker
cat > docker-compose-test.yml << 'EOF'
version: '3.8'
services:
  test:
    image: hello-world
EOF

docker compose -f docker-compose-test.yml up
docker compose -f docker-compose-test.yml down
rm docker-compose-test.yml
```

**Si tout fonctionne on est paré pour suivre le premier tuto (installer metabase, superset et jouer avec un premier dataset) !**

---

## Installation pour Linux (Ubuntu/Debian)

> Disclaimer : étant un utilisateur de Debian, je ne connais pas la procédure sur d’autres distributions, mais la logique est la même. Généralement les étudiant-e-s utilisent Ubuntu.
>
> Par ailleurs je reprends le script d’installation de Docker, mais privilégiez toujours le script que vous trouverez sur le site officiel (qui sera plus à jour)

### Étape 1 : Installer Docker Engine

```bash
# Mise à jour des paquets
sudo apt update

# Installation des dépendances
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Ajout de la clé GPG officielle de Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Ajout du dépôt Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installation de Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Étape 2 : Configuration post-installation

**Permettre à votre utilisateur d'utiliser Docker sans sudo** :

```bash
# Ajouter votre utilisateur au groupe docker
sudo usermod -aG docker $USER

# Appliquer les changements de groupe (2 options)
# Option 1 : Se déconnecter puis se reconnecter
# Option 2 : Exécuter cette commande
newgrp docker
```

**Démarrer Docker au démarrage** :
```bash
sudo systemctl enable docker
sudo systemctl start docker
```

### Étape 3 : Installer Python

À priori python est déjà installé, mais ce ne sera pas le cas de `pip` et `venv` qui requièrent des packages spécifiques :

```bash
# Installation de Python et pip
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Vérification
python3 --version  # Doit afficher Python 3.8+
pip3 --version
```

### Étape 4 : Vérification

```bash
# Test Docker (SANS sudo maintenant)
docker --version
docker compose version
docker run hello-world
```

Si vous obtenez une erreur de permission, relancez `newgrp docker` ou déconnectez-vous/reconnectez-vous.

### Étape 5 : Configuration de l'espace de travail

```bash
cd ~
mkdir bi-formation
cd bi-formation
```

### Étape 6 : Test complet

```bash
cd ~/bi-formation

cat > docker-compose-test.yml << 'EOF'
version: '3.8'
services:
  test:
    image: hello-world
EOF

docker compose -f docker-compose-test.yml up
docker compose -f docker-compose-test.yml down
rm docker-compose-test.yml
```

**Si tout fonctionne on est paré pour suivre le premier tuto (installer Metabase, Superset et jouer avec un premier dataset) !**

---

## Installation des dépendances Python (tous OS)

Une fois Docker et Python installés, nous allons créer un **environnement virtuel Python**. Même si on utilise des conteneurs pour notre projet, dès qu’on développe sur notre machine il faut créer un environnement virtuel (pour isoler les packages qu’on va utiliser, etc.).

### Création de l'environnement virtuel

```bash
# Depuis votre terminal (Ubuntu WSL pour Windows, Terminal pour Mac/Linux)
cd ~/bi-formation

# Créer un environnement virtuel nommé 'venv'
python3 -m venv venv

# Activer l'environnement virtuel
# Linux/Mac/WSL :
source venv/bin/activate

```

**Note importante** : Vous devrez activer cet environnement virtuel **à chaque nouvelle session de terminal** avant de travailler sur le projet :
```bash
cd ~/bi-formation
source venv/bin/activate  # Linux/Mac/WSL
```

Si vraiment c’est trop difficile pour vous de taper ces deux lignes en début de session, vous pouvez définir un alias dans votre `.bashrc` ou `.bash_aliases` (si celui-ci existe) par exemple : `alias bi='cd ~/bi-formation && source venv/bin/activate'`

Vous n’aurez alors plus qu’à taper `bi` et vous irez directement dans le bon répertoire et activerez l’environnement virtuel.

> Il y a des outils plus sophistiqués pour créer/gérer des environnements virtuels pour Python, par exemple `virtualenv` (dont `venv` est dérivé) mais surtout `uv`, mais ici `venv` sera bien suffisant.

### Installation des packages Python

```bash
# IMPORTANT : Assurez-vous que (venv) apparaît dans votre prompt
# Cela confirme que l'environnement virtuel est activé

# Mise à jour de pip dans le venv
pip install --upgrade pip

# Installation des packages nécessaires
pip install pandas sqlalchemy psycopg2-binary numpy

# Vérification
python -c "import pandas; import sqlalchemy; import psycopg2; import numpy; print('Tous les packages sont installés')"

# Optionnel : Créer un fichier requirements.txt pour la reproductibilité
pip freeze > requirements.txt
```

**Note pour macOS M1/M2/M3** : Si vous rencontrez des problèmes avec `psycopg2-binary`, essayez :
```bash
pip install psycopg2-binary --no-binary psycopg2-binary
# Ou installez les dépendances système :
brew install postgresql
pip install psycopg2-binary
```

### Désactiver l'environnement virtuel

```bash
deactivate
```

Le prompt reviendra à la normale (sans `(venv)`).

### Fichier requirements.txt

Votre fichier `requirements.txt` devrait contenir quelque chose comme :
```
numpy==1.26.4
pandas==2.2.0
psycopg2-binary==2.9.9
SQLAlchemy==2.0.25
```

**Rappel** : l’avantage est que n'importe qui peut recréer exactement le même environnement avec :

```bash
pip install -r requirements.txt
```

---

## Installation d'un éditeur de code 

Normalement vous avez déjà…

**VS Code (fortement recommandé, surtout avec WSL)** :

1. Téléchargez depuis https://code.visualstudio.com/
2. Installez-le
3. **Extensions recommandées** :
   - Docker (pour visualiser conteneurs/images)
   - Python
   - WSL (pour Windows uniquement - permet d'éditer directement dans WSL)

**Utilisation avec WSL (Windows)** :
```bash
# Depuis Ubuntu
cd ~/bi-formation
code .  # Ouvre VS Code dans le dossier WSL
```

VS Code détectera automatiquement WSL et installera le serveur distant.

---

## On vérifie que tout est ok

Assurez-vous que toutes ces commandes fonctionnent :

```bash
# 0. Activation de l'environnement virtuel
cd ~/bi-formation
source venv/bin/activate  # Vous devez voir (venv) dans le prompt

# 1. Versions
docker --version              # Doit afficher v24.x ou supérieur
docker compose version        # Doit afficher v2.x ou supérieur
python --version             # Doit afficher 3.8 ou supérieur (notez : python, pas python3)

# 2. Test Docker
docker run hello-world       # Doit afficher "Hello from Docker!"

# 3. Test Python packages (DANS le venv activé)
python -c "import pandas, sqlalchemy, psycopg2, numpy"  # Pas d'erreur

# 4. Vérifier l'emplacement du dossier de travail
pwd
# Windows/WSL : doit afficher /home/votre_nom/bi-formation
# Mac : doit afficher /Users/votre_nom/bi-formation  
# Linux : doit afficher /home/votre_nom/bi-formation

# 5. Vérifier que le venv existe
ls venv/  # Doit montrer des dossiers bin/, lib/, etc.
```

**Si tout fonctionne on est paré pour suivre le premier tuto (installer Metabase, Superset et jouer avec un premier dataset) !**

## SOS - Problèmes courants

### Windows : "WSL 2 installation is incomplete"

**Cause** : Composants de virtualisation non activés

**Solution** :
1. Ouvrez PowerShell en admin :
```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```
2. Redémarrez
3. Téléchargez et installez le kernel WSL2 : https://aka.ms/wsl2kernel

### Windows : "Cannot connect to the Docker daemon"

**Cause** : Docker Desktop n'est pas lancé ou intégration WSL pas activée

**Solution** :

1. Lancez Docker Desktop (icône dans la barre des tâches)
2. Attendez que l'icône devienne verte
3. Vérifiez Settings → Resources → WSL Integration

### macOS : "Docker.app" can't be opened because Apple cannot check it

**Cause** : Sécurité macOS bloque l'application

**Solution** :
1. Préférences Système → Confidentialité et sécurité
2. Cliquez sur "Ouvrir quand même" à côté de Docker
3. Relancez Docker

### macOS M1/M2/M3 : "exec format error" ou image lente

**Cause** : Image Docker non optimisée pour ARM

**Solution** : Les images que nous utilisons (postgres, metabase, superset) supportent ARM64. Si problème :
```bash
docker pull --platform linux/amd64 nom_image
```

### Linux : "permission denied while trying to connect to Docker"

**Cause** : Utilisateur pas dans le groupe docker

**Solution** :
```bash
sudo usermod -aG docker $USER
newgrp docker
# Ou déconnectez-vous et reconnectez-vous
```

### Tous OS : "Cannot download Docker image" / "network timeout"

**Cause** : Pare-feu, proxy, ou problème réseau

**Solution** :
1. Vérifiez votre connexion Internet
2. Si derrière un proxy d'entreprise :
   - Docker Desktop → Settings → Resources → Proxies
   - Configurez votre proxy HTTP/HTTPS
3. Si firewall : autorisez Docker Desktop

### Python : "ModuleNotFoundError: No module named 'pandas'"

**Cause** : Package non installé, environnement virtuel non activé, ou mauvais environnement Python

**Solution** :
```bash
# 1. Vérifiez que vous êtes dans le bon dossier
cd ~/bi-formation

# 2. Activez l'environnement virtuel
source venv/bin/activate
# Vous DEVEZ voir (venv) dans votre prompt

# 3. Réinstallez les packages
pip install --upgrade pip
pip install pandas sqlalchemy psycopg2-binary numpy

# 4. Vérifiez l'installation
python -c "import pandas; print(pandas.__version__)"
```

**Si le problème persiste** :
```bash
# Recréez l'environnement virtuel
cd ~/bi-formation
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install pandas sqlalchemy psycopg2-binary numpy
```

### Python : "Command 'python' not found" mais python3 fonctionne

**Cause** : Dans l'environnement virtuel, `python` devrait pointer vers `python3`

**Solution** :
```bash
# Vérifiez que le venv est activé
source venv/bin/activate  # Le prompt doit montrer (venv)

# Dans un venv activé, ces deux commandes sont équivalentes :
which python   # Doit pointer vers ~/bi-formation/venv/bin/python
which python3  # Peut pointer vers /usr/bin/python3 ou venv

# Si 'python' ne fonctionne toujours pas, utilisez 'python3' partout
```

### Windows/WSL : "Docker volumes are very slow"

**Cause** : Fichiers dans /mnt/c/ (système Windows monté)

**Solution** :
```bash
# Déplacez votre projet dans le système de fichiers Linux
cd ~
mkdir bi-formation
mv /mnt/c/Users/.../mon-projet/* ~/bi-formation/
```

---

## Support

Si vous rencontrez des problèmes non résolus par ce guide :

1. **Vérifiez les logs** :
   
   ```bash
   # Logs Docker Desktop
   # Windows : %APPDATA%\Docker\log.txt
   # Mac : ~/Library/Containers/com.docker.docker/Data/log
   # Linux : journalctl -u docker
   ```
   
2. **Recherchez l'erreur** :
   - RTFM! : Documentation Docker : https://docs.docker.com/

---

## Ressources complémentaires

- **Docker** :
  - Getting started : https://docs.docker.com/get-started/
  - WSL2 backend : https://docs.docker.com/desktop/wsl/
  
- **WSL2** :
  - Documentation Microsoft : https://learn.microsoft.com/windows/wsl/
  - Best practices : https://learn.microsoft.com/windows/wsl/filesystems

- **Python**  (pour plus tard) :
  - Documentation pandas : https://pandas.pydata.org/docs/
  - Documentation SQLAlchemy : https://docs.sqlalchemy.org/

