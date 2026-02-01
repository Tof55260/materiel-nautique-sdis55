from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from supabase import create_client
from datetime import datetime

SUPABASE_URL = "https://vylcvdfgrcikppxfpztj.supabase.co"
SUPABASE_KEY = "sb_publishable_aDwaBA4DNt4gjIy0ODE23g_eGWA3Az3"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = "sdis55"

# ======================
# UTILITAIRES
# ======================

def agents():
    return supabase.table("agents").select("*").execute().data

def inventaire():
    return supabase.table("inventaire").select("*").execute().data

def interventions():
    return supabase.table("interventions").select("*").execute().data

def compteur_annee():
    an = datetime.now().year
    return len(supabase.table("interventions").select("*").eq("annee", an).execute().data)

# ======================
# LOGIN
# ======================

@app.route("/", methods=["GET","POST"])
def connexion():

    if request.method=="POST":
        login=request.form["login"]
        pwd=request.form["password"]

        res=supabase.table("agents").select("*").eq("login",login).execute().data

        if res and check_password_hash(res[0]["password"],pwd):
            session.update(res[0])
            return redirect("/accueil")

    return render_template("login.html")

# ======================
# ACCUEIL
# ======================

@app.route("/accueil")
def accueil():
    return render_template("index.html", compteur=compteur_annee(), **session)

# ======================
# INTERVENTIONS
# ======================

@app.route("/interventions",methods=["GET","POST"])
def page_interventions():

    if request.method=="POST":

        role=request.form["role"]
        cu=request.form.get("cu","")
        sal=request.form.get("sal","")
        sas=request.form.get("sas","")

        if role=="CU":
            pass
        elif role=="SAL":
            cu=""
        elif role=="SAS":
            cu=""
            sal=""

        supabase.table("interventions").insert({
            "numero":request.form["numero"],
            "date":request.form["date"],
            "nature":request.form["nature"],
            "cu":cu,
            "sal":sal,
            "sas":sas,
            "annee":datetime.now().year
        }).execute()

    return render_template(
        "interventions.html",
        interventions=interventions(),
        agents=agents(),
        **session
    )

# ======================
# ADMIN AGENTS
# ======================

@app.route("/admin/agents",methods=["GET","POST"])
def admin_agents():

    if session.get("role")!="Admin":
        return redirect("/accueil")

    if request.method=="POST":

        supabase.table("agents").insert({
            "login":request.form["login"],
            "prenom":request.form["prenom"],
            "nom":request.form["nom"],
            "role":request.form["role"],
            "password":generate_password_hash(request.form["password"])
        }).execute()

    return render_template("admin_agents.html",agents=agents(),**session)

# ======================
# LOGOUT
# ======================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
    
if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
