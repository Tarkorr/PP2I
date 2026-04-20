from flask             import Flask, request, render_template, redirect, url_for, flash, jsonify, abort, send_file
from flask_login       import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from collections       import Counter
from datetime          import datetime, date
from urllib.parse      import urlencode
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils    import secure_filename
import csv
import os
import sqlite3
import hashlib
import io

DATABASE           = 'static/dk_bdd.db'
UPLOAD_FOLDER      = 'static/img'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE      = 5 * 1024 * 1024  # 5 Mo
UPLOAD_FOLDER      = 'static/uploads/documents'

app            = Flask(__name__)
app.secret_key = "9f6f6bf0b2ff2c66ecfecce096f363dae01313d84891368c423687155451b778"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "danger"

# =============================
# FONCTIONS UTILITAIRES
# =============================
class User(UserMixin):
    def __init__(self, id, nom, email, autorisations, tags):
        self.id = str(id)
        self.nom = nom
        self.email = email
        self.autorisations = autorisations
        self.tags = tags
        self.gravatar_url = get_avatar(email)
        self.devise = "eur"
        self.langue = "fr"


@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nom, email, autorisations, tags FROM utilisateurs WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return User(id=row[0], nom=row[1], email=row[2], autorisations=row[3], tags=row[4])
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_avatar(email, size=80, default='identicon', rating='g'):
    """
    Génère l'URL de l'avatar pour un email donné.
    Vérifie d'abord dans la BDD s'il existe un avatar personnalisé.
    Sinon, retourne l'URL Gravatar.
    """
    avatar_custom = None
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT avatar FROM utilisateurs WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row and row[0]:
                avatar_custom = row[0]
    except Exception:
        pass

    if avatar_custom:
        return url_for('static', filename=f'img/{avatar_custom}')

    email_clean = email.strip().lower()
    email_hash = hashlib.sha256(email_clean.encode('utf-8')).hexdigest()
    query_params = urlencode({
        's': str(size),
        'd': default,
        'r': rating
    })
    return f"https://www.gravatar.com/avatar/{email_hash}?{query_params}"

def parse_list_field(raw_value):
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.replace("\n", ",").split(",") if item.strip()]

def parse_id_list(raw_value):
    if not raw_value:
        return []
    ids = []
    for item in raw_value.replace("\n", ",").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.append(int(item))
        except ValueError:
            continue
    return ids

def parse_jalons_text(raw_value):
    jalons = []
    for line in (raw_value or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            date_part, nom = line.split("|", 1)
        elif ":" in line:
            date_part, nom = line.split(":", 1)
        else:
            date_part, nom = "", line
        jalons.append({
            "date": date_part.strip(),
            "nom": nom.strip()
        })
    return jalons

def get_jalon_assignations(cursor, jalon_ids):
    if not jalon_ids:
        return {}
    placeholder = ",".join(["?"] * len(jalon_ids))
    cursor.execute(
        f"""
        SELECT ji.jalon_id, ji.intervenant_id, ji.tache, u.email, u.nom
        FROM jalon_intervenant ji
        LEFT JOIN utilisateurs u ON ji.intervenant_id = u.id
        WHERE ji.jalon_id IN ({placeholder})
        """,
        jalon_ids,
    )
    mapping = {jid: [] for jid in jalon_ids}
    for row in cursor.fetchall():
        mapping[row[0]].append({
            "intervenant_id": row[1],
            "tache": row[2] or "",
            "email": row[3],
            "nom": row[4],
        })
    return mapping

def verify_password_hash(stored_hash, password):
    if not stored_hash:
        return False, None
    if stored_hash.startswith("scrypt") and not hasattr(hashlib, "scrypt"):
        return False, "Votre mot de passe utilise un format non supporté sur ce serveur. Merci de le réinitialiser."
    try:
        return check_password_hash(stored_hash, password), None
    except AttributeError as exc:
        if "scrypt" in str(exc).lower():
            return False, "Votre mot de passe utilise un format non supporté sur ce serveur. Merci de le réinitialiser."
        raise

def create_jalons_from_text(cursor, raw_value):
    jalons = parse_jalons_text(raw_value)
    jalon_ids = []
    for jalon in jalons:
        if not jalon["nom"]:
            continue
        cursor.execute(
            "INSERT INTO jalon (nom, taches, date_limite, description) VALUES (?, ?, ?, ?)",
            (jalon["nom"], "", jalon["date"] or None, None),
        )
        jalon_ids.append(cursor.lastrowid)
    return jalon_ids

def get_user_data_full_tuple(email):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nom, email, password, tags, autorisations, bio, disponibilite, langues, liens, avatar
        FROM utilisateurs WHERE email = ?
    """, (email,))
    row = cursor.fetchone() 
    conn.close()
    if row:
        user_list = list(row)
        url_avatar = get_avatar(user_list[2])
        user_list.insert(6, url_avatar)
        return tuple(user_list)
    return None

def ensure_project_tables(cursor):
    """ Vérifie que les tables sont bien présentes dans la BDD """

    # Client
    cursor.execute(
        """--sql
        CREATE TABLE IF NOT EXISTS client (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_complet TEXT,
            email TEXT,
            secteur TEXT
        )
        """
    )

    # Jalons
    cursor.execute(
        """--sql
        CREATE TABLE IF NOT EXISTS jalon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            taches TEXT,
            date_limite TEXT,
            description TEXT
        )
        """
    )

    # Utilisateurs
    cursor.execute(
        """--sql
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            tags TEXT,
            autorisations INTEGER DEFAULT 1,
            avatar TEXT,
            valide INTEGER DEFAULT 0,
            bio TEXT,
            disponibilite TEXT DEFAULT 'Disponible', 
            langues TEXT, 
            liens TEXT
        )
        """
    )

    cursor.execute(
        """--sql
        CREATE TABLE IF NOT EXISTS jalon_intervenant (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jalon_id INTEGER NOT NULL,
            intervenant_id INTEGER NOT NULL,
            tache TEXT,
            FOREIGN KEY (jalon_id) REFERENCES jalon(id),
            FOREIGN KEY (intervenant_id) REFERENCES utilisateurs(id)
        )
        """
    )

    # Commandes
    cursor.execute(
        """--sql
        CREATE TABLE IF NOT EXISTS commandes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cdp INTEGER,
            id_client INTEGER,
            date_debut TEXT,
            date_fin TEXT,
            objets TEXT,
            tags_intervenants TEXT,
            jalons_id TEXT,
            status TEXT,
            description TEXT,
            intervenants TEXT,
            FOREIGN KEY (id_cdp) REFERENCES utilisateurs(id),
            FOREIGN KEY (id_client) REFERENCES client(id)
        )
        """
    )
    
    # Interactions
    cursor.execute(
        """--sql
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            swiper_id INTEGER,
            target_id INTEGER,
            project_id INTEGER,
            action TEXT,
            target_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(swiper_id, target_id, project_id),
            FOREIGN KEY (swiper_id) REFERENCES utilisateurs(id),
            FOREIGN KEY (target_id) REFERENCES utilisateurs(id),
            FOREIGN KEY (project_id) REFERENCES commandes(id)
        )
        """
    )
    # Messages
    cursor.execute(
        """--sql
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_read BOOLEAN DEFAULT 0,
            FOREIGN KEY (sender_id) REFERENCES utilisateurs(id),
            FOREIGN KEY (receiver_id) REFERENCES utilisateurs(id)
        )
        """
    )

    # Documents
    cursor.execute(
        """--sql
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            nom TEXT NOT NULL,
            chemin TEXT NOT NULL,
            date_upload DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES utilisateurs(id)
        )
        """
    )
    

# =============================
# PAGE D'ACCUEIL
# =============================
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return redirect(url_for("welcome"))

# =============================
# PAGE WELCOME (si pas de session)
# =============================
@app.route("/welcome")
def welcome():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return render_template("welcome.html")


# =============================
# CONNEXION
# =============================
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        mdp = request.form.get("mdp")
        
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM utilisateurs WHERE email = ?", (email,))
        user_db = cursor.fetchone()
        conn.close()

        if user_db:
            is_valid, error = verify_password_hash(user_db['password'], mdp)
        else:
            is_valid, error = False, None

        if user_db and is_valid:
            
            if user_db['valide'] == 0:
                error = "Votre compte est en attente de validation."
                return render_template("login.html", error=error)

            # Création de l'utilisateur
            user_obj = User(
                id=user_db['id'],
                nom=user_db['nom'],
                email=user_db['email'],
                autorisations=user_db['autorisations'],
                tags=user_db['tags']
            )

            login_user(user_obj)
            flash("Connexion réussie !", "success")
            return redirect(url_for("index"))
        
        else:
            return render_template("login.html", error=error or "Email ou mot de passe incorrect.")
            
    return render_template("login.html")


# =============================
# INSCRIPTION
# =============================
@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        donnees  = request.form
        email    = donnees.get("email")
        nom      = donnees.get("nom")
        mdp      = donnees.get("mdp")
        tags_str = (donnees.get("tags") or "").strip()
        role     = donnees.get("role") or "intervenant"
        
        hashed_password = generate_password_hash(mdp, method='pbkdf2:sha256')

        # Définition des rôles et du statut par défaut
        autorisations = 2 if role == "client" else 1
        tags_value = ",".join([t.strip() for t in tags_str.split(',') if t.strip()]) if tags_str else None
        
        valide = 0 

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM utilisateurs WHERE email = ?", (email,))
        utilisateur = cursor.fetchone()

        if utilisateur is None:
            cursor.execute(
                "INSERT INTO utilisateurs (nom, email, password, tags, autorisations, valide) VALUES (?, ?, ?, ?, ?, ?)",
                (nom, email, hashed_password, tags_value, autorisations, valide),
            )
            conn.commit()
            conn.close()
            
            return render_template("login.html", error="Votre compte a été créé avec succès. Il est en attente de validation par un administrateur.")
        
        else:
            conn.close()
            error = "Cette adresse e-mail est déjà utilisée."
            return render_template("register.html", error=error)
    else:
        return render_template("register.html", error=None)


# =============================
# DÉCONNEXION
# =============================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("login"))

# =============================
# PAGE DASHBOARD
# =============================
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()


    my_id = current_user.id
    my_auth = current_user.autorisations
    
    # Initialisation des variables
    projects = []
    waiting_projects = 0
    opportunities = 0
    unread_messages = 0

    # --- STATS ---
    
    if my_auth == 1: # Intervenant
        cursor.execute("SELECT * FROM commandes WHERE intervenants LIKE ?", (f"%{current_user.email}%",))
        projects = cursor.fetchall()

        my_tags = set([t.strip().lower() for t in (current_user.tags or "").split(',') if t.strip()])
        cursor.execute("SELECT tags_intervenants FROM commandes WHERE status = 'waiting'")
        all_pending = cursor.fetchall()
        
        for p in all_pending:
            p_tags = set([t.strip().lower() for t in (p['tags_intervenants'] or "").split(',') if t.strip()])
            if my_tags.intersection(p_tags):
                opportunities += 1

    elif my_auth == 2: # CDP
        cursor.execute("SELECT * FROM commandes WHERE id_cdp = ?", (my_id,))
        projects = cursor.fetchall()

        for p in projects:
            if p['status'] == 'waiting':
                waiting_projects += 1

    elif my_auth == 3: # Admin
        cursor.execute("SELECT * FROM commandes")
        projects = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM commandes WHERE status = 'waiting'")
        waiting_projects = cursor.fetchone()[0]

    # --- MESSAGES ---
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE receiver_id = ? AND is_read = 0
        """, (my_id,))
        unread_messages = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        unread_messages = 0

    conn.close()

    # --- DONNÉES POUR LE TEMPLATE ---
    stats_data = {
        'projets_actifs': len(projects),
        'matchs_potentiels': opportunities if my_auth == 1 else waiting_projects,
        'messages_non_lus': unread_messages
    }

    return render_template('dashboard.html',
                           active_page='dashboard',
                           user_name=current_user.nom,
                           my_auth=my_auth,
                           stats=stats_data
                           )

