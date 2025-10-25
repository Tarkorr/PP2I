# Développement d'une application web d'aide à la prospection


## Contexte du projet

TNS (https://tnservices.fr/) est la junior entreprise de TELECOM Nancy, une association étudiante qui réalise des projets informatiques pour des clients externes. Dans le cadre de son développement, TNS souhaite créer une application web interne pour gérer la prospection commerciale et le suivi des projets. L'objectif est de faciliter la gestion des clients, des projets et des intervenants, tout en assurant la conformité avec le RGPD. En les aidant dans ce projet, vous les/vous aiderez à trouver des missions pour acquérir de l'expérience ! En plus, ce projet vous permettra de découvrir le développement web pour un cas concret et représentera un bon point dans votre CV. De plus, ils sont prêts à assurer un suivi pour vous aider à réussir ce projet !


## Contexte pédagogique

Ce projet vise à placer les élèves-ingénieurs en situation de développement complet d’un système informatique intégrant : 

- la conception algorithmique,
- la modélisation et l’implémentation de données,
- la réalisation d’un service web avec front-end et back-end,
- la gestion de projet collaboratif.

### Objectifs d'apprentissage

Volet Gestion de projet : 

- Définir les besoins fonctionnels et techniques à partir d’un cahier des charges simplifié.
- Planifier et suivre un projet (outils agiles, gestion des versions, documentation).
- Utiliser des outils collaboratifs (Git, GitLab, Trello/Jira, Wiki, etc.).
- Rédiger et présenter un rapport de projet clair et professionnel.

Volet Algorithmique : 

- Analyser un problème et identifier les algorithmes pertinents.
- Évaluer la complexité et la correction des solutions envisagées.
- Implémenter et tester des algorithmes efficaces en Python.

Volet Base de données : 

- Concevoir un modèle de données relationnel (MCD, MLD).
- Normaliser et documenter le schéma de la base.
- Implémenter et interroger une base relationnelle (PostgreSQL/MySQL/SQLite).
- Gérer les interactions entre la base et l’application via une API.

Volet Web : 

- Concevoir une architecture client-serveur.
- Développer une API REST avec Flask.
- Concevoir un front-end léger (HTML/CSS/JS ou framework minimal).
- Connecter le front-end à l’API.
- Déployer et tester une application web fonctionnelle.


## Périmètre fonctionnel

| Fonctionnalité | Description synthétique | Difficulté | Obligation |
| --------------- | ----------------------- | ----------- | ---------- |
| Gestion des études | Créer un projet lié à un client avec statut et dates | 🟢 Facile | ✅ Obligatoire |
| Gestion des intervenants | Créer / lire / modifier / supprimer un intervenant (CRUD/RGPD) | 🟢 Facile | ✅ Obligatoire |
| Tableau de bord | Page d'accueil listant les clients et l'état des projets | 🟢 Facile | ✅ Obligatoire |
| Gestion de projets | Création de jalons pour un projet avec dates et statut (format Kanban) | 🟢 Facile | ✅ Obligatoire |
| Gestion des clients/prospects | Créer / lire / modifier / supprimer un client (CRUD/RGPD) avec champs d'informations le plus exhaustif possible (nom, contact, secteur...) + historique de contact avec lui (qui, quand ?) | 🟢 Facile | ✅ Obligatoire |
| Historique des missions réalisées | Une page qui permet d'accéder à toutes les missions que la junior a réalisées avec les documents correspondants (import, export CSV) | 🟢 Facile | ✅ Obligatoire |
| Authentification simple | Formulaire de connexion avec gestion de session (mots de passe en clair autorisés) | 🟢 Facile | ✅ Obligatoire |
| Historique des interactions | Associer plusieurs interactions textuelles datées à un client | 🟡 Moyen | ✅ Obligatoire |
| Import/Export CSV de clients | Ajouter plusieurs clients via un fichier CSV ou les exporter | 🟡 Moyen | ✅ Obligatoire |
| Tests unitaires | Couvrir les fonctionnalités principales avec des tests automatisés (pytest) | 🟡 Moyen | ✅ Obligatoire |
| Profil d'intervenant | Page personnelle avec documents, compétences et disponibilité | 🟡 Moyen | ✅ Obligatoire  |
| Algorithme de matching | Suggérer des intervenants pour un projet en fonction de leurs compétences et portfolio | 🟡 Moyen | ✅ Obligatoire |
| Recherche texte | Champ de recherche filtrant les clients par nom ou secteur | 🟡 Moyen | 🔸 Optionnel |
| Gestion des autorisations | Chaque compte a un rôle associé qui donne certaines permissions ou non (Président, Chef de projet, DSI...) | 🟡 Moyen | 🔸 Optionnel |
| Authentification renforcée | Mots de passe chiffrés | 🟢 Facile | ✅ Obligatoire |
| Page RGPD | Page donnant les données stockées sur un client/intervenant avec possibilité de suppression ou portabilité | 🟡 Moyen | 🔸 Optionnel |
| Page tinder-like pour savoir quelle prochaine entreprise contacter | Interface utilisateur pour "swiper" entre les entreprises suggérées par l'algorithme de matching et choisir celles à contacter | 🟡 Moyen | 🔸 Optionnel |
| Ajout de clients dans la BDD par API | Recherche de prospects potentiels avec une API qui récupère les données de l'entreprise (OpenStreetMap... attention aux licences d'usage commercial) | 🔴 Difficile | ⭕️ Bonus |
| Utilisation de PostgreSQL | Passage de SQLite à PostgreSQL pour la base de données | 🟡 Moyen | ⭕️ Bonus |
| Intégration continue | Mise en place d'un pipeline CI/CD (GitHub Actions, GitLab CI) pour tests et déploiement automatisé | 🟡 Moyen | ⭕️ Bonus |
| Docker | Conteneurisation de l'application avec Docker pour faciliter le déploiement | 🟡 Moyen | ⭕️ Bonus |
| Page de statistiques | Graphiques sur l'activité de la junior (nombre de clients, projets en cours, répartition par secteur...) | 🟡 Moyen | ⭕️ Bonus |
| Authentification Google OAuth | Connexion via Google Workspace | 🔴 Difficile | ⭕️ Bonus |
| Utilisation de Google Drive | Stocker les documents liés aux clients et aux intervenants sur Google Drive (API Google Drive) | 🔴 Difficile | ⭕️ Bonus |
| Utilisation avancée de SQLAlchemy | Utilisation de fonctionnalités avancées de SQLAlchemy (migrations, relations complexes, requêtes optimisées) | 🔴 Difficile | ⭕️ Bonus |
| Carte interactive (Leaflet) | Affichage des clients sur une carte en utilisant latitude / longitude | 🔴 Difficile | ⭕️ Bonus |


