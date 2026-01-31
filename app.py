import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, template_folder="templates")
app.secret_key = "sdis55-nautique"

FICHIER_AGENTS = "agents.json"
FICHIER_ECHANGES = "echanges.json"

# =====================
# JSON helpers
# =====================

def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_json(path,data):
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=2,ensure_ascii=False)

# =====================
# AGENTS
# =====================

def charger_agents():
    return load_json(FICHIER_AGENTS)

def sauvegarder_agents(a):
    save_json(FICHIER_AGENTS,a)

def get_agent(login):
    for a in charger_agents():
        if a["login"]==login:
            return a
    return None

# =====================
# LOGIN
# =====================

@app.route("/",methods=["GET","POST"])
def login():
    if request.method=="POST":
        login=request.form["login"]
        password=request.form["password"]

        agent=get_agent(login)

        if agent and check_password_hash(agent["password"],password):
            session.update(agent)
            return redirect(url_for("accueil"))

        return render_template("login.html",erreur="Identifiant ou mot de passe incorrect")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =====================
# ACCUEIL
# =====================

@app.route("/accueil")
def accueil():
    if "login" not in session:
        return redirect(url_for("login"))
    return render_template("index.html",**session)

# =====================
# MON COMPTE (CORRIGÉ)
# =====================

@app.route("/mon-compte",methods=["GET","POST"])
def mon_compte():
    if "login" not in session:
        return redirect(url_for("login"))

    agents=charger_agents()

    if request.method=="POST":
        ancien=request.form["ancien"]
        nouveau=request.form["nouveau"]

        for a in agents:
            if a["login"]==session["login"]:
                if not check_password_hash(a["password"],ancien):
                    return render_template("mon_compte.html",erreur="Ancien mot de passe incorrect",**session)

                a["password"]=generate_password_hash(nouveau)
                sauvegarder_agents(agents)
                return render_template("mon_compte.html",succes="Mot de passe modifié",**session)

    return render_template("mon_compte.html",**session)

# =====================
# ADMIN AGENTS
# =====================

@app.route("/admin/agents",methods=["GET","POST"])
def admin_agents():
    if session.get("role")!="Admin":
        return redirect(url_for("accueil"))

    agents=charger_agents()

    if request.method=="POST":
        agents.append({
            "login":request.form["login"],
            "nom":request.form["nom"],
            "prenom":request.form["prenom"],
            "role":request.form["role"],
            "password":generate_password_hash(request.form["password"])
        })
        sauvegarder_agents(agents)
        return redirect(url_for("admin_agents"))

    return render_template("admin_agents.html",agents=agents,**session)

@app.route("/admin/reset/<login>")
def reset_agent(login):
    if session.get("role")!="Admin":
        return redirect(url_for("accueil"))

    agents=charger_agents()
    for a in agents:
        if a["login"]==login:
            a["password"]=generate_password_hash("changeme")
    sauvegarder_agents(agents)
    return redirect(url_for("admin_agents"))

# =====================
# ECHANGES
# =====================

@app.route("/echanges",methods=["GET","POST"])
def echanges():
    if "login" not in session:
        return redirect(url_for("login"))

    data=load_json(FICHIER_ECHANGES)

    if request.method=="POST":
        data.append({
            "id":len(data)+1,
            "date":datetime.now().strftime("%d/%m/%Y %H:%M"),
            "agent":session["prenom"]+" "+session["nom"],
            "profil":session["role"],
            "materiel":request.form["materiel"],
            "motif":request.form["motif"],
            "statut":"En attente"
        })
        save_json(FICHIER_ECHANGES,data)
        return redirect(url_for("echanges"))

    return render_template("echanges.html",echanges=data,**session)

@app.route("/echanges/<int:id>/<action>")
def statut(id,action):
    if session.get("role")!="Admin":
        return redirect(url_for("echanges"))

    data=load_json(FICHIER_ECHANGES)

    for e in data:
        if e["id"]==id:
            e["statut"]="Validé" if action=="valider" else "Refusé"

    save_json(FICHIER_ECHANGES,data)
    return redirect(url_for("echanges"))

# =====================
# RUN
# =====================

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
