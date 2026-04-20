import sqlite3
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'dk_bdd.db')

# Suppression de l'ancienne base pour éviter les conflits
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)

c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,       -- Ajout obligatoire pour le profil
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,  -- Renommé pour correspondre au code de connexion
    tags TEXT,  -- Stocke une liste d'entiers sous forme de texte séparé par des virgules (ex: "1,2,3")
    autorisations INTEGER
)
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS client (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_complet TEXT NOT NULL,
    contact TEXT,
    secteur TEXT
)

''')

c.execute('''
    CREATE TABLE IF NOT EXISTS jalon (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    taches TEXT,  -- Stocke un dictionnaire JSON sous forme de texte (ex: '{"1": "tâche 1", "2": "tâche 2"}')
    date_limite TEXT  -- SQLite ne possède pas de type DATE natif, on utilise TEXT et on stocke les dates au format 'YYYY-MM-DD'
)
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS commandes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_intervenants INTEGER NOT NULL,
    id_client INTEGER NOT NULL,
    date_debut TEXT NOT NULL,  -- Format 'YYYY-MM-DD'
    date_fin TEXT,  -- NULL si la commande est en cours
    objets TEXT,
    tags_intervenants TEXT,  -- Stocke un dictionnaire JSON sous forme de texte (ex: '{"1": ["tag1", "tag2"]}')
    jalons_id INTEGER,
    status TEXT,
    FOREIGN KEY (id_intervenants) REFERENCES utilisateurs(id),
    FOREIGN KEY (id_client) REFERENCES client(id),
    FOREIGN KEY (jalons_id) REFERENCES jalon(id)
)
''')

c.execute(''' 
INSERT INTO utilisateurs (nom, email, password, tags, autorisations)
VALUES
    ('Alice', 'alice@example.com', 'secure123', '1,2,3', 2),
    ('Bob', 'bob@example.com', 'bobpass456', '2,4', 1),
    ('Charlie', 'charlie@example.com', 'charlie789', '1,3,5', 3),
    ('David', 'david@example.com', 'davidpass123', '3,4,6', 2),
    ('Eve', 'eve@example.com', 'evepass789', '2,5', 1);
''')

c.execute('''
INSERT INTO client (nom_complet, contact, secteur)
VALUES
    ('Entreprise A', 'contact@entreprisea.com', 'Informatique'),
    ('Société B', '0123456789', 'Marketing'),
    ('Client C', 'contact@clientc.fr', 'Finance'),
    ('Association D', '0987654321', 'Éducation');
 ''')

c.execute('''
INSERT INTO jalon (nom, taches, date_limite)
VALUES
    ('Livraison Phase 1', '{"1": "Développer l''API", "2": "Tester l''API"}', '2025-06-30'),
    ('Réunion de suivi', '{"3": "Préparer le rapport", "1": "Envoyer le rapport"}', '2025-07-15'),
    ('Livraison Finale', '{"1": "Déploiement", "2": "Former les utilisateurs"}', '2025-08-31');
 ''')

c.execute('''
INSERT INTO commandes (id_intervenants, id_client, date_debut, date_fin, objets, tags_intervenants, jalons_id, status)
VALUES
    (1, 1, '2025-01-15', '2025-06-30', 'Développement d''une API', '{"1": ["Python", "Flask"]}', 1, 'won'),
    (2, 2, '2025-02-01', NULL, 'Création d''un site web', '{"2": ["HTML", "CSS"]}', 2, 'draft'),
    (3, 3, '2025-03-10', '2025-07-15', 'Optimisation de base de données', '{"3": ["SQL", "PostgreSQL"]}', 2, 'nego'), 
    (4, 4, '2025-04-05', NULL, 'Formation utilisateurs', '{"4": ["Communication", "Pédagogie"]}', 3, 'waiting');
 ''')
#a deux doigts du cancel..

# Valider les modifications
conn.commit()

# Fermer la connexion
conn.close()

print(f"Base de données (re)créée avec succès dans : {db_path}")