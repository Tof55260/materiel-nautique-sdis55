from flask import Flask, render_template, request, redirect, session, url_for
from supabase import create_client
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "secret"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= NOTIFS =================

@app.context_processor
def inject_notifs():
    return {"nb_notifs": session.get("nb_notifs", 0)}

@app.before_request
def refresh_notifs_count():

    if "login" not in session:
        return

    if session.get("role") == "Admin":
        try:
            nb = supabase.table("notifications").select("id").is_("lu", False).execute().data
            session["nb_notifs"] = len(nb)
        except:
            session["nb_notifs"] = 0
    else:
        session["nb_notifs"] = 0

# ================= UTIL =================

def add_historique(agent, action, materiel):
    supabase.table("historique").insert({
        "agent": agent,
        "action": action,
        "materiel": materiel,
        "date": datetime.now().isoformat()
    }).execute()

# ================= LOGIN =================

@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        a = supabase.table("agents").select("*").eq("login", request.form["login"]).execute().data

        if a and a[0]["password"] == request.form["password"]:

            session.update(a[0])

            if a[0]["password"] == "TEMP":
                return redirect("/premiere-connexion")

            return redirect("/accueil")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= PREMIERE CONNEXION =================

@app.route("/premiere-connexion", methods=["GET","POST"])
def premiere_connexion():

    if "login" not in session:
        return redirect("/")

    if request.method == "POST":

        supabase.table("agents").update({
            "password": request.form["password"]
        }).eq("login", session["login"]).execute()

        return redirect("/accueil")

    return render_template("premiere_connexion.html")

# ================= ACCUEIL =================

@app.route("/accueil")
def accueil():

    if "login" not in session:
        return redirect("/")

    return render_template("index.html", now=datetime.now, **session)

# ================= INVENTAIRE =================

@app.route("/inventaire", methods=["GET","POST"])
def inventaire():

    if "login" not in session:
        return redirect("/")

    if request.method == "POST":

        date = request.form["date"] or None

        supabase.table("materiels").insert({
            "nom": request.form["nom"],
            "numero_serie": request.form["numero"],
            "type": request.form["type"],
            "date_controle": date,
            "quantite": int(request.form["quantite"]),
            "statut": "stock"
        }).execute()

        return redirect("/inventaire")

    items = supabase.table("materiels").select("*").neq("statut","reforme").execute().data
    agents = supabase.table("agents").select("*").execute().data

    return render_template("inventaire.html", items=items, agents=agents, **session)

# ================= ACTION MATERIEL =================

@app.route("/action_materiel", methods=["POST"])
def action_materiel():

    mid = request.form["id"]
    action = request.form["action"]
    qte = int(request.form.get("qte",1))

    mat = supabase.table("materiels").select("*").eq("id",mid).execute().data[0]
    stock = mat.get("quantite") or 0

    if qte <= 0 or qte > stock:
        return redirect("/inventaire")

    if action == "affecter":

        agent = request.form["agent"]

        supabase.table("materiels").update({
            "quantite": stock-qte
        }).eq("id",mid).execute()

        supabase.table("materiels").insert({
            "nom":mat["nom"],
            "numero_serie":mat["numero_serie"],
            "type":mat["type"],
            "date_controle":mat["date_controle"],
            "statut":"affecte",
            "agent":agent,
            "quantite":qte
        }).execute()

        add_historique(agent,"affectation",mat["nom"])

    if action == "stock":

        supabase.table("materiels").update({
            "statut":"stock",
            "agent":None
        }).eq("id",mid).execute()

        add_historique(session["login"],"retour stock",mat["nom"])

    if action == "reforme":

        supabase.table("materiels").update({
            "quantite":stock-qte
        }).eq("id",mid).execute()

        add_historique(session["login"],"réforme",mat["nom"])

    return redirect("/inventaire")

# ================= ADMIN AGENTS =================

@app.route("/admin/agents")
def admin_agents():

    if session.get("role")!="Admin":
        return redirect("/accueil")

    agents=supabase.table("agents").select("*").execute().data
    return render_template("admin_agents.html",agents=agents,**session)

@app.route("/admin/agents/create",methods=["POST"])
def create_agent():

    if session.get("role")!="Admin":
        return redirect("/accueil")

    nom=request.form["nom"].strip().lower()
    prenom=request.form["prenom"].strip().lower()
    naissance=request.form["naissance"]
    role=request.form["role"]

    login=prenom[0]+nom
    login=login.replace(" ","").replace("-","")

    supabase.table("agents").insert({
        "nom":nom.capitalize(),
        "prenom":prenom.capitalize(),
        "naissance":naissance,
        "role":role,
        "login":login,
        "password":"TEMP"
    }).execute()

    return redirect("/admin/agents")

# ================= RUN =================

if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)
