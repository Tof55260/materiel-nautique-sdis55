import os
from functools import wraps
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash

from supabase import create_client
from werkzeug.security import check_password_hash


# ---------------- APP ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "sdis55-nautique")


# ---------------- SUPABASE ----------------
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    # Pour éviter un crash Render si variables non mises
    # (tu verras le message sur la page)
    supabase = None
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------- HELPERS ----------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("login"):
            return redirect(url_for("connexion"))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("login"):
            return redirect(url_for("connexion"))
        if session.get("role") != "Admin":
            return redirect(url_for("accueil"))
        return fn(*args, **kwargs)
    return wrapper


def supa_ok_or_error_page():
    """Retourne une page d'erreur lisible si supabase non configuré."""
    if supabase is None:
        return render_template(
            "login.html",
            error="Supabase non configuré : ajoute SUPABASE_URL et SUPABASE_KEY dans Render (Environment)."
        )
    return None


def agents():
    """Liste des agents depuis Supabase table agents."""
    res = supabase.table("agents").select("*").execute()
    return res.data or []


def get_agent_by_login(login):
    res = supabase.table("agents").select("*").eq("login", login).limit(1).execute()
    data = res.data or []
    return data[0] if data else None


def password_match(stored_password, entered_password) -> bool:
    """
    Supporte:
      - mot de passe hashé werkzeug (pbkdf2/scrypt/argon2)
      - mot de passe en clair (fallback)
    """
    if stored_password is None:
        return False

    stored_password = str(stored_password)

    # Si ça ressemble à un hash werkzeug (ex: "scrypt:...", "pbkdf2:...")
    if ":" in stored_password and "$" in stored_password:
        try:
            return check_password_hash(stored_password, entered_password)
        except Exception:
            # hash invalide => fallback en clair
            return stored_password == entered_password

    # Sinon, on compare en clair
    return stored_password == entered_password


# ---------------- ROUTES ----------------

# ---- LOGIN (plusieurs noms pour compat templates) ----
@app.route("/", methods=["GET", "POST"], endpoint="connexion")
@app.route("/login", methods=["GET", "POST"], endpoint="login")        # alias
@app.route("/connecter", methods=["GET", "POST"], endpoint="connecter")  # alias
def connexion():
    err = supa_ok_or_error_page()
    if err:
        return err

    if request.method == "POST":
        login = request.form.get("login", "").strip()
        password = request.form.get("password", "").strip()

        a = get_agent_by_login(login)

        if not a:
            return render_template("login.html", error="Identifiant ou mot de passe incorrect")

        if not password_match(a.get("password"), password):
            return render_template("login.html", error="Identifiant ou mot de passe incorrect")

        # Session
        session["login"] = a.get("login")
        session["nom"] = a.get("nom") or ""
        session["prenom"] = a.get("prenom") or ""
        session["role"] = a.get("role") or "Agent"
        session["fonction"] = a.get("fonction") or ""

        return redirect(url_for("accueil"))

    return render_template("login.html")


# ---- LOGOUT (plusieurs noms pour compat templates) ----
@app.route("/logout", endpoint="logout")
@app.route("/deconnecter", endpoint="deconnecter")  # alias
def logout():
    session.clear()
    return redirect(url_for("connexion"))


# ---- ACCUEIL ----
@app.route("/accueil", endpoint="accueil")
@login_required
def accueil():
    # On fournit "now" aux templates si tu l'utilises
    return render_template("index.html", now=datetime.now, **session)


# ---- ECHANGES (plusieurs endpoints pour compat templates) ----
@app.route("/echanges", endpoint="echanges")
@app.route("/page-echanges", endpoint="page_echanges")  # alias
@login_required
def echanges():
    # Si ton echanges.html attend d'autres variables plus tard, tu pourras les ajouter ici
    return render_template("echanges.html", now=datetime.now, **session)


# ---- INVENTAIRE (plusieurs endpoints pour compat templates) ----
@app.route("/inventaire", endpoint="inventaire")
@app.route("/inventaire-page", endpoint="inventaire_page")  # alias
@login_required
def inventaire():
    err = supa_ok_or_error_page()
    if err:
        return err

    # Table inventaire : adapte si ton nom de table est différent
    # (chez toi ça a souvent été "materiel" / "inventaire")
    # On essaye "inventaire" puis fallback "materiel".
    items = []
    try:
        items = supabase.table("inventaire").select("*").execute().data or []
    except Exception:
        items = supabase.table("materiel").select("*").execute().data or []

    return render_template("inventaire.html", items=items, now=datetime.now, **session)


# ---- MA FICHE (plusieurs endpoints pour compat templates) ----
@app.route("/ma-fiche", endpoint="ma_fiche")
@app.route("/mon-compte", endpoint="mon_compte")  # alias si tes templates utilisent mon_compte
@login_required
def ma_fiche():
    err = supa_ok_or_error_page()
    if err:
        return err

    # Ton app a déjà utilisé "nom" comme clé d'agent dans certaines tables
    agent_key = session.get("nom") or session.get("login")

    # Fallback safe : si table affectations n'existe pas, on affiche vide sans crash.
    materiel = []
    try:
        materiel = supabase.table("affectations").select("*").eq("agent", agent_key).execute().data or []
    except Exception:
        materiel = []

    return render_template("ma_fiche.html", materiel=materiel, now=datetime.now, **session)


# ---- FICHES AGENTS (ADMIN ONLY) ----
@app.route("/fiches-agents", endpoint="fiches_agents")
@admin_required
def fiches_agents():
    err = supa_ok_or_error_page()
    if err:
        return err

    return render_template("fiches_agents.html", agents=agents(), now=datetime.now, **session)


# ---- ADMIN (ADMIN ONLY) ----
@app.route("/admin/agents", endpoint="admin_agents")
@admin_required
def admin_agents():
    err = supa_ok_or_error_page()
    if err:
        return err

    return render_template("admin_agents.html", agents=agents(), now=datetime.now, **session)


# ---------------- START ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
