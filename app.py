from flask import Flask, render_template, request, redirect, session, send_file
from datetime import datetime, date
from supabase import create_client
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "sdis55"

SUPABASE_URL = "https://vylcvdfgrcikppxfpztj.supabase.co"
SUPABASE_KEY = "sb_publishable_aDwaBA4DNt4gjIy0ODE23g_eGWA3Az3"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

# ---------------- HELPERS ----------------

def agents():
    return supabase.table("agents").select("*").execute().data

def get_agent(login):
    r = supabase.table("agents").select("*").eq("login", login).execute().data
    return r[0] if r else None

def materiels():
    return supabase.table("materiels").select("*").execute().data

def affectations():
    return supabase.table("affectations").select("*").execute().data

def echanges_list():
    return supabase.table("echanges").select("*").execute().data

def epi_status(d):
    try:
        delta = (datetime.strptime(d, "%Y-%m-%d").date() - date.today()).days
        if delta < 0:
            return "expired"
        if delta < 30:
            return "warning"
        return "ok"
    except:
        return "ok"

# ---------------- LOGIN ----------------

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        a = get_agent(request.form["login"])
        if a and a["password"] == request.form["password"]:
            session.update(a)
            return redirect("/accueil")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- ACCUEIL ----------------

@app.route("/accueil")
def accueil():
    if "login" not in session:
        return redirect("/")
    return render_template("index.html", **session)

# ---------------- ADMIN AGENTS ----------------

@app.route("/admin/agents", methods=["GET","POST"])
def admin_agents():
    if session.get("role")!="Admin":
        return redirect("/accueil")

    if request.method=="POST":
        supabase.table("agents").insert({
            "login":request.form["login"],
            "nom":request.form["nom"],
            "prenom":request.form["prenom"],
            "role":request.form["role"],
            "password":request.form["password"]
        }).execute()

    return render_template("admin_agents.html", agents=agents(), **session)

@app.route("/admin/supprimer/<login>")
def supprimer_agent(login):
    supabase.table("agents").delete().eq("login", login).execute()
    return redirect("/admin/agents")

# ---------------- FICHES AGENTS ----------------

@app.route("/fiches-agents")
def fiches_agents():
    if session.get("role")!="Admin":
        return redirect("/accueil")
    return render_template("fiches_agents.html", agents=agents(), **session)

@app.route("/fiche-agent/<login>")
def fiche_agent(login):
    a=get_agent(login)
    nom=a["prenom"]+" "+a["nom"]
    mats=supabase.table("affectations").select("*").eq("agent",nom).execute().data
    for m in mats:
        m["epi"]=epi_status(m.get("controle",""))
    return render_template("fiche_agent.html", agent=a, materiels=mats, **session)

# ---------------- INVENTAIRE ----------------

@app.route("/inventaire", methods=["GET","POST"])
def inventaire():
    if "login" not in session:
        return redirect("/")

    if request.method=="POST" and session["role"]=="Admin":
        nom=request.form["nom"]
        stock=int(request.form["stock"])
        agent=request.form["agent"]
        controle=request.form["controle"]

        if agent=="magasin":
            supabase.table("materiels").insert({
                "nom":nom,
                "type":request.form["type"],
                "stock":stock,
                "controle":controle
            }).execute()
        else:
            for i in range(stock):
                supabase.table("affectations").insert({
                    "agent":agent,
                    "materiel":nom,
                    "date":datetime.now().strftime("%Y-%m-%d"),
                    "controle":controle
                }).execute()

    mats=materiels()
    for m in mats:
        m["epi"]=epi_status(m.get("controle",""))

    return render_template("inventaire.html", materiels=mats, agents=agents(), **session)

# ---------------- MA FICHE ----------------

@app.route("/ma-fiche")
def ma_fiche():
    nom=session["prenom"]+" "+session["nom"]
    mats=supabase.table("affectations").select("*").eq("agent",nom).execute().data
    for m in mats:
        m["epi"]=epi_status(m.get("controle",""))
    return render_template("ma_fiche.html", materiels=mats, **session)

# ---------------- ECHANGES ----------------

@app.route("/echanges")
def echanges():
    return render_template("echanges.html", echanges=echanges_list(), **session)

# ---------------- EXPORT EXCEL ----------------

@app.route("/export/<table>")
def export_excel(table):
    if session.get("role")!="Admin":
        return redirect("/accueil")

    data=supabase.table(table).select("*").execute().data
    df=pd.DataFrame(data)
    fname=f"{EXPORT_DIR}/{table}.xlsx"
    df.to_excel(fname,index=False)
    return send_file(fname, as_attachment=True)

# ---------------- SAUVEGARDE AUTO ----------------

@app.route("/backup")
def backup():
    for t in ["agents","materiels","affectations","echanges"]:
        data=supabase.table(t).select("*").execute().data
        pd.DataFrame(data).to_csv(f"{EXPORT_DIR}/{t}.csv",index=False)
    return "Backup OK"

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
