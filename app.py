import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, template_folder="templates")
app.secret_key = "sdis55-nautique"

FICHIER_AGENTS = "agents.json"
FICHIER_ECHANGES = "echanges.json"

# =========================
# OUTILS JSON
# =========================

def charger_json(fichier, default):
    if not os.path.exists(fichier):
        return default
    try:
        with open(fichier, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

def sauvegarder_json(fichier, data):
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# =========================
# AGENTS
# =========================

def charger_agents():
    return charger_json(FICHIER_AGENTS, [])

def sauvegarder_agents(agents):
    sauvegarder_json(FICHIER_AGENTS, agents)

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
# AUTHENTIFICATION
# =========================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form["login"].strip()
        password = request.form["password"].strip()

        agent = get_agent(login)
        if agent and check_password_hash(agent["password"], password):
            session.update({
                "login": agent["login"],
                "nom": agent["nom"],
                "prenom": agent["prenom"],
                "role": agent["role"]
            })
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
        role=session["role"]
    )

# =========================
# MON COMPTE (CHANGER MOT DE PASSE)
# =========================

@app.route("/mon-compte", methods=["GET", "POST"])
def mon_compte():
    if not login_requis():
        return redirect(url_for("login"))

    agents = charger_agents()
    agent = get_agent(session["login"])

    if request.method == "POST":
        ancien = request.form["ancien"]
        nouveau = request.form["nouveau"]

        if not check_password_hash(agent["password"], ancien):
            return render_template("mon_compte.html", erreur="Ancien mot de passe incorrect")

        agent["password"] = generate_password_hash(nouveau)
        sauvegarder_agents(agents)
        return render_template("mon_compte.html", succes="Mot de passe modifié")

    return render_template("mon_compte.html")

# =========================
# ADMIN — GESTION DES AGENTS
# =========================

@app.route("/admin/agents", methods=["GET", "POST"])
def admin_agents():
    if not admin_requis():
        return redirect(url_for("accueil"))

    agents = charger_agents()

    if request.method == "POST":
        login = request.form["login"]

        if get_agent(login):
            return render_template("admin_agents.html", agents=agents, erreur="Login existant")

        agents.append({
            "login": login,
            "nom": request.form["nom"],
            "prenom": request.form["prenom"],
            "role": request.form["role"],
            "password": generate_password_hash(request.form["password"])
        })
        sauvegarder_agents(agents)
        return redirect(url_for("admin_agents"))

    return render_template("admin_agents.html", agents=agents)

@app.route("/admin/agents/reset/<login>")
def reset_mdp_agent(login):
    if not admin_requis():
        return redirect(url_for("accueil"))

    agents = charger_agents()
    for a in agents:
        if a["login"] == login:
            a["password"] = generate_password_hash("changeme")
            sauvegarder_agents(agents)
            break

    return redirect(url_for("admin_agents"))

# =========================
# ÉCHANGES (inchangé)
# =========================

@app.route("/echanges", methods=["GET", "POST"])
def page_echanges():
    if not login_requis():
        return redirect(url_for("login"))

    echanges = charger_json(FICHIER_ECHANGES, [])

    if request.method == "POST":
        echanges.append({
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "agent": f"{session['prenom']} {session['nom']}",
            "profil": session["role"],
            "materiel": request.form["materiel"],
            "motif": request.form["motif"],
            "statut": "En attente"
        })
        sauvegarder_json(FICHIER_ECHANGES, echanges)

    return render_template("echanges.html", echanges=echanges)

# =========================
# LANCEMENT
# =========================
print("HASH ADMIN =", generate_password_hash("admin55"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