### Légende des niveaux de difficulté
- 🟢 **Facile** : peut être réalisé dès les premières séances avec l'appui du tutoriel Flask.
- 🟡 **Moyen** : nécessite de combiner plusieurs notions (formulaires + relations BDD par exemple).
- 🔴 **Difficile** : demande des recherches supplémentaires ou l'utilisation d'API externes.
- ✅ **Obligatoire** : à livrer pour valider le projet.
- 🔸 **Optionnel** : à choisir si le temps le permet ou pour aller plus loin.
- ⭕️ **Bonus** : réservé aux équipes très à l'aise.


## Architecture et contraintes techniques

**Framework** : Flask + Jinja2.

**Base de données** : SQLite (par défaut). Passage à PostgreSQL = 🟡 Moyen, ⭕️ Bonus.

**Authentification** : Flask-Login conseillé (si non utilisé, gérer sessions manuellement).

**Interface** : HTML/CSS minimal. JavaScript optionnel.

**Gestion des données test** : minimum 20 clients et 10 interactions en base pour la démonstration.


## Jalons indicatifs

**Jalon 1 : Mise en place et bases**  
- Objectifs : Formation Flask, dépôt Git, authentification simple, modélisation BDD pour clients/prospects.  
- Livrables : Application de base fonctionnelle avec base de données pour clients contactés.

