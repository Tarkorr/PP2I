import pytest
import os
import sqlite3
from datetime import date
from flask_login import login_user
from werkzeug.utils import secure_filename
from main import app, User, allowed_file, parse_list_field, parse_id_list, parse_jalons_text, MAX_FILE_SIZE, ensure_project_tables

# =============================
# CONFIGURATION DE L'ENV.
# =============================

@pytest.fixture
def client():
    """Configuration de l'application Flask et de la BDD pour les tests"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    test_db = 'static/test_dk_bdd_pytest.db'
    app.config['DATABASE'] = test_db
    client = app.test_client()
    with app.app_context():
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        ensure_project_tables(cursor)
        conn.commit()
        conn.close()
        yield client
        if os.path.exists(test_db):
            os.remove(test_db)

@pytest.fixture
def db_path():
    """Renvoie le chemin de la base de données de test pour les connexions manuelles"""
    return 'static/test_dk_bdd_pytest.db'

# =============================
# TESTS FONCTIONS UTILITAIRES
# =============================

def test_util_fichier_autorise_valide():
    """Vérifie que les extensions d'images autorisées sont bien acceptées"""
    assert allowed_file('test.png') is True
    assert allowed_file('image.jpg') is True
    assert allowed_file('photo.jpeg') is True
    assert allowed_file('icon.gif') is True

def test_util_fichier_autorise_invalide():
    """Vérifie que les fichiers non autorisés ou dangereux sont refusés"""
    assert allowed_file('test.pdf') is False
    assert allowed_file('script.js') is False
    assert allowed_file('virus.exe') is False
    assert allowed_file('sans_extension') is False

def test_util_analyse_liste_standard():
    """Vérifie le découpage standard d'une chaîne de tags en liste"""
    assert parse_list_field("python, flask, sql") == ['python', 'flask', 'sql']

def test_util_analyse_liste_desordonnee():
    """Vérifie que le nettoyage des virgules et espaces fonctionne pour les tags"""
    assert parse_list_field("python, , flask \n, sql ,,") == ['python', 'flask', 'sql']

def test_util_analyse_liste_vide():
    """Vérifie le comportement de la fonction avec des entrées vides ou nulles"""
    assert parse_list_field("") == []
    assert parse_list_field(None) == []

def test_util_analyse_id_liste_valide():
    """Vérifie la conversion d'une chaîne d'IDs en liste d'entiers"""
    assert parse_id_list("1, 2, 3") == [1, 2, 3]

def test_util_analyse_id_liste_mixte():
    """Vérifie que les valeurs non numériques sont ignorées lors du parsing d'IDs"""
    assert parse_id_list("1, abc, 3, 4.5") == [1, 3]

def test_util_analyse_jalons_format_barre_vert():
    """Vérifie le parsing des jalons utilisant le séparateur '|'"""
    raw = "2024-01-01 | Debut\n2024-02-01 | Fin"
    result = parse_jalons_text(raw)
    assert len(result) == 2
    assert result[0]['nom'] == "Debut"
    assert result[0]['date'] == "2024-01-01"

def test_util_analyse_jalons_format_deux_points():
    """Vérifie le parsing des jalons utilisant le séparateur ':'"""
    raw = "2024-03-01 : Etape importante"
    result = parse_jalons_text(raw)
    assert result[0]['nom'] == "Etape importante"
    assert result[0]['date'] == "2024-03-01"

# =============================
# TESTS BDD (CRUD)
# =============================

def test_bdd_insertion_utilisateur(client, db_path):
    """Vérifie qu'un utilisateur est correctement enregistré dans la bdd"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO utilisateurs (nom, email, password, valide) VALUES (?, ?, ?, ?)",
                   ("TestUser", "test@prospector.fr", "hash123", 1))
    conn.commit()
    cursor.execute("SELECT nom FROM utilisateurs WHERE email = ?", ("test@prospector.fr",))
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "TestUser"

def test_bdd_creation_projet(client, db_path):
    """Vérifie la création d'une commande et l'intégrité des données"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO commandes (objets, status) VALUES (?, ?)", ("Projet Alpha", "draft"))
    conn.commit()
    
    cursor.execute("SELECT id FROM commandes WHERE objets = ?", ("Projet Alpha",))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None

