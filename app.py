from flask import Flask, render_template, request, redirect, session
from datetime import datetime, date
from supabase import create_client

app = Flask(__name__)
app.secret_key = "sdis55"

SUPABASE_URL = "https://vylcvdfgrcikppxfpztj.supabase.co"
SUPABASE_KEY = "sb_publishable_aDwaBA4DNt4gjIy0ODE23g_eGWA3Az3"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def agents():
    return supabase.table("agents").select("*").execute().data

def get_agent(login):
    r = supabase.table("agents").select("*").eq("login", login).execute().data
    return r[0] if r else None

def materiels():
    return supabase.table("materiels").select("*").execute().data

def full_name(a):
    return f"{a.get('prenom','')} {a.get('nom','')}".strip()

def epi(d):
    try:
        delta = (datetime.strptime(d, "%Y-%m-%d").date() - date.today()).days
        if delta < 0: return "expired"
        if delta < 30: return "warning"
        return "ok"
    except:
        return "ok"

def affectations(login, fullname):
    return supabase.table("affectations").select("*").or_(f"agent.eq.{login},agent.eq.{fullname}").execute().data

def historique(login, fullname):
    return supabase.table("historique").select("*").or_(f"agent.eq.{login},agent.eq.{fullname}").order("date", desc=True).execute().data

# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        a=get_agent(request.form["login"])
        if a and a["password"]==request.form["password"]:
            session.clear()
            session.update(a)
            return redirect("/accueil")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# --------------------------------------------------
# ACCUEIL / MON COMPTE
# --------------------------------------------------

@app.route("/accueil")
def accueil():
    return render_template("index.html",**session)

@app.route("/mon-compte")
def mon_compte():
    return render_template("mon_compte.html",**session)

# --------------------------------------------------
# ADMIN AGENTS
# --------------------------------------------------

@app.route("/admin/agents",methods=["GET","POST"])
def admin_agents():
    if request.method=="POST":
        supabase.table("agents").insert({
            "login":request.form["login"],
            "prenom":request.form["prenom"],
            "nom":request.form["nom"],
            "role":request.form["role"],
            "password":request.form["password"]
        }).execute()

    return render_template("admin_agents.html",agents=agents(),**session)

@app.route("/admin/supprimer/<login>")
def supprimer_agent(login):
    supabase.table("agents").delete().eq("login",login).execute()
    return redirect("/admin/agents")

# --------------------------------------------------
# INVENTAIRE / AFFECTATION
# --------------------------------------------------

@app.route("/inventaire",methods=["GET","POST"])
def inventaire():

    if session.get("role")=="Admin" and request.method=="POST":

        nom=request.form["nom"]
        type_m=request.form["type"]
        stock=int(request.form["stock"])
        controle=request.form["controle"]
        dest=request.form.get("agent")

        if dest=="magasin":
            supabase.table("materiels").insert({
                "nom":nom,
                "type":type_m,
                "stock":stock,
                "controle":controle
            }).execute()

        else:
            for i in range(stock):
                supabase.table("affectations").insert({
                    "agent":dest,
                    "materiel":nom,
                    "date":datetime.now().strftime("%Y-%m-%d"),
                    "controle":controle
                }).execute()

            supabase.table("historique").insert({
                "agent":dest,
                "materiel":nom,
                "action":f"Affectation initiale x{stock}",
                "date":datetime.now().strftime("%Y-%m-%d %H:%M")
            }).execute()

    mats=materiels()
    for m in mats: m["epi"]=epi(m.get("controle"))

    return render_template("inventaire.html",materiels=mats,agents=agents(),**session)

# --------------------------------------------------
# FICHES AGENTS
# --------------------------------------------------

@app.route("/fiches-agents")
def fiches_agents():
    return render_template("fiches_agents.html",agents=agents(),**session)

@app.route("/fiche-agent/<login>")
def fiche_agent(login):

    a=get_agent(login)
    name=full_name(a)

    mats=affectations(login,name)
    hist=historique(login,name)
    mag=materiels()

    for m in mats: m["epi"]=epi(m.get("controle"))

    return render_template("fiche_agent.html",
        agent=a,
        agent_fullname=name,
        materiels=mats,
        magasin=mag,
        hist=hist,
        **session)

# --------------------------------------------------
# ACTION MATERIEL
# --------------------------------------------------

@app.route("/materiel/action",methods=["POST"])
def action_materiel():

    aff_id=request.form["id"]
    agent=request.form["agent_login"]
    fullname=request.form["agent_fullname"]
    mat=request.form["materiel"]
    action=request.form["action"]
    remplace=request.form.get("remplace","")
    controle=request.form.get("controle","")

    supabase.table("affectations").delete().eq("id",aff_id).execute()

    if action=="echange" and remplace:
        supabase.table("affectations").insert({
            "agent":agent,
            "materiel":remplace,
            "date":datetime.now().strftime("%Y-%m-%d"),
            "controle":controle
        }).execute()

    supabase.table("historique").insert({
        "agent":agent,
        "materiel":mat,
        "action":action,
        "date":datetime.now().strftime("%Y-%m-%d %H:%M")
    }).execute()

    return redirect(f"/fiche-agent/{agent}")

# --------------------------------------------------
# MA FICHE
# --------------------------------------------------

@app.route("/ma-fiche")
def ma_fiche():

    login=session["login"]
    a=get_agent(login)
    name=full_name(a)

    mats=affectations(login,name)
    hist=historique(login,name)

    for m in mats: m["epi"]=epi(m.get("controle"))

    return render_template("ma_fiche.html",materiels=mats,hist=hist,**session)

# --------------------------------------------------
# ECHANGES
# --------------------------------------------------

@app.route("/echanges")
def echanges():
    return render_template("echanges.html",**session)

# --------------------------------------------------

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
