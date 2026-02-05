from flask import Flask, render_template, request, redirect, session
from supabase import create_client
from datetime import datetime
import os
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= NOTIFS =================

@app.context_processor
def inject_notifs():
    return {"nb_notifs": session.get("nb_notifs", 0)}

@app.before_request
def refresh_notifs():

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

        login = request.form["login"].strip().lower()
        password = request.form.get("password","")

        agents = supabase.table("agents").select("*").eq("login", login).execute().data

        if agents:

            agent = agents[0]

            if agent["password"] is None:
                session.update(agent)
                return redirect("/premiere-connexion")

            if password == agent["password"]:
                session.update(agent)
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

        supabase.table("materiels").insert({
            "nom": request.form["nom"],
            "numero_serie": request.form["numero"],
            "type": request.form["type"],
            "date_controle": request.form["date"] or None,
            "quantite": int(request.form["quantite"]),
            "statut": "stock"
        }).execute()

        return redirect("/inventaire")

    items = supabase.table("materiels").select("*").neq("statut","reforme").execute().data
    agents = supabase.table("agents").select("*").execute().data

    return render_template("inventaire.html", items=items, agents=agents, **session)

# ================= ECHANGES =================

@app.route("/echanges")
def echanges():

    if "login" not in session:
        return redirect("/")

    e = supabase.table("echanges").select("*").order("date", desc=True).execute().data
    stock = supabase.table("materiels").select("*").eq("statut","stock").execute().data

    return render_template("echanges.html", echanges=e, stock=stock, **session)

# ================= MA FICHE =================

@app.route("/ma-fiche")
def ma_fiche():

    if "login" not in session:
        return redirect("/")

    mats = supabase.table("materiels").select("*").eq("agent",session["login"]).execute().data
    hist = supabase.table("historique").select("*").eq("agent",session["login"]).order("date",desc=True).execute().data

    return render_template("ma_fiche.html", materiels=mats, historique=hist, **session)
@app.route("/ma-fiche")
def ma_fiche():

    if "login" not in session:
        return redirect("/")

    agent = {
        "nom": session.get("nom"),
        "prenom": session.get("prenom"),
        "login": session.get("login"),
        "role": session.get("role")
    }

    mats = supabase.table("materiels") \
        .select("*") \
        .eq("agent", session["login"]) \
        .execute().data

    hist = supabase.table("historique") \
        .select("*") \
        .eq("agent", session["login"]) \
        .order("date", desc=True) \
        .execute().data

    return render_template(
        "ma_fiche.html",
        agent=agent,
        materiels=mats,
        historique=hist,
        **session
    )

# ================= FICHES AGENTS =================

@app.route("/fiches-agents")
def fiches_agents():

    if session.get("role") != "Admin":
        return redirect("/accueil")

    agents = supabase.table("agents").select("*").execute().data
    return render_template("fiches_agents.html", agents=agents, **session)

# ================= ADMIN AGENTS =================

@app.route("/admin/agents")
def admin_agents():

    if session.get("role") != "Admin":
        return redirect("/accueil")

    agents = supabase.table("agents").select("*").execute().data
    return render_template("admin_agents.html", agents=agents, **session)

@app.route("/admin/agents/create", methods=["POST"])
def create_agent():

    nom = request.form["nom"].strip().lower()
    prenom = request.form["prenom"].strip().lower()

    login = (prenom[0] + nom).replace(" ","").replace("-","")

    supabase.table("agents").insert({
        "nom": nom.capitalize(),
        "prenom": prenom.capitalize(),
        "naissance": request.form["naissance"],
        "role": request.form["role"],
        "login": login,
        "password": None
    }).execute()

    return redirect("/admin/agents")

@app.route("/admin/agents/delete", methods=["POST"])
def delete_agent():

    login = request.form.get("login")

    if not login or login == session.get("login"):
        return redirect("/admin/agents")

    supabase.table("materiels").update({
        "agent": None,
        "statut": "stock"
    }).eq("agent", login).execute()

    supabase.table("historique").delete().eq("agent", login).execute()
    supabase.table("echanges").delete().eq("agent", login).execute()
    supabase.table("agents").delete().eq("login", login).execute()

    return redirect("/admin/agents")

# ================= NOTIFICATIONS =================

@app.route("/notifications")
def notifications():

    if session.get("role") != "Admin":
        return redirect("/accueil")

    notes = supabase.table("notifications").select("*").order("date",desc=True).execute().data
    return render_template("notifications.html", notifications=notes, **session)

# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