**Jalon 2 : Gestion clients et projets**  
- Objectifs : CRUD (*Create, Read, Update, Delete*) clients, projets, intervenants, historique...  
- Livrables : Interfaces de gestion et tableau de bord.

**Jalon 3 : Finalisation**  
- Objectifs : Tests, fonctionnalités avancées, documentation.  
- Livrables : Application complète avec démo.


## Développement incrémental

Il est vivement recommandé à ce que le groupe adopte une stratégie de développement incrémentale.

L'idée est donc de planifier et de définir des "incréments" ou de petites unités fonctionnelles du jeu (ou de ces composants). Cela permet de se concentrer sur une petite section du jeu à la fois et d'être toujours capable d'avoir une version fonctionnelle du jeu complet. Cela permet également d'éviter l'effet tunnel : de commencer le développement de beaucoup de fonctionnalités et de n'avoir finalement rien ou pas grand-chose de fonctionnel à montrer à la fin du projet.


## Rendu final

**Code source** : Livraison du code source complet et proprement organisé (ex : `app.py`, `models.py`, `routes.py`, `forms.py`, `templates/`) 

**Tests unitaires** : Un ensemble de tests unitaires accompagnant le code source.

**Documentations** : Comprend un guide d'installation, un court manuel utilisateur, une description des détails techniques et notamment de la modélisation de la base de données relationnelles.

**État de l'art** : Rapport de l’état de l’art sur les algorithmes d’intelligence artificielle applicables et appliqués.

**Gestion de projet** : Comprend tous les éléments de gestion de projet que vous aurez produits (fiche de projet, comptes-rendus de réunion, planification et répartition des tâches, analyse post-mortem des efforts individuels et de l'atteinte des objectifs, etc.).


**Tous ces éléments seront déposés de manière organisée dans le dépôt git de votre projet.**


## Soutenance et date de rendu

Le projet est à rendre pour le **mercredi 7 janvier 2026** à 22 heures au plus tard.

Des soutenances de groupes de projet seront organisées la deuxième ou troisième semaine de janvier.

Votre projet fera l'objet d'une démonstration devant un jury composé d'au moins 2 membres de l’équipe pédagogique (et peut-être d'un membre de TNS). Durant cette soutenance, vous serez jugés sur votre démonstration de l'application et votre capacité à expliquer votre projet et son fonctionnement. Chaque membre du groupe devra être présent lors de soutenance et **participer activement**.

*Toute personne ne se présentant pas à la soutenance sera considérée comme démissionnaire de l'UE et en conséquence, ne pourra pas la valider pour l’année universitaire 2025-2026.*

Il est attendu que chaque membre du groupe ait contribué **à plusieurs parties fonctionnelles du code** (il ne s'agit pas d'avoir uniquement corrigé quelques lignes par ci et par là).

Lors de la soutenance, il est attendu :
- que le groupe réalise une démonstration fonctionnelle de l'application qu'il a réalisée sur une dizaine de minutes. L'objectif est de présenter les fonctionnalités et les spécificités de votre application. Il est conseillé de scénariser cette démonstration (pas une pièce de théâtre, mais de dérouler un scénario utilisateur) ;
- puis qu'il présente (supports à l'appui) en 5 minutes maximum la gestion de projet (organisation/répartition des tâches, planning prévisionnel/réalisé).

Cette démonstration/présentation sera suivie d'un échange avec le jury pendant environ 10 minutes.

