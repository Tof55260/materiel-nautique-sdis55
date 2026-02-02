from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from werkzeug.security import check_password_hash
import os

app = Flask(__name__)
app.secret_key = "secret123"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- LOGIN ----------------

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        login = request.form["login"]
        password = request.form["password"]

        res = supabase.table("agents").select("*").eq("login",login).execute().data

        if not res:
            return render_template("login.html", erreur="Identifiant incorrect")

        agent = res[0]

        if agent["password"] != password:
            return render_template("login.html", erreur="Mot de passe incorrect")

        session["login"] = agent["login"]
        session["role"] = agent["role"]
        session["prenom"] = agent["prenom"]
        session["nom"] = agent["nom"]

        return redirect(url_for("accueil"))

    return render_template("login.html")

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- ACCUEIL ----------------

@app.route("/accueil")
def accueil():
    if "login" not in session:
        return redirect(url_for("login"))

    return render_template("index.html", **session)

# ---------------- INVENTAIRE ----------------

@app.route("/inventaire")
def inventaire():
    if "login" not in session:
        return redirect(url_for("login"))

    items = supabase.table("inventaire").select("*").execute().data
    return render_template("inventaire.html", items=items, **session)

# ---------------- ECHANGES ----------------

@app.route("/echanges")
def echanges():
    if "login" not in session:
        return redirect(url_for("login"))

    return render_template("echanges.html", **session)

# ---------------- MA FICHE ----------------

@app.route("/ma-fiche")
def ma_fiche():
    if "login" not in session:
        return redirect(url_for("login"))

    return render_template("ma_fiche.html", **session)

# ---------------- ADMIN ----------------

@app.route("/admin/agents")
def admin_agents():
    if session.get("role") != "Admin":
        return redirect(url_for("accueil"))

    agents = supabase.table("agents").select("*").execute().data
    return render_template("admin_agents.html", agents=agents, **session)

# ---------------- FICHES AGENTS ----------------

@app.route("/fiches-agents")
def fiches_agents():
    if session.get("role") != "Admin":
        return redirect(url_for("accueil"))

    agents = supabase.table("agents").select("*").execute().data
    return render_template("fiches_agents.html", agents=agents, **session)

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
