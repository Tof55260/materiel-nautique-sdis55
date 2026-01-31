import os, json
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder="templates")
app.secret_key = "sdis55-nautique"

FICHIER_AGENTS = "agents.json"
FICHIER_ECHANGES = "echanges.json"
FICHIER_MATERIELS = "materiels.json"

# ===================== JSON helpers =====================

def load_json(p):
    if not os.path.exists(p):
        return []
    try:
        with open(p,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_json(p,d):
    with open(p,"w",encoding="utf-8") as f:
        json.dump(d,f,indent=2,ensure_ascii=False)

def charger_agents(): return load_json(FICHIER_AGENTS)
def sauvegarder_agents(a): save_json(FICHIER_AGENTS,a)
def charger_echanges(): return load_json(FICHIER_ECHANGES)
def sauvegarder_echanges(e): save_json(FICHIER_ECHANGES,e)
def charger_materiels(): return load_json(FICHIER_MATERIELS)
def sauvegarder_materiels(m): save_json(FICHIER_MATERIELS,m)

def get_agent(login):
    for a in charger_agents():
        if a["login"]==login:
            return a
    return None

# ===================== LOGIN =====================

@app.route("/",methods=["GET","POST"])
def login():
    if request.method=="POST":
        agent=get_agent(request.form["login"])
        if agent and check_password_hash(agent["password"],request.form["password"]):
            session.update(agent)
            return redirect(url_for("accueil"))
        return render_template("login.html",erreur="Identifiant ou mot de passe incorrect")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ===================== ACCUEIL =====================

@app.route("/accueil")
def accueil():
    if "login" not in session:
        return redirect(url_for("login"))
    return render_template("index.html",**session)

# ===================== MON COMPTE =====================

@app.route("/mon-compte",methods=["GET","POST"])
def mon_compte():
    if "login" not in session:
        return redirect(url_for("login"))

    agents=charger_agents()

    if request.method=="POST":
        for a in agents:
            if a["login"]==session["login"]:
                if not check_password_hash(a["password"],request.form["ancien"]):
                    return render_template("mon_compte.html",erreur="Ancien mot de passe incorrect",**session)
                a["password"]=generate_password_hash(request.form["nouveau"])
                sauvegarder_agents(agents)
                return render_template("mon_compte.html",succes="Mot de passe modifié",**session)

    return render_template("mon_compte.html",**session)

# ===================== ADMIN AGENTS =====================

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

# ===================== ECHANGES =====================

@app.route("/echanges",methods=["GET","POST"])
def echanges():
    if "login" not in session:
        return redirect(url_for("login"))

    e=charger_echanges()

    if request.method=="POST":
        e.append({
            "id":len(e)+1,
            "date":datetime.now().strftime("%d/%m/%Y %H:%M"),
            "agent":session["prenom"]+" "+session["nom"],
            "materiel":request.form["materiel"],
            "motif":request.form["motif"],
            "statut":"En attente"
        })
        sauvegarder_echanges(e)
        return redirect(url_for("echanges"))

    return render_template("echanges.html",echanges=e,**session)

@app.route("/echanges/<int:id>/<action>")
def statut(id,action):
    if session.get("role")!="Admin":
        return redirect(url_for("echanges"))

    e=charger_echanges()
    for x in e:
        if x["id"]==id:
            x["statut"]="Validé" if action=="valider" else "Refusé"
    sauvegarder_echanges(e)
    return redirect(url_for("echanges"))

# ===================== INVENTAIRE =====================

@app.route("/inventaire",methods=["GET","POST"])
def inventaire():
    if "login" not in session:
        return redirect(url_for("login"))

    m=charger_materiels()

    if request.method=="POST" and session.get("role")=="Admin":
        m.append({
            "id":len(m)+1,
            "nom":request.form["nom"],
            "type":request.form["type"],
            "stock":int(request.form["stock"]),
            "controle":request.form["controle"],
            "periodicite":int(request.form["periodicite"]),
            "etat":"Actif"
        })
        sauvegarder_materiels(m)
        return redirect(url_for("inventaire"))

    today=date.today()
    for x in m:
        if x["etat"]!="Actif": continue
        if x["controle"]:
            last=date.fromisoformat(x["controle"])
            delta=(last.replace(year=last.year+x["periodicite"]//12)-today).days
            x["statut"]="retard" if delta<0 else "bientot" if delta<30 else "ok"
        else:
            x["statut"]="ok"

    return render_template("inventaire.html",materiels=m,**session)

@app.route("/inventaire/reforme/<int:id>")
def reformer(id):
    if session.get("role")!="Admin":
        return redirect(url_for("inventaire"))

    m=charger_materiels()
    for x in m:
        if x["id"]==id:
            x["etat"]="Réformé"
    sauvegarder_materiels(m)
    return redirect(url_for("inventaire"))

# ===================== RUN =====================

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
