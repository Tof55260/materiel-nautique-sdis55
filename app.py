from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from werkzeug.security import check_password_hash
from datetime import datetime
import os

# ================= CONFIG =================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = "sdis55"

# ================= HELPERS =================

def get_agents():
    return supabase.table("agents").select("*").execute().data

def get_agent(login):
    r = supabase.table("agents").select("*").eq("login", login).execute().data
    return r[0] if r else None

def inventaire():
    return supabase.table("inventaire").select("*").execute().data

def affectations(agent):
    return supabase.table("affectations").select("*").eq("agent", agent).execute().data

# ================= AUTH =================

@app.route("/", methods=["GET","POST"])
def connexion():
    if request.method == "POST":
        login = request.form["login"]
        pwd = request.form["password"]

        a = get_agent(login)

        if not a:
            return render_template("login.html", erreur="Identifiant incorrect")

        # mot de passe clair OU hashé
        if a["password"].startswith("pbkdf2"):
            ok = check_password_hash(a["password"], pwd)
        else:
            ok = pwd == a["password"]

        if ok:
            session["login"] = a["login"]
            session["nom"] = a["nom"]
            session["prenom"] = a["prenom"]
            session["role"] = a["role"]
            return redirect(url_for("accueil"))

        return render_template("login.html", erreur="Mot de passe incorrect")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("connexion"))

# ================= ACCUEIL =================

@app.route("/accueil")
def accueil():
    if "login" not in session:
        return redirect(url_for("connexion"))
    return render_template("index.html", **session)

# ================= INVENTAIRE =================

@app.route("/inventaire")
def inventaire_page():
    if "login" not in session:
        return redirect(url_for("connexion"))
    return render_template("inventaire.html", items=inventaire(), **session)

# ================= ECHANGES =================

@app.route("/echanges")
def echanges():
    if "login" not in session:
        return redirect(url_for("connexion"))
    return render_template("echanges.html", **session)

# ================= MA FICHE =================

@app.route("/ma-fiche")
def ma_fiche():
    if "login" not in session:
        return redirect(url_for("connexion"))

    mats = affectations(session["login"])
    return render_template("ma_fiche.html", materiel=mats, **session)

# ================= FICHES AGENTS =================

@app.route("/fiches-agents")
def fiches_agents():
    if "login" not in session or session["role"] != "Admin":
        return redirect(url_for("accueil"))

    return render_template("fiches_agents.html", agents=get_agents(), **session)

@app.route("/fiche-agent/<login>")
def fiche_agent(login):
    if "login" not in session or session["role"] != "Admin":
        return redirect(url_for("accueil"))

    agent = get_agent(login)
    mats = affectations(login)

    return render_template("fiche_agent.html", agent=agent, materiel=mats, **session)

# ================= ADMIN =================

@app.route("/admin/agents", methods=["GET","POST"])
def admin_agents():
    if "login" not in session or session["role"] != "Admin":
        return redirect(url_for("accueil"))

    if request.method == "POST":
        supabase.table("agents").insert({
            "login": request.form["login"],
            "nom": request.form["nom"],
            "prenom": request.form["prenom"],
            "role": request.form["role"],
            "password": request.form["password"]
        }).execute()

    return render_template("admin_agents.html", agents=get_agents(), **session)

@app.route("/admin/supprimer/<login>")
def supprimer_agent(login):
    if session["role"]=="Admin":
        supabase.table("agents").delete().eq("login",login).execute()
    return redirect(url_for("admin_agents"))

# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
