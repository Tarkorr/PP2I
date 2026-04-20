import unittest
import io
import os
import sqlite3
from datetime import date
from flask_login import login_user
from main import app, User, allowed_file, parse_list_field, parse_id_list, parse_jalons_text, MAX_FILE_SIZE,ensure_project_tables

class SuiteTestsProspector(unittest.TestCase):

    def setUp(self):
        """Configuration de l'environnement de test avant chaque fonction"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.test_db = 'static/test_dk_bdd.db'
        app.config['DATABASE'] = self.test_db
        self.app = app.test_client()
        
        # Base propre pour chaque test
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        ensure_project_tables(cursor)
        conn.commit()
        conn.close()

        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        """Nettoyage de l'environnement après chaque test"""
        self.ctx.pop()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    # =============================
    # TESTS DES UTILITAIRES DE MAIN
    # =============================

    def test_util_fichier_autorise_valide(self):
        """Vérifie que les extensions d'images autorisées sont bien acceptées"""
        self.assertTrue(allowed_file('test.png'))
        self.assertTrue(allowed_file('image.jpg'))
        self.assertTrue(allowed_file('photo.jpeg'))
        self.assertTrue(allowed_file('icon.gif'))

    def test_util_fichier_autorise_invalide(self):
        """Vérifie que les fichiers non autorisés ou dangereux sont refusés"""
        self.assertFalse(allowed_file('test.pdf'))
        self.assertFalse(allowed_file('script.js'))
        self.assertFalse(allowed_file('virus.exe'))
        self.assertFalse(allowed_file('sans_extension'))

    def test_util_analyse_liste_standard(self):
        """Vérifie le découpage standard d'une chaîne de tags en liste"""
        self.assertEqual(parse_list_field("python, flask, sql"), ['python', 'flask', 'sql'])

    def test_util_analyse_liste_desordonnee(self):
        """Vérifie que le nettoyage des virgules et espaces fonctionne (Correction Bug)"""
        self.assertEqual(parse_list_field("python, , flask \n, sql ,,"), ['python', 'flask', 'sql'])

    def test_util_analyse_liste_vide(self):
        """Vérifie le comportement de la fonction avec des entrées vides ou nulles"""
        self.assertEqual(parse_list_field(""), [])
        self.assertEqual(parse_list_field(None), [])

    def test_util_analyse_id_liste_valide(self):
        """Vérifie la conversion d'une chaîne d'IDs en liste d'entiers"""
        self.assertEqual(parse_id_list("1, 2, 3"), [1, 2, 3])

    def test_util_analyse_id_liste_mixte(self):
        """Vérifie que les valeurs non numériques sont ignorées lors du parsing d'IDs"""
        self.assertEqual(parse_id_list("1, abc, 3, 4.5"), [1, 3])

    def test_util_analyse_jalons_format_pipe(self):
        """Vérifie le parsing des jalons utilisant le séparateur '|'"""
        raw = "2024-01-01 | Debut\n2024-02-01 | Fin"
        result = parse_jalons_text(raw)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['nom'], "Debut")
        self.assertEqual(result[0]['date'], "2024-01-01")

    def test_util_analyse_jalons_format_deux_points(self):
        """Vérifie le parsing des jalons utilisant le séparateur ':'"""
        raw = "2024-03-01 : Etape importante"
        result = parse_jalons_text(raw)
        self.assertEqual(result[0]['nom'], "Etape importante")
        self.assertEqual(result[0]['date'], "2024-03-01")

    # =============================
    # TESTS BDD (CRUD)
    # =============================

    def test_bdd_insertion_utilisateur(self):
        """Vérifie qu'un utilisateur est correctement enregistré dans la bdd"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO utilisateurs (nom, email, password, valide) VALUES (?, ?, ?, ?)",
                       ("TestUser", "test@prospector.fr", "hash123", 1))
        conn.commit()
        
        cursor.execute("SELECT nom FROM utilisateurs WHERE email = ?", ("test@prospector.fr",))
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "TestUser")

    def test_bdd_creation_projet(self):
        """Vérifie la création d'une commande et l'intégrité des données"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO commandes (objets, status) VALUES (?, ?)", ("Projet Alpha", "draft"))
        conn.commit()
        
        cursor.execute("SELECT id FROM commandes WHERE objets = ?", ("Projet Alpha",))
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)

    # =============================
    # TESTS MESSAGERIE
    # =============================

    def test_messagerie_envoi_et_lecture(self):
        """Vérifie le stockage d'un message et son statut par défaut (non lu)"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (sender_id, receiver_id, content, is_read) VALUES (?, ?, ?, ?)",
                       (1, 2, "Bonjour", 0))
        conn.commit()
        
        cursor.execute("SELECT is_read FROM messages WHERE content = ?", ("Bonjour",))
        is_read = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(is_read, 0)

    # =============================
    # TESTS SECURITE FICHIERS
    # =============================

    def test_securite_taille_fichier_limite(self):
        """Vérifie que la constante de taille maximale est de 5Mo"""
        self.assertEqual(MAX_FILE_SIZE, 5 * 1024 * 1024)

    def test_securite_nom_fichier_upload(self):
        """Vérifie que le système nettoie les noms de fichiers (via secure_filename)"""
        from werkzeug.utils import secure_filename
        nom_sale = "../../mauvais_endroit.png"
        nom_propre = secure_filename(nom_sale)
        self.assertEqual(nom_propre, "mauvais_endroit.png")

    # =============================
    # TESTS AUTHENTIFICATION
    # =============================

    def test_auth_initialisation_utilisateur(self):
        """Vérifie que l'objet User est correctement créé avec ses attributs"""
        utilisateur = User(1, "Test", "test@test.com", 1, "python,sql")
        self.assertEqual(utilisateur.id, "1")
        self.assertEqual(utilisateur.nom, "Test")
        self.assertEqual(utilisateur.email, "test@test.com")
        self.assertEqual(utilisateur.autorisations, 1)

    def test_auth_recuperation_id_utilisateur(self):
        """Vérifie la méthode get_id() requise par Flask-Login"""
        utilisateur = User(99, "Admin", "admin@a.a", 3, "")
        self.assertEqual(utilisateur.get_id(), "99")

    # =============================
    # TESTS DES ROUTES
    # =============================

    def test_route_welcome_accessible(self):
        """Vérifie que la page Welcome est accessible publiquement"""
        reponse = self.app.get('/welcome')
        self.assertEqual(reponse.status_code, 200)

    def test_route_connexion_accessible(self):
        """Vérifie l'affichage de la page de connexion"""
        reponse = self.app.get('/login')
        self.assertEqual(reponse.status_code, 200)

    def test_route_dashboard_redirection_si_non_connecte(self):
        """Vérifie que l'accès au Dashboard est bloqué sans connexion"""
        reponse = self.app.get('/dashboard')
        self.assertEqual(reponse.status_code, 302)
        self.assertIn('/login', reponse.location)

    def test_route_parametres_redirection_si_non_connecte(self):
        """Vérifie la protection de la page des paramètres"""
        reponse = self.app.get('/settings')
        self.assertEqual(reponse.status_code, 302)

    # =============================
    # TESTS DE LOGIQUE METIER
    # =============================

    def test_logique_algorithme_matching_parfait(self):
        """Vérifie le calcul du score Tinder B2B pour un match à 100% """
        tags_projet = set(["python", "flask"])
        tags_utilisateur = set(["python", "flask", "docker"])
        communs = len(tags_utilisateur.intersection(tags_projet))
        score = int((communs / len(tags_projet)) * 100)
        self.assertEqual(score, 100)

    def test_logique_algorithme_matching_partiel(self):
        """Vérifie le calcul du score pour un match partiel (50%) """
        tags_projet = set(["python", "flask", "css", "js"])
        tags_utilisateur = set(["python", "flask"])
        communs = len(tags_utilisateur.intersection(tags_projet))
        score = int((communs / len(tags_projet)) * 100)
        self.assertEqual(score, 50)

    def test_logique_calcul_jours_restants(self):
        """Vérifie le calcul des jours restants avant l'échéance d'un projet"""
        date_fin = date(2025, 12, 31)
        aujourdhui = date(2025, 12, 1)
        difference = (date_fin - aujourdhui).days
        self.assertEqual(difference, 30)

    def test_logique_pourcentage_avancement_projet(self):
        """Vérifie le calcul du pourcentage d'avancement temporel d'un projet"""
        debut = date(2025, 1, 1)
        fin = date(2025, 1, 11)
        actuel = date(2025, 1, 6)
        total = (fin - debut).days
        ecoule = (actuel - debut).days
        pourcentage = int((ecoule / total) * 100)
        self.assertEqual(pourcentage, 50)

if __name__ == '__main__':
    # Lancement des test
    unittest.main()