En résumé : un créneau de 30 minutes sera dédié à chaque projet :
- 10 min de démonstration de votre réalisation
- 5 min de présentation de la gestion de projet
- 10 min de questions
- 5 min délibérations.


## Critères d'évaluation

Pour l'évaluation, les points suivants seront pris en considération :

- Respect du périmètre obligatoire et qualité de l'implémentation.
- Qualité (adéquation, correction, performance, etc.) des algorithmes mis en œuvre.
- Qualité du modèle relationnel proposé et respect de la 3ème forme normale.
- Respect des bonnes pratiques de programmation (structure du code, lisibilité, commentaires, structure cohérente).
- Tests et gestion des erreurs (robustesse de l’application).
- Valeur ajoutée via les fonctionnalités optionnelles choisies.
- Gestion de projet (répartition des tâches, utilisation d'un tableau Kanban ou équivalent).
- Qualité de la démonstration finale et de la documentation fournie.


## Mieux comprendre le projet

Pour mieux comprendre les besoins et le contexte, vous pouvez contacter l'équipe pédagogique ou les membres de TNS pour leur poser des questions à tout moment. 
N'hésitez pas à demander des précisions sur les fonctionnalités ou à proposer des idées d'amélioration. Vous pouvez échanger avec nTNSous dans le local, par mail ou par Discord ([https://discord.gg/gHEfQrUdkg](https://discord.gg/gHEfQrUdkg)). 
L'équipe est là pour vous aider à réussir ce projet !


## Fraude, tricherie et plagiat

Ne trichez pas ! Ne copiez pas ! Ne plagiez pas ! Si vous le faites, vous serez lourdement sanctionnés. Nous ne ferons pas de distinction entre copieur et copié. Vous n'avez pas de (bonnes) raisons de copier. De même, vous ne devez pas utiliser de solution clé en main trouvée sur internet.

Par tricher, nous entendons notamment :
- Rendre le travail d’un collègue en y apposant votre nom ;
- Obtenir un code, une solution par un moteur de recherche (ou une IA) et la rendre sous votre nom ;
- Récupérer du code et ne changer que les noms de variables et fonctions ou leur ordre avant de les présenter sous votre nom 
- Autoriser consciemment ou inconsciemment un collègue à s'approprier votre travail personnel. Assurez-vous particulièrement que votre projet et ses différentes copies locales ne soient lisibles que par vous et les membres de votre groupe.

Nous encourageons les séances de *brainstorming* et de discussion entre les élèves sur le projet. C’est une démarche naturelle et saine comme vous la rencontrerez dans votre vie professionnelle. Si les réflexions communes sont fortement recommandées, vous ne pouvez rendre que du code et des documents écrits par vous-même. Vous indiquerez notamment dans votre rapport toutes vos sources (comme les sites internet que vous auriez consultés), en indiquant brièvement ce que vous en avez retenu.
Il est quasi certain que nous détections les tricheries. En effet, les rapports et les codes sont systématiquement soumis à des outils de détection de plagiat et de copie. Il existe spécifiquement des outils de détection de manipulation de code extraordinaire mis à disposition par l’Université de Stanford, tels que `MOSS` (https://theory.stanford.edu/~aiken/moss/) ou `compare50` (https://cs50.readthedocs.io/projects/compare50/). De plus, chacun a son propre style de programmation et personne ne développe la même chose de la même manière.

Puisqu'il s'agit d'un projet réalisé dans le cadre de cours avancés de programmation, nous nous attendons à ce que vous soyez capable d'apprendre à déboguer des programmes par vous-même. Par exemple, demander à un autre élève de regarder directement votre code et de donner des suggestions d'amélioration commence à devenir un peu délicat au niveau éthique.

Si vous rencontrez des difficultés pour terminer une tâche, veuillez contacter l'un de vos enseignants afin que nous puissions vous aider. Nous préférons de loin passer du temps à vous aider plutôt que de traiter des cas de fraudes.

