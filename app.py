import json
import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash

app = Flask(__name__, template_folder="templates")
app.secret_key = "sdis55-nautique"

FICHIER_AGENTS = "agents.json"

# =========================
# OUTILS
# =========================

def charger_agents():
    if not os.path.exists(FICHIER_AGENTS):
        return []
    with open(FICHIER_AGENTS, "r", encoding="utf-8") as f:
        return json.load(f)

def get_agent(login):
    for a in charger_agents():
        if a["login"] == login:
            return a
    return None

def login_requis():
    return "login" in session

def admin_requis():
    return session.get("role") == "Admin"

# =========================
# CONNEXION
# =========================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form["login"].strip()
        password = request.form["password"].strip()

        agent = get_agent(login)

        if agent and check_password_hash(agent["password"], password):
            session["login"] = agent["login"]
            session["nom"] = agent["nom"]
            session["prenom"] = agent["prenom"]
            session["role"] = agent["role"]
            return redirect(url_for("accueil"))

        return render_template("login.html", erreur="Identifiant ou mot de passe incorrect")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =========================
# ACCUEIL
# =========================

@app.route("/accueil")
def accueil():
    if not login_requis():
        return redirect(url_for("login"))

    return render_template(
        "index.html",
        nom=session["nom"],
        prenom=session["prenom"],
        role=session["role"],
        materiels=[]
    )

# =========================
# ÉCHANGES (placeholder stable)
# =========================

@app.route("/echanges")
def page_echanges():
    if not login_requis():
        return redirect(url_for("login"))

    return render_template(
        "echanges.html",
        echanges=[],
        nom=session["nom"],
        prenom=session["prenom"],
        role=session["role"]
    )

# =========================
# ADMIN
# =========================

@app.route("/admin/agents")
def admin_agents():
    if not login_requis() or not admin_requis():
        return redirect(url_for("accueil"))

    return render_template(
        "admin_agents.html",
        agents=charger_agents()
    )

# =========================
# LANCEMENT
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