@app.route('/projets', methods=["GET", "POST"])
@login_required
def projects():
    # 1. Config BDD & Utilisateur
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    is_admin = (current_user.autorisations == 3)
    project_id = request.args.get('p')

    # Config des statuts (Label + Couleur pour les badges)
    status_config = {
        "draft":   {'label': "Brouillon",  'color': "gray"},
        "waiting": {'label': "En attente", 'color': "blue"},
        "nego":    {'label': "En cours",   'color': "orange"},
        "won":     {'label': "Terminé",    'color': "green"},
    }
    # Map simple pour les menus déroulants
    status_map_simple = {k: v['label'] for k, v in status_config.items()}

    # ==========================================
    # CAS A : PROJET UNIQUE (Détail / Édition)
    # ==========================================
    if project_id:
        # Vérification accès
        cursor.execute("""
            SELECT u.email as cdp_email, c.intervenants, cl.email as client_email
            FROM commandes c
            LEFT JOIN utilisateurs u ON c.id_cdp = u.id
            LEFT JOIN client cl ON c.id_client = cl.id
            WHERE c.id = ?
        """, (project_id,))
        access = cursor.fetchone()

        if not access:
            conn.close()
            flash("Projet introuvable.", "danger")
            return redirect(url_for('projects'))

        intervenants = parse_list_field(access['intervenants'])
        is_cdp = (current_user.email == access['cdp_email'])
        can_access = is_admin or is_cdp or (current_user.email == access['client_email']) or (current_user.email in intervenants)

        if not can_access:
            conn.close()
            flash("Accès refusé", "danger")
            return redirect(url_for('projects'))

        # Traitement POST (Mise à jour)
        if request.method == "POST":
            f = request.form
            action = f.get("action", "edit_project").strip()

            if action == "planning":
                if not (is_admin or is_cdp):
                    flash("Accès refusé.", "danger")
                else:
                    intervenants_value = ",".join(parse_list_field(f.get("intervenants")))
                    jalons_raw = f.get("jalons")
                    if jalons_raw is None:
                        cursor.execute(
                            "UPDATE commandes SET intervenants = ? WHERE id = ?",
                            (intervenants_value, project_id),
                        )
                    else:
                        cursor.execute(
                            "UPDATE commandes SET intervenants = ?, jalons_id = ? WHERE id = ?",
                            (intervenants_value,
                             ",".join(map(str, create_jalons_from_text(cursor, jalons_raw))) or None,
                             project_id),
                        )
                    conn.commit()
                    flash("Planning mis à jour.", "success")
            else:
                if not is_admin:
                    flash("Accès admin requis.", "danger")
                else:
                    st = f.get("status", "draft").lower()
                    cursor.execute("UPDATE commandes SET objets=?, date_fin=?, tags_intervenants=?, status=?, description=? WHERE id=?", 
                                   (f.get("titre"), f.get("date_fin") or None, ",".join(parse_list_field(f.get("tags"))), 
                                    st if st in status_config else "draft", f.get("description"), project_id))
                    conn.commit()
                    flash("Projet mis à jour.", "success")
            
            conn.close()
            return redirect(url_for('projects', p=project_id))

        # Affichage Détail
        cursor.execute("""--sql
            SELECT c.*, u.email as cdp_email, cl.nom_complet, cl.email as client_email, cl.secteur, cl.nom_complet as contact
            FROM commandes c
            LEFT JOIN client cl ON c.id_client = cl.id
            LEFT JOIN utilisateurs u ON c.id_cdp = u.id
            WHERE c.id = ?
        """, (project_id,))
        row = cursor.fetchone()
        
        # Jalons
        j_ids = parse_id_list(row['jalons_id'])
        jalons_list = []
        assignations_map = get_jalon_assignations(cursor, j_ids)
        if j_ids:
            cursor.execute(f"SELECT * FROM jalon WHERE id IN ({','.join(['?']*len(j_ids))}) ORDER BY id", j_ids)
            jalons_list = [{
                "id": j['id'],
                "nom": j['nom'],
                "date": j['date_limite'],
                "description": j['description'],
                "taches": parse_list_field(j['taches']),
                "assignations": assignations_map.get(j['id'], [])
            } for j in cursor.fetchall()]

        project_data = dict(row)
        print(project_data)
        project_intervenants = parse_list_field(row['intervenants'])
        current_jalon_tasks = []
        if jalons_list:
            current_jalon = jalons_list[0]
            current_jalon_tasks = [
                item["tache"] for item in current_jalon.get("assignations", [])
                if str(item.get("intervenant_id")) == str(current_user.id) and item.get("tache")
            ]

        project_data.update({
            'tags': parse_list_field(row['tags_intervenants']),
            'intervenants': project_intervenants,
            'jalons': jalons_list,
            'jalons_raw': "\n".join([f"{j['date']}: {j['nom']}" for j in jalons_list]),
            'titre': row['objets'],
            'status': status_map_simple.get((row['status'] or 'draft').lower(), "Brouillon"),
            'status_key': (row['status'] or 'draft').lower(),
            'client': {'nom': row['nom_complet'], 'email': row['client_email'], 'secteur': row['secteur'], 'contact': row['contact']},
            'current_jalon_tasks': current_jalon_tasks
        })

        conn.close()
        return render_template('project_frame.html', active_page='projects', p=project_data, is_admin=is_admin, is_cdp=is_cdp, status_map=status_map_simple)

    # ==========================================
    # CAS B : TABLEAU DE BORD ADMIN (Stats + Formulaire)
    # ==========================================
    elif is_admin:
        if request.method == "POST":
            f = request.form
            client_email, cdp_email = f.get("client_email"), f.get("cdp_email")
            
            # Récupération IDs
            c_res = cursor.execute("SELECT id FROM client WHERE email=?", (client_email,)).fetchone()
            u_res = cursor.execute("SELECT id FROM utilisateurs WHERE email=?", (cdp_email,)).fetchone()

            if c_res and u_res and f.get("titre"):
                intervenants = parse_list_field(f.get("intervenants"))
                if cdp_email not in intervenants: intervenants.insert(0, cdp_email)
                
                cursor.execute("""
                    INSERT INTO commandes (id_cdp, id_client, date_debut, date_fin, objets, tags_intervenants, jalons_id, status, description, intervenants)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (u_res[0], c_res[0], date.today().isoformat(), f.get("date_fin") or None, f.get("titre"), 
                      ",".join(parse_list_field(f.get("tags"))), 
                      ",".join(map(str, create_jalons_from_text(cursor, f.get("jalons")))) or None, 
                      f.get("status", "draft"), f.get("description"), ",".join(intervenants)))
                conn.commit()
                flash("Projet créé.", "success")
            else:
                flash("Erreur: Client, CDP ou Titre invalide.", "danger")
            
            conn.close()
            return redirect(url_for('projects'))

        # Calcul Stats pour la "Synthèse"
        cursor.execute("SELECT status, tags_intervenants FROM commandes")
        raw_data = cursor.fetchall()
        
        status_board = {k: [] for k in status_config} # Sert juste à compter la longueur des listes
        tag_counter = {}

        for r in raw_data:
            st = (r['status'] or 'draft').lower()
            if st in status_board: status_board[st].append(1) # On ajoute juste un élément pour faire length
            
            for t in parse_list_field(r['tags_intervenants']):
                tag_counter[t] = tag_counter.get(t, 0) + 1

        # Options formulaires
        clients = [{"email": r[0], "label": f"{r[1]} ({r[0]})"} for r in cursor.execute("SELECT email, nom_complet FROM client ORDER BY nom_complet").fetchall()]
        cdps = [{"email": r[0], "label": f"{r[1]} ({r[0]})"} for r in cursor.execute("SELECT email, nom FROM utilisateurs WHERE autorisations = 2 ORDER BY nom").fetchall()]

        conn.close()
        return render_template('projects_client.html', active_page='projects', status_board=status_board, status_map=status_config, 
                               tag_counter=tag_counter, form_data=request.form if request.method=="POST" else {}, client_options=clients, cdp_options=cdps)

    # ==========================================
    # CAS C : LISTE SIMPLE (Intervenant / CDP)
    # ==========================================
    else:
        cursor.execute("""--sql
            SELECT c.id, c.objets, c.date_debut, c.date_fin, c.tags_intervenants, cl.nom_complet
            FROM commandes c JOIN client cl ON c.id_client = cl.id
            WHERE c.id_cdp = ? OR (c.intervenants LIKE ?) ORDER BY c.date_fin ASC
        """, (current_user.id, f"%{current_user.email}%"))
        
        projects_list = []
        for r in cursor.fetchall():
            pc = 0
            days_left = 0 # Valeur par défaut pour éviter l'erreur
            
            if r['date_fin'] and r['date_debut']:
                try:
                    s = datetime.strptime(r['date_debut'], '%Y-%m-%d').date()
                    e = datetime.strptime(r['date_fin'], '%Y-%m-%d').date()
                    
                    # Calcul pourcentage
                    total = (e - s).days
                    elapsed = (date.today() - s).days
                    if total > 0:
                        pc = max(0, min(100, int((elapsed / total) * 100)))
                    else:
                        pc = 100
                    
                    # Calcul jours restants
                    days_left = (e - date.today()).days
                except ValueError: 
                    pass
            
            projects_list.append({
                'id': r['id'], 
                'titre': r['objets'], 
                'client': r['nom_complet'], 
                'tags': parse_list_field(r['tags_intervenants']),
                'percent': pc, 
                'days_left': days_left, # <--- C'est cette ligne qui manquait !
                'date_fin': r['date_fin'],
                'initiale': r['objets'][0].upper() if r['objets'] else "?",
                'color_class': 'green' if pc == 100 else ('blue' if pc > 50 else 'yellow')
            })

        conn.close()
        return render_template('projects.html', active_page='projects', projects=projects_list, get_avatar=get_avatar, is_client=False)


@app.route('/projets/jalons', methods=["GET", "POST"])
@login_required
def edit_jalons():
    project_id = request.args.get('p') or request.form.get('project_id')
    if not project_id:
        flash("Projet introuvable.", "danger")
        return redirect(url_for('projects'))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.email as cdp_email, c.intervenants, cl.email as client_email, c.objets as titre
        FROM commandes c
        LEFT JOIN utilisateurs u ON c.id_cdp = u.id
        LEFT JOIN client cl ON c.id_client = cl.id
        WHERE c.id = ?
    """, (project_id,))
    access = cursor.fetchone()

    if not access:
        conn.close()
        flash("Projet introuvable.", "danger")
        return redirect(url_for('projects'))

    intervenants = parse_list_field(access['intervenants'])
    is_admin = (current_user.autorisations == 3)
    is_cdp = (current_user.email == access['cdp_email'])
    can_access = is_admin or is_cdp

    if not can_access:
        conn.close()
        flash("Accès refusé.", "danger")
        return redirect(url_for('projects'))

    if request.method == "POST":
        titles = request.form.getlist("jalon_title[]")
        dates = request.form.getlist("jalon_date[]")
        descriptions = request.form.getlist("jalon_description[]")

        cursor.execute("SELECT jalons_id FROM commandes WHERE id = ?", (project_id,))
        old_jalons = parse_id_list((cursor.fetchone() or [None])[0])
        if old_jalons:
            placeholder = ",".join(["?"] * len(old_jalons))
            cursor.execute(f"DELETE FROM jalon_intervenant WHERE jalon_id IN ({placeholder})", old_jalons)
            cursor.execute(f"DELETE FROM jalon WHERE id IN ({placeholder})", old_jalons)

        new_jalon_ids = []
        existing_intervenants_value = ",".join(intervenants) if intervenants else None

        for idx, title in enumerate(titles):
            title = (title or "").strip()
            if not title:
                continue
            date_value = (dates[idx] if idx < len(dates) else "").strip()
            description = (descriptions[idx] if idx < len(descriptions) else "").strip()

            cursor.execute(
                "INSERT INTO jalon (nom, taches, date_limite, description) VALUES (?, ?, ?, ?)",
                (title, "", date_value or None, description or None),
            )
            jalon_id = cursor.lastrowid
            new_jalon_ids.append(jalon_id)

            intervenant_ids = request.form.getlist(f"assignment_intervenant_id_{idx}[]")
            tasks = request.form.getlist(f"assignment_task_{idx}[]")
            for intervenant_id, task in zip(intervenant_ids, tasks):
                intervenant_id = (intervenant_id or "").strip()
                task = (task or "").strip()
                if not intervenant_id:
                    continue
                cursor.execute(
                    "INSERT INTO jalon_intervenant (jalon_id, intervenant_id, tache) VALUES (?, ?, ?)",
                    (jalon_id, intervenant_id, task),
                )

        cursor.execute(
            "UPDATE commandes SET jalons_id = ?, intervenants = ? WHERE id = ?",
            (",".join(map(str, new_jalon_ids)) or None, existing_intervenants_value, project_id),
        )
        conn.commit()
        conn.close()
        flash("Jalons mis à jour.", "success")
        return redirect(url_for('projects', p=project_id))

    cursor.execute("SELECT jalons_id FROM commandes WHERE id = ?", (project_id,))
    j_ids = parse_id_list((cursor.fetchone() or [None])[0])
    assignations_map = get_jalon_assignations(cursor, j_ids)
    jalons_list = []
    if j_ids:
        cursor.execute(f"SELECT * FROM jalon WHERE id IN ({','.join(['?']*len(j_ids))}) ORDER BY id", j_ids)
        jalons_list = [{
            "id": j["id"],
            "nom": j["nom"],
            "date": j["date_limite"],
            "description": j["description"],
            "assignations": assignations_map.get(j["id"], [])
        } for j in cursor.fetchall()]

    project_emails = set(intervenants)
    if access['cdp_email']:
        project_emails.add(access['cdp_email'])

    project_intervenants = []
    if project_emails:
        placeholder = ",".join(["?"] * len(project_emails))
        cursor.execute(
            f"SELECT id, nom, email FROM utilisateurs WHERE email IN ({placeholder}) ORDER BY nom",
            list(project_emails),
        )
        project_intervenants = [{"id": row[0], "nom": row[1], "email": row[2]} for row in cursor.fetchall()]

    conn.close()
    return render_template(
        'jalons_edit.html',
        active_page='projects',
        project_id=project_id,
        project_title=access['titre'],
        jalons=jalons_list,
        project_intervenants=project_intervenants,
        is_admin=is_admin,
        is_cdp=is_cdp,
    )
    
    
