import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session

from supabase import create_client
from postgrest.exceptions import APIError

app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "sdis55-nautique")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL / SUPABASE_KEY manquants dans Render (Environment Variables).")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# -------------------------
# Helpers
# -------------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("login"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def safe_select(table_name: str, **filters):
    """
    Retourne une liste (jamais une erreur 500) même si la table n'existe pas.
    """
    try:
        q = supabase.table(table_name).select("*")
        for k, v in filters.items():
            q = q.eq(k, v)
        data = q.execute().data
        return data or []
    except APIError:
        return []


def get_agent(login: str):
    rows = safe_select("agents", login=login)
    return rows[0] if rows else {}


@app.context_processor
def inject_now():
    return {"now": datetime.now}


# -------------------------
# Auth
# -------------------------
@app.route("/", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "POST":
        login = request.form.get("login", "").strip()
        password = request.form.get("password", "").strip()

        agent = get_agent(login)
        # IMPORTANT: chez toi, tu as eu des passwords en clair (admin55/test)
        # => on accepte comparaison simple pour la démo.
        if agent and (agent.get("password") == password):
            session["login"] = agent.get("login")
            session["role"] = agent.get("role", "Agent")
            session["nom"] = agent.get("nom", "")
            session["prenom"] = agent.get("prenom", "")
            session["fonction"] = agent.get("fonction", "")
            return redirect(url_for("accueil"))

        return render_template("login.html", error="Identifiant ou mot de passe incorrect")

    return render_template("login.html", error=None)


@app.route("/logout", endpoint="logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -------------------------
# Pages DEMO
# -------------------------
@app.route("/accueil", endpoint="accueil")
@login_required
def accueil():
    return render_template("index.html", **session)


@app.route("/inventaire", endpoint="inventaire")
@login_required
def inventaire():
    # Ta table est bien "materiels"
    items = safe_select("materiels")
    return render_template("inventaire.html", items=items, **session)


@app.route("/echanges", endpoint="echanges")
@login_required
def echanges():
    # Si la table "echanges" existe => on affiche
    demandes = safe_select("echanges")
    return render_template("echanges.html", demandes=demandes, **session)


@app.route("/ma-fiche", endpoint="ma_fiche")
@login_required
def ma_fiche():
    agent = get_agent(session.get("login"))

    # affectations : si tu as une table affectations
    affectations = []
    try:
        # si tu as une table "affectations" avec colonne "agent_login"
        aff = supabase.table("affectations").select("*").eq("agent_login", session.get("login")).execute().data or []
        # si tu stockes juste des IDs de materiel, adapte ici si besoin.
        # Pour la démo: on affiche directement les champs s'ils sont dans affectations.
        affectations = aff
    except APIError:
        affectations = []

    # SÉCURITÉ: agent existe toujours (dict)
    if not agent:
        agent = {
            "login": session.get("login", ""),
            "nom": session.get("nom", ""),
            "prenom": session.get("prenom", ""),
            "role": session.get("role", ""),
            "fonction": session.get("fonction", "")
        }

    return render_template("ma_fiche.html", agent=agent, affectations=affectations, **session)


# -------------------------
# Stubs (si tes templates les appellent)
# -------------------------
@app.route("/fiches-agents", endpoint="fiches_agents")
@login_required
def fiches_agents():
    # pour éviter 500 si quelqu'un clique
    if session.get("role") != "Admin":
        return redirect(url_for("accueil"))
    return render_template("fiches_agents.html", agents=safe_select("agents"), **session)


@app.route("/admin/agents", endpoint="admin_agents")
@login_required
def admin_agents():
    if session.get("role") != "Admin":
        return redirect(url_for("accueil"))
    return render_template("admin_agents.html", agents=safe_select("agents"), **session)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
