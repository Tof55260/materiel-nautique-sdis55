import os, json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "sdis55-nautique"

FICHIER_AGENTS="agents.json"
FICHIER_ECHANGES="echanges.json"
FICHIER_MATERIELS="materiels.json"
FICHIER_AFFECTATIONS="affectations.json"
FICHIER_RETOURS="retours.json"

def load_json(p):
    if not os.path.exists(p): return []
    try:
        with open(p,"r",encoding="utf-8") as f: return json.load(f)
    except: return []

def save_json(p,d):
    with open(p,"w",encoding="utf-8") as f:
        json.dump(d,f,indent=2,ensure_ascii=False)

def charger_agents(): return load_json(FICHIER_AGENTS)
def sauvegarder_agents(a): save_json(FICHIER_AGENTS,a)
def charger_echanges(): return load_json(FICHIER_ECHANGES)
def sauvegarder_echanges(e): save_json(FICHIER_ECHANGES,e)
def charger_materiels(): return load_json(FICHIER_MATERIELS)
def sauvegarder_materiels(m): save_json(FICHIER_MATERIELS,m)
def charger_affectations(): return load_json(FICHIER_AFFECTATIONS)
def sauvegarder_affectations(a): save_json(FICHIER_AFFECTATIONS,a)
def charger_retours(): return load_json(FICHIER_RETOURS)
def sauvegarder_retours(r): save_json(FICHIER_RETOURS,r)

def get_agent(login):
    for a in charger_agents():
        if a["login"]==login: return a
    return None

@app.context_processor
def inject():
    return dict(charger_retours=charger_retours)

@app.route("/",methods=["GET","POST"])
def login():
    if request.method=="POST":
        a=get_agent(request.form["login"])
        if a and check_password_hash(a["password"],request.form["password"]):
            session.update(a)
            return redirect(url_for("accueil"))
        return render_template("login.html",erreur="Identifiant incorrect")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/accueil")
def accueil():
    if "login" not in session: return redirect(url_for("login"))
    return render_template("index.html",**session)

@app.route("/mon-compte",methods=["GET","POST"])
def mon_compte():
    if "login" not in session: return redirect(url_for("login"))
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

@app.route("/admin/agents",methods=["GET","POST"])
def admin_agents():
    if session.get("role")!="Admin": return redirect(url_for("accueil"))
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
    agents=charger_agents()
    for a in agents:
        if a["login"]==login:
            a["password"]=generate_password_hash("changeme")
    sauvegarder_agents(agents)
    return redirect(url_for("admin_agents"))

@app.route("/echanges",methods=["GET","POST"])
def echanges():
    if "login" not in session: return redirect(url_for("login"))
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
    e=charger_echanges()
    m=charger_materiels()
    a=charger_affectations()

    for x in e:
        if x["id"]==id and x["statut"]=="En attente":
            if action=="valider":
                x["statut"]="Validé"
                for mat in m:
                    if mat["nom"]==x["materiel"] and mat["stock"]>0:
                        mat["stock"]-=1
                        a.append({
                            "agent":x["agent"],
                            "materiel":x["materiel"],
                            "date":datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "controle":mat["controle"]
                        })
                        break
            else:
                x["statut"]="Refusé"

    sauvegarder_echanges(e)
    sauvegarder_materiels(m)
    sauvegarder_affectations(a)
    return redirect(url_for("echanges"))

@app.route("/inventaire",methods=["GET","POST"])
def inventaire():
    if "login" not in session: return redirect(url_for("login"))
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

    return render_template("inventaire.html",materiels=m,**session)

@app.route("/inventaire/reforme/<int:id>")
def reformer(id):
    m=charger_materiels()
    for x in m:
        if x["id"]==id: x["etat"]="Réformé"
    sauvegarder_materiels(m)
    return redirect(url_for("inventaire"))

@app.route("/ma-fiche")
def ma_fiche():
    nom=session["prenom"]+" "+session["nom"]
    aff=[x for x in charger_affectations() if x["agent"]==nom]
    return render_template("ma_fiche.html",materiels=aff,**session)

@app.route("/fiches-agents")
def fiches_agents():
    if session.get("role")!="Admin": return redirect(url_for("accueil"))
    return render_template("fiches_agents.html",affectations=charger_affectations(),**session)

@app.route("/retour/<int:i>/<action>")
def retour(i,action):
    aff=charger_affectations()
    r=charger_retours()

    mat=aff[i]

    r.append({
        "agent":mat["agent"],
        "materiel":mat["materiel"],
        "date":datetime.now().strftime("%d/%m/%Y %H:%M"),
        "action":action,
        "statut":"En attente"
    })

    del aff[i]

    sauvegarder_affectations(aff)
    sauvegarder_retours(r)

    return redirect(url_for("ma_fiche"))

@app.route("/admin/retours/<int:i>/<decision>")
def admin_retour(i,decision):
    if session.get("role")!="Admin": return redirect(url_for("accueil"))

    r=charger_retours()
    m=charger_materiels()

    if decision=="valider" and r[i]["action"]=="retour":
        for x in m:
            if x["nom"]==r[i]["materiel"]:
                x["stock"]+=1

    r[i]["statut"]="Traité"

    sauvegarder_retours(r)
    sauvegarder_materiels(m)

    return redirect(url_for("fiches_agents"))

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