@app.route('/propositions')
@login_required
def proposals():

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    user_role = current_user.autorisations

    # SÉCURITÉ
    if user_role != 3:
        conn.close()
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('dashboard'))

    is_client = True 

    query = """--sql
        SELECT 
            c.id, 
            c.objets, 
            c.tags_intervenants, 
            cl.nom_complet,
            c.date_fin,
            c.status,
            c.description
        FROM commandes c
        LEFT JOIN client cl ON c.id_client = cl.id
    """
    cursor.execute(query)
    
    raw_data = cursor.fetchall()
    conn.close()

    columns_config = {
        1: {'label': 'Brouillons', 'color': 'gray'},
        2: {'label': 'En attente', 'color': 'blue'},
        3: {'label': 'En cours', 'color': 'orange'},
        4: {'label': 'Terminés', 'color': 'green'}
    }

    kanban_board = {1: [], 2: [], 3: [], 4: []}

    for row in raw_data:
        tags_str = row[2] if row[2] else ""
        tags_list = tags_str.split(',') if tags_str else []
        
        status_db = (row[5] or "draft").lower()
        
        col_index = 1
        if "won" in status_db or "valid" in status_db: col_index = 4
        elif "nego" in status_db: col_index = 3
        elif "waiting" in status_db: col_index = 2
        
        nom_client = row[3] if row[3] else "Client Inconnu"
        description = row[6] if row[6] else ""

        card = {
            'id': row[0],
            'titre': row[1],
            'client': nom_client,
            'tags': tags_list,
            'date_fin': row[4],
            'description': description
        }

        kanban_board[col_index].append(card)

    return render_template('proposals.html', 
                           active_page='proposals', 
                           board=kanban_board, 
                           columns_config=columns_config,
                           is_client=is_client)

