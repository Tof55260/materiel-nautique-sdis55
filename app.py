import os, json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "sdis55"

FILES = [
    "agents.json",
    "materiels.json",
    "affectations.json",
    "echanges.json",
    "retours.json"
]

def ensure():
    for f in FILES:
        if not os.path.exists(f):
            with open(f,"w") as x:
                x.write("[]")

ensure()

def load(f):
    with open(f,"r",encoding="utf8") as x:
        return json.load(x)

def save(f,d):
    with open(f,"w",encoding="utf8") as x:
        json.dump(d,x,indent=2,ensure_ascii=False)

def agents(): return load("agents.json")
def save_agents(x): save("agents.json",x)
def mats(): return load("materiels.json")
def save_mats(x): save("materiels.json",x)
def aff(): return load("affectations.json")
def save_aff(x): save("affectations.json",x)

def get(login):
    for a in agents():
        if a["login"]==login:
            return a

@app.route("/",methods=["GET","POST"])
def login():
    if request.method=="POST":
        a=get(request.form["login"])
        if a and check_password_hash(a["password"],request.form["password"]):
            session.update(a)
            return redirect("/accueil")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/accueil")
def accueil():
    if "login" not in session:
        return redirect("/")
    return render_template("index.html",**session)

@app.route("/admin/agents",methods=["GET","POST"])
def admin_agents():
    if session.get("role")!="Admin":
        return redirect("/accueil")

    a=agents()

    if request.method=="POST":
        a.append({
            "login":request.form["login"],
            "nom":request.form["nom"],
            "prenom":request.form["prenom"],
            "role":request.form["role"],
            "password":generate_password_hash(request.form["password"])
        })
        save_agents(a)

    return render_template("admin_agents.html",agents=a,**session)

@app.route("/fiches-agents")
def fiches_agents():
    if session.get("role")!="Admin":
        return redirect("/accueil")
    return render_template("fiches_agents.html",agents=agents(),**session)

@app.route("/inventaire",methods=["GET","POST"])
def inventaire():
    if "login" not in session:
        return redirect("/")

    m=mats()
    a=agents()
    af=aff()

    if request.method=="POST" and session["role"]=="Admin":
        nom=request.form["nom"]
        stock=int(request.form["stock"])
        agent=request.form["agent"]
        controle=request.form["controle"]

        if agent=="magasin":
            m.append({
                "nom":nom,
                "type":request.form["type"],
                "stock":stock,
                "controle":controle
            })
            save_mats(m)
        else:
            for i in range(stock):
                af.append({
                    "agent":agent,
                    "materiel":nom,
                    "date":datetime.now().strftime("%d/%m/%Y"),
                    "controle":controle
                })
            save_aff(af)

    return render_template("inventaire.html",materiels=m,agents=a,**session)

@app.route("/ma-fiche")
def ma_fiche():
    nom=session["prenom"]+" "+session["nom"]
    lst=[x for x in aff() if x["agent"]==nom]
    return render_template("ma_fiche.html",materiels=lst,**session)
@app.route("/echanges")
def echanges():
    if "login" not in session:
        return redirect("/")

    return render_template("echanges.html",**session)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
