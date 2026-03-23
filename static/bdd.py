from flask import Flask, g
import sqlite3

# Nom du fichier de la base de données SQLite
DATABASE = 'data/dk_bdd.db'

# Initialisation de l'application Flask
app = Flask(__name__)

# Fonction pour obtenir une connexion à la base de données
def get_db():
    # Vérifie si une connexion existe déjà dans le contexte de l'application
    db = getattr(g, '_database', None)
    if db is None:
        # Si aucune connexion n'existe, crée une nouvelle connexion
        db = g._database = sqlite3.connect(DATABASE)
    return db

    """
    CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    nom TEXT NOT NULL,
    chemin TEXT NOT NULL,
    date_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES utilisateurs(id)
);
    """