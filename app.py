from flask import Flask, render_template, request, redirect, session, url_for
from supabase import create_client
from datetime import datetime

SUPABASE_URL = "https://vylcvdfgrcikppxfpztj.supabase.co"
SUPABASE_KEY = "sb_publishable_aDwaBA4DNt4gjIy0ODE23g_eGWA3Az3"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = "sdis55"

# ------------------ UTILS ------------------

def agents():
    return supabase.table("agents").select("*").execute().data

def interventions():
    return supabase.table("interventions").select("*").order("date", desc=True).execute().data

def compteur_annee():
    an = datetime.now().year
    return len(supabase.table("interventions").select("*").eq("annee", an).execute().data)

def agents_par_fonction():
    """
    Hiérarchie:
    CU => SAL + SAS
    SAL => SAS
    SAS => SAS
    """
    ags = agents()
    cu = []
    sal = []
    sas = []

    for a in ags:
        f = (a.get("fonction") or "").upper()
        if f == "CU":
            cu.append(a)
            sal.append(a)
            sas.append(a)
        elif f == "SAL":
            sal.append(a)
            sas.append(a)
        elif f == "SAS":
            sas.append(a)

    return cu, sal, sas

# ------------------ LOGIN ------------------

@app.route("/", methods=["GET","POST"])
def connexion():
    erreur = None

    if request.method == "POST":
        login = request.form["login"]
        pwd = request.form["password"]

        res = supabase.table("agents").select("*").eq("login", login).execute().data

        if res:
            a = res[0]
            # mots de passe EN CLAIR (temporaire)
            if a["password"] == pwd:
                session.clear()
                session.update(a)
                return redirect("/accueil")

        erreur = "Identifiant ou mot de passe incorrect"

    return render_template("login.html", erreur=erreur)

# ------------------ ACCUEIL ------------------

@app.route("/accueil")
def accueil():
    if not session.get("login"):
        return redirect("/")
    return render_template("index.html", compteur=compteur_annee(), **session)

# ------------------ INTERVENTIONS ------------------

@app.route("/interventions", methods=["GET","POST"])
def page_interventions():
    if not session.get("login"):
        return redirect("/")

    cu_list, sal_list, sas_list = agents_par_fonction()

    if request.method == "POST":
        role = request.form["role"]  # CU / SAL / SAS

        cu = request.form.get("cu","")
        sal = request.form.get("sal","")
        sas = request.form.get("sas","")

        # appliquer hiérarchie
        if role == "SAL":
            cu = ""
        if role == "SAS":
            cu = ""
            sal = ""

        supabase.table("interventions").insert({
            "numero": request.form["numero"],
            "date": request.form["date"],
            "nature": request.form["nature"],
            "cu": cu,
            "sal": sal,
            "sas": sas,
            "annee": datetime.now().year
        }).execute()

        return redirect("/interventions")

    return render_template(
        "interventions.html",
        interventions=interventions(),
        cu_list=cu_list,
        sal_list=sal_list,
        sas_list=sas_list,
        **session
    )

# ------------------ ADMIN AGENTS ------------------

@app.route("/admin/agents", methods=["GET","POST"])
def admin_agents():
    if not session.get("login"):
        return redirect("/")
    if session.get("role") != "Admin":
        return redirect("/accueil")

    if request.method == "POST":
        supabase.table("agents").insert({
            "login": request.form["login"],
            "prenom": request.form["prenom"],
            "nom": request.form["nom"],
            "role": request.form["role"],          # Admin / Agent
            "fonction": request.form["fonction"],# CU / SAL / SAS
            "password": request.form["password"] # clair (temporaire)
        }).execute()
        return redirect("/admin/agents")

    return render_template("admin_agents.html", agents=agents(), **session)

# ------------------ LOGOUT ------------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
