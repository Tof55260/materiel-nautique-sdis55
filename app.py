import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, template_folder="templates")
app.secret_key = "sdis55-nautique"

# =========================
# ADMIN FIXE (SÉCURISÉ)
# =========================

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("admin55")

# =========================
# FICHIERS JSON
# =========================

FICHIER_AGENTS = "agents.json"
FICHIER_ECHANGES = "echanges.json"

# =========================
# OUTILS AGENTS
# =========================

def charger_agents():
    if not os.path.exists(FICHIER_AGENTS):
        return []
    with open(FICHIER_AGENTS, "r", encoding="utf-8") as f:
        return json.load(f)

def sauvegarder_agents(agents):
    with open(FICHIER_AGENTS, "w", encoding="utf-8") as f:
        json.dump(agents, f, indent=2, ensure_ascii=False)

def get_agent(login):
    for a in charger_agents():
        if a["login"] == login:
            return a
    return None

# =========================
# OUTILS ÉCHANGES
# =========================

def charger_echanges():
    if not os.path.exists(FICHIER_ECHANGES):
        return []
    with open(FICHIER_ECHANGES, "r", encoding="utf-8") as f:
        return json.load(f)

def sauvegarder_echanges(echanges):
    with open(FICHIER_ECHANGES, "w", encoding="utf-8") as f:
        json.dump(echanges, f, indent=2, ensure_ascii=False)

# =========================
# AUTHENTIFICATION
# =========================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form["login"].strip()
        password = request.form["password"].strip()

        # ADMIN
        if login == ADMIN_LOGIN and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.update({
                "login": "admin",
                "nom": "BOUDOT",
                "prenom": "Christophe",
                "role": "Admin"
            })
            return redirect(url_for("accueil"))

        # AGENTS
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
    if "login" not in session:
        return redirect(url_for("login"))

    return render_template(
        "index.html",
        nom=session["nom"],
        prenom=session["prenom"],
        role=session["role"],
        materiels=[]
    )

# =========================
# ADMIN — GESTION DES AGENTS
# =========================

@app.route("/admin/agents", methods=["GET", "POST"])
def admin_agents():
    if session.get("role") != "Admin":
        return redirect(url_for("accueil"))

    agents = charger_agents()

    if request.method == "POST":
        login = request.form["login"].strip()

        if get_agent(login):
            return render_template(
                "admin_agents.html",
                agents=agents,
                erreur="Login déjà existant"
            )

        agents.append({
            "login": login,
            "nom": request.form["nom"].strip(),
            "prenom": request.form["prenom"].strip(),
            "role": request.form["role"],
            "password": generate_password_hash(request.form["password"])
        })

        sauvegarder_agents(agents)
        return redirect(url_for("admin_agents"))

    return render_template("admin_agents.html", agents=agents)

@app.route("/admin/agents/supprimer/<login>")
def supprimer_agent(login):
    if session.get("role") != "Admin":
        return redirect(url_for("accueil"))

    agents = [a for a in charger_agents() if a["login"] != login]
    sauvegarder_agents(agents)
    return redirect(url_for("admin_agents"))

# =========================
# ÉCHANGES — WORKFLOW COMPLET
# =========================

@app.route("/echanges", methods=["GET", "POST"])
def page_echanges():
    if "login" not in session:
        return redirect(url_for("login"))

    echanges = charger_echanges()

    if request.method == "POST":
        echanges.append({
            "id": len(echanges) + 1,
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "agent": f"{session['prenom']} {session['nom']}",
            "profil": session["role"],
            "materiel": request.form["materiel"],
            "motif": request.form["motif"],
            "statut": "En attente"
        })
        sauvegarder_echanges(echanges)
        return redirect(url_for("page_echanges"))

    return render_template(
        "echanges.html",
        echanges=echanges,
        nom=session["nom"],
        prenom=session["prenom"],
        role=session["role"]
    )

@app.route("/echanges/<int:id>/<action>")
def changer_statut(id, action):
    if session.get("role") != "Admin":
        return redirect(url_for("page_echanges"))

    echanges = charger_echanges()

    for e in echanges:
        if e["id"] == id:
            if action == "valider":
                e["statut"] = "Validé"
            elif action == "refuser":
                e["statut"] = "Refusé"

    sauvegarder_echanges(echanges)
    return redirect(url_for("page_echanges"))

# =========================
# LANCEMENT
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
