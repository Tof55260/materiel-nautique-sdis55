import os,json,csv,subprocess
from datetime import datetime,timedelta
from flask import Flask,render_template,request,redirect,url_for,session,send_file
from werkzeug.security import generate_password_hash,check_password_hash

app=Flask(__name__)
app.secret_key="sdis55"

FILES=["agents.json","materiels.json","affectations.json","echanges.json","retours.json"]

def git_save():
    try:
        subprocess.run(["git","add","."])
        subprocess.run(["git","commit","-m","auto save"],timeout=10)
        subprocess.run(["git","push"],timeout=10)
    except:
        pass

def ensure(f):
    if not os.path.exists(f):
        with open(f,"w") as x:x.write("[]")

for f in FILES: ensure(f)

def load(f):
    with open(f,"r",encoding="utf8") as x:return json.load(x)

def save(f,d):
    with open(f,"w",encoding="utf8") as x:json.dump(d,x,indent=2,ensure_ascii=False)
    git_save()

def agents():return load("agents.json")
def save_agents(x):save("agents.json",x)
def mats():return load("materiels.json")
def save_mats(x):save("materiels.json",x)
def aff():return load("affectations.json")
def save_aff(x):save("affectations.json",x)
def ech():return load("echanges.json")
def save_ech(x):save("echanges.json",x)
def ret():return load("retours.json")
def save_ret(x):save("retours.json",x)

def get(login):
    for a in agents():
        if a["login"]==login:return a

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
    if "login" not in session:return redirect("/")
    return render_template("index.html",**session)

@app.route("/admin/agents",methods=["GET","POST"])
def admin_agents():
    if session.get("role")!="Admin":return redirect("/accueil")
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
    if session.get("role")!="Admin":return redirect("/accueil")
    return render_template("fiches_agents.html",agents=agents(),**session)

@app.route("/inventaire",methods=["GET","POST"])
def inventaire():
    if "login" not in session:return redirect("/")
    m=mats()
    a=agents()
    af=aff()
    if request.method=="POST" and session["role"]=="Admin":
        if request.form["agent"]=="magasin":
            m.append({
                "nom":request.form["nom"],
                "type":request.form["type"],
                "stock":int(request.form["stock"]),
                "controle":request.form["controle"]
            })
            save_mats(m)
        else:
            for i in range(int(request.form["stock"])):
                af.append({
                    "agent":request.form["agent"],
                    "materiel":request.form["nom"],
                    "date":datetime.now().strftime("%d/%m/%Y"),
                    "controle":request.form["controle"]
                })
            save_aff(af)
    return render_template("inventaire.html",materiels=m,agents=a,**session)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
