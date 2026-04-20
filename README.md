
# Prospector

Une application web complète développée avec **Flask** pour la gestion de projets, le matching de compétences, le suivi administratif entre Chefs de Projets (CDP), Clients et Intervenants.

## Table des Matières

1. Fonctionnalités Principales
2. Installation et Démarrage
3. Modélisation de la Base de Données
4. Détails Techniques
5. Manuel Utilisateur

---

## Fonctionnalités Principales

* **Gestion de Projets (CRUD)** : Création, édition, suivi de jalons et timeline visuelle.
* **Système de Matching ("Tinder B2B")** : Algorithme de calcul de pertinence entre les tags d'un projet et les compétences des intervenants. Interface de "swipe" pour valider ou écarter des profils.
* **Attribution des Ressources** : Interface administrateur pour valider les "matchs" et assigner officiellement des intervenants aux projets.
* **Tableau de Bord Kanban** : Suivi des statuts des propositions (Brouillon, En attente, Négociation, Validé) avec Drag & Drop.
* **Messagerie Instantanée** : Chat en temps réel (stocké en BDD) entre utilisateurs.
* **Gestion Documentaire** : Upload et téléchargement de fichiers administratifs.
* **Statistiques** : Visualisation graphique (Chart.js) de l'offre et la demande de compétences.
* **Interface Réactive** : Support complet du **Dark Mode** (Thème sombre) et design responsive.

---

## 🛠 Installation et Démarrage

### Prérequis

* Python 3.8 ou supérieur
* Pip (gestionnaire de paquets Python)

### 1. Cloner le projet

```bash
git clone https://github.com/votre-repo/dk-dashboard.git
cd groupe-03-deadkillerz
```

### 2. Créer un environnement virtuel (recommandé)

```bash
# Windows/Mac/Linux
python -m venv venv
venv\Scripts\activate

```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt

```

### 4. Initialisation de la Base de Données

Le fichier `main.py` contient une fonction `ensure_project_tables()` qui crée automatiquement les tables SQLite manquantes au premier lancement. Aucune action manuelle n'est requise.
Cependant le projet contient une base de donnée pré-chargée avec un utilisateur Administrateur : Admin (email: `admin@a.a`; mot de pass: `1234`)

### 5. Lancer l'application

```bash
python main.py

```

L'application sera accessible à l'adresse : `http://127.0.0.1:5000`

> **Note de sécurité** : Pour un déploiement en production, changez la `SECRET_KEY` dans `main.py` et désactivez `debug=True`.

---

## Modélisation de la Base de Données

L'application utilise **SQLite** (`static/dk_bdd.db`). Voici le schéma relationnel déduit du code source.

### Schéma Entité-Association

#### 1. `utilisateurs`

Table centrale des acteurs du système.

* `id` (PK)
* `autorisations` : Niveau d'accès (1: Intervenant, 2: CDP/Client, 3: Admin).
* `tags` : Liste de compétences (ex: "Python, Design, SEO") utilisée pour le matching.
* `valide` : Booléen (0/1) pour l'approbation du compte par un admin.

#### 2. `commandes` (Les Projets)

Représente un projet ou une mission.

* `id` (PK)
* `id_cdp` (FK -> `utilisateurs`) : Le créateur/gestionnaire du projet.
* `id_client` (FK -> `client`) : Le client final.
* `tags_intervenants` : Compétences requises pour ce projet.
* `intervenants` : Liste textuelle (emails) des utilisateurs assignés.
* `status` : draft, waiting, nego, won, finished.

#### 3. `interactions` (Le "Matching")

Stocke les actions de type "Tinder" effectuées par les CDP sur les profils.

* `swiper_id` (FK -> `utilisateurs`) : Qui a swipé.
* `target_id` (FK -> `utilisateurs`) : Qui a été swipé.
* `project_id` (FK -> `commandes`) : Pour quel projet.
* `action` : 'LIKE' ou 'PASS'.

#### 4. `messages`

Système de chat interne.

* `sender_id` / `receiver_id` (FK -> `utilisateurs`).
* `is_read` : Statut de lecture.

#### 5. `jalon` & `documents`

Tables annexes pour la gestion temporelle et documentaire.

---

## Détails Techniques

### Algorithme de Matching

Le calcul de pertinence (visible dans `/intervenants` et `/tinder`) fonctionne par intersection de sets :

1. Récupération des `tags` du projet (Besoin).
2. Récupération des `tags` de l'utilisateur (Compétence).
3. **Score (%)** = `(Tags Communs / Total Tags Projet) * 100`.
Les profils sont ensuite triés par score décroissant.

### Gestion du Thème Sombre (Dark Mode)

Le thème est géré via une classe CSS `.dark-mode` sur le `<body>`.

---

## Manuel Utilisateur

### Administrateur (Niveau 3)

* **Gestion du Site** : Valider les inscriptions, supprimer des utilisateurs, importer/exporter des utilisateurs en CSV.
* **Attribution** : Vue globale sur tous les projets. Peut voir qui a "Liké" quel candidat et valider l'attribution finale.
* **Statistiques** : Accès aux graphiques globaux (KPIs).

### Chef de Projet / Client (Niveau 2)

* **Création de Projet** : Définir un besoin, des dates et des compétences (tags).
* **Recherche (Tinder)** : Accès au module de swipe pour sélectionner des intervenants potentiels pour leurs projets.
* **Suivi** : Vue Kanban pour gérer l'avancement des négociations.

### Intervenant (Niveau 1)

* **Tableau de bord** : Voit les projets auxquels il est assigné.
* **Opportunités** : Voit le nombre de projets en attente correspondant à ses tags (compétences).
* **Chat** : Peut discuter avec les administrateurs ou CDP.
* **Documents** : Espace pour déposer CV, factures ou contrats.