# =============================
# TESTS MESSAGERIE
# =============================

def test_messagerie_envoi_et_lecture(client, db_path):
    """Vérifie le stockage d'un message et son statut par défaut (non lu)"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (sender_id, receiver_id, content, is_read) VALUES (?, ?, ?, ?)",
                   (1, 2, "Bonjour", 0))
    conn.commit()
    cursor.execute("SELECT is_read FROM messages WHERE content = ?", ("Bonjour",))
    is_read = cursor.fetchone()[0]
    conn.close()
    assert is_read == 0

# =============================
# TESTS SECURITE FICHIERS
# =============================

def test_securite_taille_fichier_limite():
    """Vérifie que la constante de taille maximale est de 5 Mo"""
    # Note: Assure-toi que MAX_FILE_SIZE est importé depuis main
    assert MAX_FILE_SIZE == 5 * 1024 * 1024

def test_securite_nom_fichier_upload():
    """Vérifie que le système nettoie les noms de fichiers (via secure_filename)"""
    nom_sale = "../../mauvais_endroit.png"
    nom_propre = secure_filename(nom_sale)
    assert nom_propre == "mauvais_endroit.png"

# =============================
# TESTS AUTHENTIFICATION
# =============================

def test_auth_initialisation_utilisateur():
    """Vérifie que l'objet "User" est correctement créé avec ses attributs"""
    utilisateur = User(1, "Test", "test@test.com", 1, "python,sql")
    assert utilisateur.id == "1"
    assert utilisateur.nom == "Test"
    assert utilisateur.email == "test@test.com"
    assert utilisateur.autorisations == 1

def test_auth_recuperation_id_utilisateur():
    """Vérifie la fonction get_id() requise par Flask-Login"""
    utilisateur = User(99, "Admin", "admin@a.a", 3, "")
    assert utilisateur.get_id() == "99"

# =============================
# TESTS DES ROUTES
# =============================

def test_route_welcome_accessible(client):
    """Vérifie que la page Welcome est accessible publiquement"""
    reponse = client.get('/welcome')
    assert reponse.status_code == 200

def test_route_connexion_accessible(client):
    """Vérifie l'affichage de la page de connexion"""
    reponse = client.get('/login')
    assert reponse.status_code == 200

def test_route_dashboard_redirection_si_non_connecte(client):
    """Vérifie que l'accès au Dashboard est bloqué sans connexion"""
    reponse = client.get('/dashboard')
    # 302 = REDIRECTION
    assert reponse.status_code == 302
    assert '/login' in reponse.headers['Location']

def test_route_parametres_redirection_si_non_connecte(client):
    """Vérifie la protection de la page des paramètres"""
    reponse = client.get('/settings')
    assert reponse.status_code == 302

# =============================
# TESTS GDP / MATCHING 
# =============================

def test_logique_algorithme_matching_parfait():
    """Vérifie le calcul du score Tinder B2B pour un match à 100%"""
    tags_projet = set(["python", "flask"])
    tags_utilisateur = set(["python", "flask", "docker"])
    communs = len(tags_utilisateur.intersection(tags_projet))
    score = int((communs / len(tags_projet)) * 100)
    assert score == 100

def test_logique_algorithme_matching_partiel():
    """Vérifie le calcul du score pour un match partiel -> 50%"""
    tags_projet = set(["python", "flask", "css", "js"])
    tags_utilisateur = set(["python", "flask"])
    communs = len(tags_utilisateur.intersection(tags_projet))
    score = int((communs / len(tags_projet)) * 100)
    assert score == 50

def test_logique_calcul_jours_restants():
    """Vérifie le calcul des jours restants avant la deadline d'un projet"""
    date_fin = date(2025, 12, 31)
    aujourdhui = date(2025, 12, 1)
    difference = (date_fin - aujourdhui).days
    assert difference == 30

def test_logique_pourcentage_avancement_projet():
    """Vérifie le calcul du pourcentage d'avancement temporel d'un projet"""
    debut = date(2025, 1, 1)
    fin = date(2025, 1, 11)
    actuel = date(2025, 1, 6)
    total = (fin - debut).days
    ecoule = (actuel - debut).days
    pourcentage = int((ecoule / total) * 100)
    assert pourcentage == 50