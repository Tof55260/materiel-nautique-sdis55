from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from supabase import create_client

app = Flask(__name__)
app.secret_key = "sdis55"

SUPABASE_URL = "https://vylcvdfgrcikppxfpztj.supabase.co"
SUPABASE_KEY = "sb_publishable_aDwaBA4DNt4gjIy0ODE23g_eGWA3Az3"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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

def echanges():
    return supabase.table("echanges").select("*").execute().data

# ---------------- LOGIN ----------------

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        a = get_agent(request.form["login"])

        # LOGIN EN CLAIR (TEMPORAIRE)
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

# ---------------- MON COMPTE ----------------

@app.route("/mon-compte")
def mon_compte():
    return render_template("mon_compte.html", **session)

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

# ---------------- FICHES AGENTS ----------------

@app.route("/fiches-agents")
def fiches_agents():
    if session.get("role")!="Admin":
        return redirect("/accueil")
    return render_template("fiches_agents.html", agents=agents(), **session)

@app.route("/fiche-agent/<login>")
def fiche_agent(login):
    if session.get("role")!="Admin":
        return redirect("/accueil")

    a = get_agent(login)
    nom = a["prenom"]+" "+a["nom"]
    mats = supabase.table("affectations").select("*").eq("agent",nom).execute().data

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
                    "date":datetime.now().strftime("%d/%m/%Y"),
                    "controle":controle
                }).execute()

    return render_template(
        "inventaire.html",
        materiels=materiels(),
        agents=agents(),
        **session
    )

# ---------------- MA FICHE ----------------

@app.route("/ma-fiche")
def ma_fiche():
    nom=session["prenom"]+" "+session["nom"]
    mats=supabase.table("affectations").select("*").eq("agent",nom).execute().data
    return render_template("ma_fiche.html", materiels=mats, **session)

# ---------------- ECHANGES ----------------

@app.route("/echanges")
def page_echanges():
    return render_template("echanges.html", echanges=echanges(), **session)

# ---------------- MAIN ----------------

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)
