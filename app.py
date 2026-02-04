from flask import Flask, render_template, request, redirect, session, url_for
from supabase import create_client
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "secret"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
def add_historique(agent, action, materiel):
    supabase.table("historique").insert({
        "agent": agent,
        "action": action,
        "materiel": materiel,
        "date": datetime.now().isoformat()
    }).execute()

# ================= LOGIN =================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        a = supabase.table("agents").select("*").eq("login", request.form["login"]).execute().data
        if a and a[0]["password"] == request.form["password"]:
            session.update(a[0])
            return redirect("/accueil")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= ACCUEIL =================

@app.route("/accueil")
def accueil():
    if "login" not in session:
        return redirect("/")

    return render_template("index.html", now=datetime.now, **session)

# ================= INVENTAIRE =================

@app.route("/inventaire", methods=["GET", "POST"])
def inventaire():

    if request.method == "POST":
        supabase.table("materiels").insert({
            "nom": request.form["nom"],
            "numero_serie": request.form["numero"],
            "type": request.form["type"],
            "date_controle": request.form["date"],
            "statut": "stock"
        }).execute()

    items = supabase.table("materiels").select("*").execute().data
    agents = supabase.table("agents").select("*").execute().data

    return render_template("inventaire.html", items=items, agents=agents, **session)

@app.route("/action_materiel", methods=["POST"])
def action_materiel():

    mid = request.form.get("id")
    action = request.form.get("action")

    mat = supabase.table("materiels").select("*").eq("id", mid).execute().data[0]
    nom_mat = f"{mat['nom']} ({mat['numero_serie']})"

    if action == "affecter":
        agent = request.form.get("agent")

        supabase.table("materiels").update({
            "statut": "affecte",
            "agent": agent
        }).eq("id", mid).execute()

        add_historique(agent, "Affectation", nom_mat)

    if action == "reforme":

        supabase.table("materiels").update({
            "statut": "reforme",
            "agent": None
        }).eq("id", mid).execute()

        add_historique(session["login"], "Réforme", nom_mat)

    return redirect("/inventaire")



# ================= DEMANDE AGENT =================

@app.route("/demande_echange", methods=["POST"])
def demande_echange():

    supabase.table("echanges").insert({
        "agent": session["login"],
        "ancien_materiel": request.form["materiel"],
        "statut": "en_attente",
        "date": datetime.now().isoformat()
    }).execute()

    supabase.table("notifications").insert({
        "message": f"{session['prenom']} demande un échange",
        "lu": False,
        "date": datetime.now().isoformat()
    }).execute()

    return redirect("/echanges")

# ================= ECHANGES =================

@app.route("/echanges")
def echanges():

    e = supabase.table("echanges").select("*").order("date", desc=True).execute().data
    stock = supabase.table("materiels").select("*").eq("statut", "stock").execute().data

    return render_template("echanges.html", echanges=e, stock=stock, **session)

@app.route("/valider/<int:id>", methods=["POST"])
def valider(id):

    nouveau = request.form["nouveau"]

    ex = supabase.table("echanges").select("*").eq("id", id).execute().data[0]

    supabase.table("materiels").update({
        "statut": "stock",
        "agent": None
    }).eq("numero_serie", ex["ancien_materiel"]).execute()

    supabase.table("materiels").update({
        "statut": "affecte",
        "agent": ex["agent"]
    }).eq("numero_serie", nouveau).execute()

    supabase.table("echanges").update({
        "statut": "valide",
        "nouveau_materiel": nouveau
    }).eq("id", id).execute()

    return redirect("/echanges")
@app.route("/notifications")
def notifications():

    if session.get("role") != "Admin":
        return redirect("/accueil")

    notes = supabase.table("notifications") \
        .select("*") \
        .order("date", desc=True) \
        .execute().data

    return render_template("notifications.html", notifications=notes, **session)


@app.route("/notifications/lu/<int:id>")
def notif_lu(id):

    supabase.table("notifications").update({
        "lu": True
    }).eq("id", id).execute()

    return redirect("/notifications")

# ================= MA FICHE =================

@app.route("/ma-fiche")
def ma_fiche():

    # infos agent depuis session
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

    agents = supabase.table("agents").select("*").execute().data
    return render_template("fiches_agents.html", agents=agents, **session)

# ================= ADMIN =================

@app.route("/admin/agents")
def admin_agents():

    if session.get("role") != "Admin":
        return redirect("/accueil")

    agents = supabase.table("agents").select("*").execute().data
    return render_template("admin_agents.html", agents=agents, **session)

# ================= RUN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
