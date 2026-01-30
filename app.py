import json
import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder="templates")
app.secret_key = "sdis55-nautique"

FICHIER_AGENTS = "agents.json"
FICHIER_ECHANGES = "echanges.json"

materiels = []

# ======================
# OUTILS JSON
# ======================

def charger_json(fichier):
    if not os.path.exists(fichier):
        return []
    with open(fichier, "r", encoding="utf-8") as f:
        return json.load(f)

def sauvegarder_json(fichier, data):
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_agent(login):
    agents = charger_json(FICHIER_AGENTS)
    for a in agents:
        if a["login"] == login:
            return a
    return None

# ======================
# AUTHENTIFICATION
# ======================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form["login"]
        password = request.form["password"]

        agent = get_agent(login)
        if agent and check_password_hash(agent["password"], password):
            session["login"] = agent["login"]
            session["nom"] = agent["nom"]
            session["prenom"] = agent["prenom"]
            session["role"] = agent["role"]
            return redirect(url_for("accueil"))

        return render_template("login.html", erreur="Identifiants incorrects")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def login_requis():
    return "login" in session

def admin_requis():
    return session.get("role") == "Admin"

# ======================
# PAGES PRINCIPALES
# ======================

@app.route("/accueil")
def accueil():
    if not login_requis():
        return redirect(url_for("login"))

    return render_template(
        "index.html",
        materiels=materiels,
        nom=session["nom"],
        prenom=session["prenom"],
        role=session["role"]
    )

# ======================
# ADMIN — GESTION DES AGENTS
# ======================

@app.route("/admin/agents", methods=["GET", "POST"])
def admin_agents():
    if not login_requis() or not admin_requis():
        return redirect(url_for("accueil"))

    agents = charger_json(FICHIER_AGENTS)

    if request.method == "POST":
        agents.append({
            "login": request.form["login"],
            "nom": request.form["nom"],
            "prenom": request.form["prenom"],
            "role": request.form["role"],
            "password": generate_password_hash(request.form["password"])
        })
        sauvegarder_json(FICHIER_AGENTS, agents)

    return render_template("admin_agents.html", agents=agents)

# ======================
# ÉCHANGES
# ======================

@app.route("/echanges", methods=["GET", "POST"])
def echanges():
    if not login_requis():
        return redirect(url_for("login"))

    echanges = charger_json(FICHIER_ECHANGES)

    if request.method == "POST":
        echanges.append({
            "id": len(echanges) + 1,
            "agent": f"{session['prenom']} {session['nom']}",
            "profil": session["role"],
            "materiel": request.form["materiel"],
            "motif": request.form["motif"],
            "statut": "En attente"
        })
        sauvegarder_json(FICHIER_ECHANGES, echanges)

    return render_template(
        "echanges.html",
        echanges=echanges,
        nom=session["nom"],
        prenom=session["prenom"],
        role=session["role"]
    )

# ======================
# LANCEMENT
# ======================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