@app.route('/api/update_project_status', methods=['POST'])
@login_required
def update_project_status():

    data       = request.get_json()
    project_id = data.get('project_id')
    new_status = data.get('new_status')

    if not project_id or not new_status:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Sécurité : On vérifie si l'utilisateur a le droit de toucher à ce projet
    if current_user.autorisations == 3:
        cursor.execute("UPDATE commandes SET status = ? WHERE id = ?", (new_status, project_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    else:
        conn.close()
        return jsonify({'success': False, 'message': 'Permission refusée'}), 403


@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    my_id     = current_user.id
    my_auth   = current_user.autorisations

    if my_auth == 1:
        query_contacts = "SELECT id, nom FROM utilisateurs WHERE autorisations > 1 AND id != ?"
    elif my_auth == 2:
        query_contacts = "SELECT id, nom FROM utilisateurs WHERE autorisations = 1 AND id != ?"
    else:
        query_contacts = "SELECT id, nom FROM utilisateurs WHERE id != ?"
        
    cursor.execute(query_contacts, (my_id,))
    users_raw = cursor.fetchall()
    allowed_ids = [u[0] for u in users_raw]
    other_user_id = request.args.get('contact_id')
    
    if other_user_id:
        try:
            other_user_id = int(other_user_id)
            if other_user_id not in allowed_ids:
                flash("Vous n'avez pas le droit de contacter cette personne.", "danger")
                other_user_id = None 
        except ValueError:
            other_user_id = None

    if request.method == 'POST' and other_user_id:
        content = request.form.get('message')
        if content:
            cursor.execute(
                """--sql
                INSERT INTO messages (sender_id, receiver_id, content)
                VALUES (?, ?, ?)
                """, (my_id, other_user_id, content))
            conn.commit()
            return redirect(url_for('chat', contact_id=other_user_id))

    contacts = []
    for u in users_raw:
        u_id = u[0]
        u_nom = u[1]
        
        cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE sender_id = ? AND receiver_id = ? AND is_read = 0",
            (u_id, my_id)
        )
        unread_count = cursor.fetchone()[0]
        
        contacts.append({
            'id': u_id,
            'nom': u_nom,
            'initiales': u_nom[:2].upper() if u_nom else "?",
            'active': (u_id == other_user_id),
            'unread_count': unread_count
        })

    messages = []
    active_contact_name = "Sélectionnez un contact"

    if other_user_id:
        cursor.execute(
            "UPDATE messages SET is_read = 1 WHERE sender_id = ? AND receiver_id = ?", 
            (other_user_id, my_id)
        )
        conn.commit()

        cursor.execute("SELECT nom FROM utilisateurs WHERE id = ?", (other_user_id,))
        res = cursor.fetchone()
        if res:
            active_contact_name = res[0]

        query_msg = """--sql
            SELECT sender_id, content, timestamp 
            FROM messages 
            WHERE (sender_id = ? AND receiver_id = ?) 
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp ASC
        """
        cursor.execute(query_msg, (my_id, other_user_id, other_user_id, my_id))
        raw_msgs = cursor.fetchall()
        
        for msg in raw_msgs:
            is_me = (msg[0] == my_id)
            messages.append({
                'is_me': is_me,
                'text': msg[1],
                'time': msg[2][11:16] if msg[2] else ""
            })

    conn.close()

    return render_template('chat.html', 
                           active_page='chat', 
                           contacts=contacts, 
                           messages=messages, 
                           active_contact_name=active_contact_name,
                           selected_id=other_user_id)

@app.route('/tinder/action/<int:target_id>/<action>', methods=['POST'])
@login_required
def tinder_action(target_id, action):

    data = request.get_json()
    project_id = data.get('project_id')

    try:
        project_id = int(project_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Project ID invalide'}), 400

    conn = sqlite3.connect(DATABASE, timeout=10)
    cursor = conn.cursor()
    
    try:
        my_id = current_user.id
        
        cursor.execute("""--sql
            INSERT INTO interactions (swiper_id, target_id, project_id, action, target_type)
            VALUES (?, ?, ?, ?, 'USER')
        """, (my_id, target_id, project_id, action))
        
        conn.commit()
        return jsonify({'success': True})

    except sqlite3.IntegrityError:
        return jsonify({'success': True, 'info': 'Doublon'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        conn.close()

@app.route('/tinder')
@login_required
def tinder():
    
    project_id = request.args.get('p')
    
    if not project_id:
        flash("Aucun projet sélectionné pour le swipe.", "warning")
        return redirect(url_for('intervenants'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    my_id = current_user.id
    
    cursor.execute("SELECT objets, tags_intervenants FROM commandes WHERE id = ?", (project_id,))
    project_data = cursor.fetchone()
    
    if not project_data:
        conn.close()
        return redirect(url_for('intervenants'))
        
    project_title = project_data[0]
    p_tags_str = project_data[1] if project_data[1] else ""
    p_req_set = set([k.strip().lower() for k in p_tags_str.split(',') if k.strip()])

    candidates = []

    query_users = """--sql
        SELECT id, nom, tags, bio FROM utilisateurs 
        WHERE autorisations = 1
          AND id NOT IN (
              SELECT target_id FROM interactions 
              WHERE swiper_id = ? AND project_id = ?
          )
    """
    cursor.execute(query_users, (my_id, project_id))
    users = cursor.fetchall()

    for u in users:
        u_id, u_nom, u_tags, u_bio = u
        
        u_tags_str = u_tags if u_tags else ""
        u_tags_set = set([k.strip().lower() for k in u_tags_str.split(',') if k.strip()])

        common = len(u_tags_set.intersection(p_req_set))
        required = len(p_req_set)
        
        match_score = int((common / required) * 100) if required > 0 else 100

        candidates.append({
            'id': u_id,
            'nom': u_nom,
            'role': "Intervenant",
            'description': u_bio if u_bio else "Pas de bio renseignée.",
            'taux_match': match_score,
            'initiales': u_nom[:2].upper() if u_nom else "?",
            'tags': list(u_tags_set)
        })

    conn.close()

    candidates.sort(key=lambda x: x['taux_match'], reverse=True)

    current_prospect = candidates[0] if candidates else None
    next_prospect = True if len(candidates) > 1 else False
    
    return render_template('tinder.html', 
                           current_prospect=current_prospect, 
                           next_prospect=next_prospect,
                           current_project_id=project_id,
                           current_project_title=project_title)



@app.route('/gestion_site', methods=['GET', 'POST'])
@login_required
def gestion_site():
    
    auth_level = current_user.autorisations
    if auth_level is None or int(auth_level) != 3:
       abort(403)
    is_error = False # ? bool pour déclencher une erreur (ex avec ajout)

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST': 
        action = request.form.get('action') 

        # Valider un compte
        if action == 'validate-user':
            user_id = request.form.get('user_id')
            cursor.execute("UPDATE utilisateurs SET valide = 1 WHERE id = ?", (user_id,))
            conn.commit()
            flash("Compte validé")

        # Supprimer utilisateur
        elif action == 'delete-user':
            user_id = request.form.get('user_id')
            cursor.execute("DELETE FROM utilisateurs WHERE id = ?", (user_id,))
            conn.commit()

        # ? Importer CSV
        elif action == 'import-csv':
            fichier = request.files.get('fichier')
            if fichier and fichier.filename != '':
                file_content = fichier.read().decode("utf-8")
                lignes = file_content.splitlines()
                if len(lignes) > 1:
                    header = lignes[0].split(';')
                    idx = {}
                    for i, col in enumerate(header):
                        c = col.lower().strip()
                        if   'nom'   in c: idx['nom'] = i
                        elif 'email' in c: idx['email'] = i
                        elif 'pass'  in c: idx['mdp'] = i
                        elif 'tag'   in c: idx['tags'] = i
                        elif 'auto'  in c: idx['aut'] = i
                    
                    if 'email' in idx and 'nom' in idx and 'mdp' in idx:
                        for ligne in lignes[1:]:
                            data = ligne.split(';')
                            if len(data) >= 3:
                                email = data[idx['email']]
                                cursor.execute("SELECT id FROM utilisateurs WHERE email = ?", (email,))
                                if cursor.fetchone() is None:
                                    nom = data[idx['nom']]
                                    mdp = data[idx['mdp']]
                                    tags = data[idx['tags']] if 'tags' in idx and len(data) > idx['tags'] else ""
                                    aut = data[idx['aut']] if 'aut' in idx and len(data) > idx['aut'] else 1
                                    
                                    cursor.execute(
                                        "INSERT INTO utilisateurs (nom, email, password, tags, autorisations, valide) VALUES (?, ?, ?, ?, ?, 1)",
                                        (nom, email, mdp, tags, aut)
                                    )
                        conn.commit()

        # ? Exporter CSV 
        elif action == 'export-csv':
            selected_ids = request.form.getlist('user-ids')# ? liste des ids sélectionnées
            #print(selected_ids) bon l'erreur vient du html
            if  not selected_ids :
                cursor.execute('SELECT * FROM utilisateurs')
            else :
                sql_liste = ', '.join(['?'] * len(selected_ids)) # ? pour avoir la liste des id an sql (juste plein de ? join)
                cursor.execute(f'SELECT * FROM utilisateurs WHERE id IN ({sql_liste})',selected_ids)
            users_data = cursor.fetchall()
            
            output = io.StringIO()
            writer = csv.writer(output, delimiter=';')
            
            if cursor.description:
                writer.writerow([col[0] for col in cursor.description])
                
            writer.writerows(users_data)

            output.seek(0)
            conn.close()
            
            return send_file(#merci flask quand meme
                io.BytesIO(output.getvalue().encode('utf-8-sig')),
                mimetype='csv',
                as_attachment=True,
                download_name='uutilisateurs.csv'
            )
        
        elif action == 'supprimer':
            selected_ids = request.form.getlist('user-ids')# ? liste des ids sélectionnées
            if  not selected_ids :
                error = "Sélectionner la personne à supprimer"
                is_error = True 
            else :
                sql_liste = ', '.join(['?'] * len(selected_ids)) # ? pour avoir la liste des id an sql (juste plein de ? join)
                cursor.execute(f'DELETE FROM utilisateurs WHERE id IN ({sql_liste})',selected_ids)
                conn.commit()
            

        # ? Ajout d'un utilisateur
        elif action == 'ajout-utilisateur':
            donnees = request.form
            email = donnees.get("email")
            nom = donnees.get("nom")
            mdp = donnees.get("mdp")
            role = donnees.get("role") 
            val_r = 1
            if role == "cdp" :
                val_r =2
            elif role == "admin" :
                val_r=3

            cursor.execute("SELECT * FROM utilisateurs WHERE email = ?", (email,))
            utilisateur = cursor.fetchone()

            if utilisateur is None:
                cursor.execute(
                "INSERT INTO utilisateurs (nom, email, password,autorisations) VALUES (?, ?, ?, ?)",
                (nom, email, mdp, val_r),
                )
                conn.commit()
            else:
                error = "Cette adresse e-mail est déjà utilisée."
                is_error = True

        elif action == 'add-selected':
            new_id = request.get()

    # Affichage
    cursor.execute('SELECT * FROM utilisateurs') 
    user_list = cursor.fetchall()
    conn.close()
    if is_error :
        return render_template('gestion_site.html', active_page='gestion_site', users=user_list, error=error)
    return render_template('gestion_site.html', active_page='gestion_site', users=user_list,error=None)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # --- MIGRATION AUTOMATIQUE (Sécurité colonne avatar) ---
    cursor.execute("PRAGMA table_info(utilisateurs)")
    cols = [col[1] for col in cursor.fetchall()]
    if 'avatar' not in cols:
        cursor.execute("ALTER TABLE utilisateurs ADD COLUMN avatar TEXT")
        conn.commit()

    # --- SAUVEGARDE (POST) ---
    if request.method == 'POST':
        try:
            nom = request.form.get('nom')
            email = request.form.get('email')
            tags_str = request.form.get('tags')
            bio = request.form.get('bio', '')
            disponibilite = request.form.get('disponibilite', 'Disponible')
            langues = request.form.get('langues', '')
            liens = request.form.get('liens', '')
            nouveau_mdp = request.form.get('new_password')
            
            tags_list = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
            tags_clean = ", ".join(tags_list)
            avatar_filename = None

            # --- GESTION DE L'AVATAR ---
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and file.filename != '':

                    # Vérification de la taille du fichier
                    file.seek(0, os.SEEK_END)
                    file_length = file.tell()
                    file.seek(0)

                    if file_length > MAX_FILE_SIZE:
                        flash("Erreur : L'image dépasse 5 Mo.", "danger")
                    elif allowed_file(file.filename):
                        ext = file.filename.rsplit('.', 1)[1].lower()
                        uid = current_user.id if current_user.id else "unknown"
                        
                        import time
                        filename = f"user_{uid}_{int(time.time())}.{ext}"
                        
                        if not os.path.exists(UPLOAD_FOLDER):
                            os.makedirs(UPLOAD_FOLDER)
                            
                        file.save(os.path.join(UPLOAD_FOLDER, filename))
                        avatar_filename = filename
                    else:
                        flash("Format d'image non supporté.", "danger")

            query = """UPDATE utilisateurs 
                       SET nom = ?, email = ?, tags = ?, bio = ?, disponibilite = ?, langues = ?, liens = ?"""
            params = [nom, email, tags_clean, bio, disponibilite, langues, liens]

            if nouveau_mdp:
                query += ", password = ?"
                params.append(generate_password_hash(nouveau_mdp, method='pbkdf2:sha256'))
            
            if avatar_filename:
                query += ", avatar = ?"
                params.append(avatar_filename)

            query += " WHERE email = ?"
            params.append(current_user.email)
            
            cursor.execute(query, tuple(params))
            conn.commit()

            current_user.email = email
            current_user.nom   = nom
            
            flash("Profil mis à jour !", "success")
            return redirect(url_for('compte'))

        except Exception as e:
            print(f"Erreur settings: {e}")
            flash(f"Erreur lors de la mise à jour : {e}", "danger")
        finally:
            conn.close()
            
        return redirect(url_for('settings'))

    # --- AFFICHAGE (GET) ---
    user = get_user_data_full_tuple(current_user.email)
    
    if user:
        utilisateur_liste = list(user)
        if utilisateur_liste[4] is None:
            utilisateur_liste[4] = ""
        return render_template('settings.html', 
                               active_page='settings', 
                               user=utilisateur_liste, 
                               avatar_url=user[6])
    
    return redirect(url_for('login'))

@app.route("/compte")
@login_required
def compte():
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()

    target_id_param = request.args.get('id')

    if target_id_param:
        try:
            target_id = int(target_id_param)
        except ValueError:
            target_id = current_user.id
    else:
        target_id = current_user.id
    
    can_view = (target_id == current_user.id)

    if not can_view:
        cursor.execute("SELECT autorisations FROM utilisateurs WHERE id = ?", (target_id,))
        res = cursor.fetchone()
        
        if res:
            target_auth = res["autorisations"]
            
            if current_user.autorisations == 3:
                can_view = True
            elif current_user.autorisations == 2 and target_auth == 1:
                can_view = True
            
        else:
            conn.close()
            flash("Profil introuvable.", "danger")
            return redirect(url_for("compte"))

    if not can_view:
        conn.close()
        flash("Vous n'avez pas la permission d'accéder à ce profil.", "danger")
        return redirect(url_for("compte"))

    if target_id == current_user.id:
        target_email = current_user.email
    else:
        cursor.execute("SELECT email FROM utilisateurs WHERE id = ?", (target_id,))
        target_email = cursor.fetchone()["email"]

    user_tuple = get_user_data_full_tuple(target_email)
    target_role = user_tuple[5]
    

    unread_count = 0
    waiting_count = 0
    overdue_count = 0
    opp_count = 0
    projects_list = []
    documents = [] 
    
    aujourdhui = date.today().isoformat()
    is_me = (target_id == current_user.id)


    if is_me:
        cursor.execute("SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0", (current_user.id,))
        unread_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT * FROM documents WHERE user_id = ? ORDER BY date_upload DESC", (current_user.id,))
        documents = cursor.fetchall()

        if current_user.autorisations == 2:
            cursor.execute("SELECT * FROM commandes WHERE id_client = (SELECT id FROM client WHERE email = ?)", (current_user.email,))
            projects_list = cursor.fetchall()
            
            cursor.execute("SELECT COUNT(*) FROM commandes WHERE id_client = (SELECT id FROM client WHERE email = ?) AND status = 'waiting'", (current_user.email,))
            waiting_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM commandes WHERE id_client = (SELECT id FROM client WHERE email = ?) AND status = 'won' AND date_fin < ?", (current_user.email, aujourdhui))
            overdue_count = cursor.fetchone()[0]
        else:
            cursor.execute("SELECT * FROM commandes WHERE id_cdp = ?", (current_user.id,))
            projects_list = cursor.fetchall()
            
            cursor.execute("SELECT COUNT(*) FROM commandes WHERE id_cdp IS NULL AND status = 'waiting'")
            opp_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM commandes WHERE id_cdp = ? AND status = 'won' AND date_fin < ?", (current_user.id, aujourdhui))
            overdue_count = cursor.fetchone()[0]

    else:
        if target_role == 1: 
             cursor.execute("SELECT * FROM commandes WHERE id_cdp = ?", (target_id,))
             projects_list = cursor.fetchall()

    conn.close()

    return render_template(
        "compte.html", 
        user=user_tuple, 
        unread_messages=unread_count, 
        projects=projects_list,
        waiting_projects=waiting_count,
        opportunities=opp_count,
        active_page="compte",
        documents=documents,
        is_me=is_me
    )

@app.route('/intervenants')
@login_required
def intervenants():
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    my_id   = current_user.id
    my_auth = current_user.autorisations

    if my_auth != 2:
        conn.close()
        flash("Accès réservé aux Chefs de Projet.", "danger")
        return redirect(url_for('dashboard'))

    # Récupération des interactions
    cursor.execute("SELECT project_id, target_id, action FROM interactions WHERE swiper_id = ?", (my_id,))
    interactions_raw = cursor.fetchall()
    interactions_map = {(row[0], row[1]): row[2] for row in interactions_raw}

    client_view_data = []

    # Projets en attente
    query_my_projects = """--sql
        SELECT c.id, c.objets, c.tags_intervenants, cl.nom_complet
        FROM commandes c
        LEFT JOIN client cl ON c.id_client = cl.id
        WHERE c.id_cdp = ? 
        AND c.status = 'waiting'
    """
    
    cursor.execute(query_my_projects, (my_id,))
    my_projects = cursor.fetchall()

    # Tous les intervenants
    query_intervenants = "SELECT id, nom, tags FROM utilisateurs WHERE autorisations = 1"
    cursor.execute(query_intervenants)
    all_intervenants = cursor.fetchall()
    
    for project in my_projects:
        p_id, p_objet, p_tags_str, p_client_name = project
        
        p_tags_str = p_tags_str if p_tags_str else ""
        required_tags_set = set([k.strip().lower() for k in p_tags_str.split(',') if k.strip()])
        
        candidates_for_this_project = []
        
        for inter in all_intervenants:
            i_id, i_nom, i_tags_str = inter
            
            # STATUT
            past_action = interactions_map.get((p_id, i_id))

            i_tags_str = i_tags_str if i_tags_str else ""
            intervenant_tags_set = set([k.strip().lower() for k in i_tags_str.split(',') if k.strip()])
            
            common_tags = required_tags_set.intersection(intervenant_tags_set)
            nb_common = len(common_tags)
            nb_required = len(required_tags_set)
            
            score = int((nb_common / nb_required) * 100) if nb_required > 0 else 100
            
            candidates_for_this_project.append({
                'id': i_id,
                'nom': i_nom,
                'initiales': i_nom[:2].upper() if i_nom else "?",
                'score': score,
                'common_tags': ", ".join(list(common_tags)) if common_tags else "Aucun",
                'interaction_status': past_action 
            })
        
        # Tri par pertinence
        candidates_for_this_project.sort(key=lambda x: x['score'], reverse=True)
        
        client_view_data.append({
            'project_id': p_id,
            'project_title': p_objet,
            'client_name': p_client_name if p_client_name else "Client Inconnu",
            'required_tags': p_tags_str,
            'candidates': candidates_for_this_project
        })

    conn.close()

    return render_template('intervenants.html', 
                            active_page='intervenants', 
                            my_auth=my_auth,
                            projects=[], 
                            client_data=client_view_data)

@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    
    mot_verification = request.form.get("verification")
    
    if mot_verification != "Je souhaite supprimer mon compte":
        flash("La phrase de confirmation était incorrecte.", "error")
        return redirect(url_for("settings"))

    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM utilisateurs WHERE email = ?", (current_user.email,))
        conn.commit()
        conn.close()
        logout_user()
        return redirect(url_for("index"))

    except Exception as e:
        print(f"Erreur lors de la suppression : {e}")
        return redirect(url_for("settings"))

import os

@app.route("/upload_document", methods=["POST"])
@login_required
def upload_document():
    
    file = request.files.get('file')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    user_id = current_user.id

    if file and file.filename != '':

        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)

        if file_length > MAX_FILE_SIZE:
            conn.close()
            flash("Le fichier dépasse la limite de 5 Mo.", "danger")
            print("Erreur : Fichier > 5Mo") 
            return redirect(url_for('compte', id=user_id))
        # -----------------------------------------

        filename = secure_filename(file.filename)

        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
        cursor.execute("INSERT INTO documents (user_id, nom, chemin) VALUES (?, ?, ?)", 
                       (user_id, filename, filename)) 
        conn.commit()
        
    conn.close()     
    return redirect(url_for('compte', id=user_id))

@app.route("/delete_document/<int:doc_id>")
@login_required
def delete_document(doc_id):

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    current_user_id = current_user.id

    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    document = cursor.fetchone()

    if document:

        if document['user_id'] == current_user_id:
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], document['chemin'])
            
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    print(f"Erreur lors de la suppression du fichier : {e}")
            
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            flash("Document supprimé avec succès.", "success")
        else:
            flash("Vous n'avez pas le droit de supprimer ce document.", "danger")
            
    conn.close()
    return redirect(request.referrer)

@app.route("/download_document/<int:doc_id>")
@login_required
def download_document(doc_id):
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    document = cursor.fetchone()
    conn.close()

    if document and current_user.is_authenticated:
        if document['user_id'] == current_user.id or current_user.autorisations == 3:
            
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], document['chemin'])

            if os.path.exists(full_path):
                return send_file(
                    full_path,
                    as_attachment=True,
                    download_name=document['nom']
                )
            else:

                flash("Erreur : Le fichier n'existe plus sur le serveur.", "danger")
                return redirect(request.referrer)
        else:
            flash("Accès refusé. Vous n'avez pas la permission.", "danger")
            return redirect(url_for('compte'))
    
    return redirect(request.referrer)

@app.route('/stats')
@login_required
def stats():

    if current_user.autorisations != 3: 
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # 1. UTILISATEURS
    cursor.execute("SELECT autorisations, COUNT(*) FROM utilisateurs GROUP BY autorisations")
    users_raw = cursor.fetchall()
    users_stats = {1: 0, 2: 0, 3: 0} 
    total_users = 0
    for role, count in users_raw:
        if role in users_stats: users_stats[role] = count
        total_users += count
    
    # LISTE PROPRE POUR CHART.JS (Intervenant, Client, Admin)
    # On force l'ordre pour que les couleurs correspondent
    users_chart_data = [users_stats[1], users_stats[2], users_stats[3]]

    cursor.execute("SELECT COUNT(*) FROM utilisateurs WHERE valide = 0")
    pending_users = cursor.fetchone()[0]

    # 2. PROJETS
    cursor.execute("SELECT status, COUNT(*) FROM commandes GROUP BY status")
    projects_raw = cursor.fetchall()
    projects_stats = {'draft': 0, 'waiting': 0, 'nego': 0, 'won': 0, 'finished': 0}
    total_projects = 0
    for status, count in projects_raw:
        s_key = (status or 'draft').lower()
        if s_key in projects_stats: projects_stats[s_key] += count
        total_projects += count

    # LISTE PROPRE POUR CHART.JS
    # Ordre : Brouillon, En attente, Nego, Validé, Terminé
    projects_chart_data = [
        projects_stats['draft'], 
        projects_stats['waiting'], 
        projects_stats['nego'], 
        projects_stats['won'], 
        projects_stats['finished']
    ]

    # 3. SKILLS (Offre vs Demande)
    from collections import Counter # S'assurer que c'est importé
    
    # Offre
    cursor.execute("SELECT tags FROM utilisateurs WHERE autorisations = 1")
    tags_supply = []
    for row in cursor.fetchall():
        if row[0]: tags_supply.extend([t.strip().lower() for t in row[0].split(',') if t.strip()])
    supply_counter = Counter(tags_supply)

    # Demande
    cursor.execute("SELECT tags_intervenants FROM commandes")
    tags_demand = []
    for row in cursor.fetchall():
        if row[0]: tags_demand.extend([t.strip().lower() for t in row[0].split(',') if t.strip()])
    demand_counter = Counter(tags_demand)

    # Fusion des clés pour le graphique
    top_10_supply = dict(supply_counter.most_common(10))
    top_10_demand = dict(demand_counter.most_common(10))
    
    # On prend tous les tags présents dans le top 10 offre OU demande
    all_skills_keys = list(set(list(top_10_supply.keys()) + list(top_10_demand.keys())))
    all_skills_keys.sort() # On trie par ordre alphabétique

    # On prépare les valeurs correspondantes
    skills_supply_data = [supply_counter[k] for k in all_skills_keys]
    skills_demand_data = [demand_counter[k] for k in all_skills_keys]

    # 4. AUTRES KPI
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM documents")
    total_documents = cursor.fetchone()[0]

    # 5. INTERACTIONS
    try:
        cursor.execute("SELECT action, COUNT(*) FROM interactions GROUP BY action")
        interactions_raw = cursor.fetchall()
        interactions_stats = {'LIKE': 0, 'PASS': 0}
        for action, count in interactions_raw:
            interactions_stats[action] = count
    except:
        interactions_stats = {'LIKE': 0, 'PASS': 0}
    
    conn.close()

    return render_template('stats.html', 
                           active_page='stats',
                           total_users=total_users,
                           pending_users=pending_users,
                           total_projects=total_projects,
                           total_messages=total_messages,
                           total_documents=total_documents,
                           interactions_stats=interactions_stats,
                           users_chart_data=users_chart_data,
                           projects_chart_data=projects_chart_data,
                           skills_labels=all_skills_keys,
                           skills_supply_data=skills_supply_data,
                           skills_demand_data=skills_demand_data
                           )

@app.route('/attribution', methods=['GET', 'POST'])
@login_required
def attribution():

    auth_level = current_user.autorisations
    if auth_level not in [2, 3]:
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # --- ACTION : ATTRIBUER (POST) ---
    if request.method == 'POST':
        project_id = request.form.get('project_id')
        candidate_email = request.form.get('candidate_email')

        cursor.execute("SELECT intervenants FROM commandes WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        
        if row:
            current_list_str = row['intervenants'] if row['intervenants'] else ""
            current_list = [x.strip() for x in current_list_str.split(',') if x.strip()]

            if candidate_email in current_list:
                flash("Cet intervenant est déjà attribué au projet.", "warning")
            else:
                current_list.append(candidate_email)
                new_list_str = ",".join(current_list)
                cursor.execute("UPDATE commandes SET intervenants = ? WHERE id = ?", (new_list_str, project_id))
                conn.commit()
                flash(f"L'intervenant {candidate_email} a été ajouté au projet.", "success")
        
        # On redirige vers la page avec les mêmes filtres si possible (ou reset)
        return redirect(url_for('attribution'))

    # --- AFFICHAGE AVEC FILTRES (GET) ---
    
    # 1. Récupération des filtres
    search_query = request.args.get('q', '').strip()
    filter_status = request.args.get('status', '').strip()

    # 2. Construction de la requête de base
    # Note : Si c'est un client (2), on pourrait filtrer par son ID ici si nécessaire
    # Pour l'instant on garde la logique "Admin/Client voient tout" ou adapté selon tes besoins précédents
    sql_projets = "SELECT id, objets, intervenants, status FROM commandes WHERE 1=1"
    params_projets = []

    # 3. Application des filtres
    if search_query:
        sql_projets += " AND objets LIKE ?"
        params_projets.append(f"%{search_query}%")
    
    if filter_status:
        sql_projets += " AND status = ?"
        params_projets.append(filter_status)

    # Tri par défaut (les plus récents en premier)
    sql_projets += " ORDER BY id DESC"

    cursor.execute(sql_projets, params_projets)
    projects_raw = cursor.fetchall()

    attribution_data = []

    for p in projects_raw:
        p_id = p['id']
        p_title = p['objets']
        assigned_str = p['intervenants'] if p['intervenants'] else ""
        assigned_emails = [x.strip() for x in assigned_str.split(',') if x.strip()]

        # Récupération des candidats (Likes / Pass)
        query_candidates = """--sql
            SELECT 
                u.id, u.nom, u.email, u.tags, u.avatar,
                i.action, i.timestamp,
                s.nom AS client_nom
            FROM utilisateurs u
            LEFT JOIN interactions i ON u.id = i.target_id AND i.project_id = ?
            LEFT JOIN utilisateurs s ON i.swiper_id = s.id
            WHERE u.autorisations = 1
            ORDER BY 
                CASE WHEN i.action = 'LIKE' THEN 1 
                     WHEN i.action = 'PASS' THEN 3
                     ELSE 2 END ASC,
                u.nom ASC
        """
        cursor.execute(query_candidates, (p_id,))
        candidates_raw = cursor.fetchall()
        
        candidates = []
        for c in candidates_raw:
            is_assigned = (c['email'] in assigned_emails)
            date_display = c['timestamp'][:10] if c['timestamp'] else "-"

            candidates.append({
                'id': c['id'],
                'nom': c['nom'],
                'email': c['email'],
                'tags': c['tags'] if c['tags'] else "",
                'avatar': get_avatar(c['email']),
                'action': c['action'],
                'date_like': date_display,
                'client_nom': c['client_nom'],
                'is_assigned': is_assigned
            })

        attribution_data.append({
            'project_id': p_id,
            'project_title': p_title,
            'status': p['status'], # On passe le status au template pour l'afficher éventuellement
            'candidates': candidates
        })

    conn.close()

    # On renvoie aussi les valeurs actuelles des filtres pour pré-remplir le formulaire
    return render_template('attribution.html', 
                           active_page='attribution', 
                           data=attribution_data,
                           current_search=search_query,
                           current_status=filter_status)

@app.route('/gestion_clients', methods=['GET', 'POST'])
@login_required
def gestion_clients():
    
    if current_user.autorisations != 3:
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')

        # AJOUTER UN CLIENT
        if action == 'add-client':
            nom = request.form.get('nom_complet')
            email = request.form.get('email')
            secteur = request.form.get('secteur')
            
            if nom and email:
                try:
                    cursor.execute(
                        "INSERT INTO client (nom_complet, email, secteur) VALUES (?, ?, ?)",
                        (nom, email, secteur)
                    )
                    conn.commit()
                    flash(f"Client '{nom}' ajouté avec succès.", "success")
                except Exception as e:
                    flash(f"Erreur lors de l'ajout : {e}", "danger")

        # SUPPRIMER DES CLIENTS
        elif action == 'delete-clients':
            selected_ids = request.form.getlist('client-ids')
            
            if selected_ids:
                try:
                    
                    sql_list = ', '.join(['?'] * len(selected_ids))
                    cursor.execute(f"DELETE FROM client WHERE id IN ({sql_list})", selected_ids)
                    conn.commit()
                    flash(f"{len(selected_ids)} client(s) supprimé(s).", "success")
                except Exception as e:
                    flash(f"Erreur suppression : {e} (Vérifiez si le client a des projets en cours)", "danger")
            else:
                flash("Aucun client sélectionné pour la suppression.", "warning")

        conn.close()
        return redirect(url_for('gestion_clients'))

    # AFFICHAGE
    cursor.execute("SELECT * FROM client ORDER BY id DESC")
    clients = cursor.fetchall()
    conn.close()

    return render_template('gestion_clients.html', 
                           active_page='gestion_clients', 
                           clients=clients)

# =============================
# LANCEMENT SERVEUR
# =============================
if __name__ == "__main__":
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    ensure_project_tables(cursor)
    conn.commit()
    conn.close()
    app.run(debug=True)
