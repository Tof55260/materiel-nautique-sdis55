from flask import Flask, render_template, request, redirect, session, url_for
from supabase import create_client
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "secret"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

from flask import g

@app.context_processor
def inject_notifs():
    # Valeur par défaut
    return {"nb_notifs": session.get("nb_notifs", 0)}

@app.before_request
def refresh_notifs_count():
    # pas connecté -> rien
    if "login" not in session:
        return

    # uniquement admin : compteur des notifications non lues
    if session.get("role") == "Admin":
        try:
            nb = supabase.table("notifications").select("id").is_("lu", False).execute().data

            session["nb_notifs"] = len(nb)
        except Exception:
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

    nb = supabase.table("notifications").select("*").eq("lu", False).execute().data

    session["nb_notifs"] = len(nb)

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
    qte = int(request.form.get("qte", 1))

    mat = supabase.table("materiels").select("*").eq("id", mid).execute().data[0]
    stock = mat.get("quantite") or 0

    if qte <= 0 or qte > stock:
        return redirect("/inventaire")

    # AFFECTER
    if action == "affecter":

        agent = request.form["agent"]

        supabase.table("materiels").update({
            "quantite": stock - qte
        }).eq("id", mid).execute()

        supabase.table("materiels").insert({
            "nom": mat["nom"],
            "numero_serie": mat["numero_serie"],
            "type": mat["type"],
            "date_controle": mat["date_controle"],
            "statut": "affecte",
            "agent": agent,
            "quantite": qte
        }).execute()

        add_historique(agent, "affectation", mat["nom"])

    # RETOUR STOCK
    if action == "stock":

        supabase.table("materiels").update({
            "statut": "stock",
            "agent": None
        }).eq("id", mid).execute()

        add_historique(session["login"], "retour stock", mat["nom"])

    # REFORME
    if action == "reforme":

        supabase.table("materiels").update({
            "quantite": stock - qte
        }).eq("id", mid).execute()

        add_historique(session["login"], "réforme", mat["nom"])

    return redirect("/inventaire")

# ================= DEMANDE ECHANGE =================

@app.route("/demande_echange", methods=["POST"])
def demande_echange():

    supabase.table("echanges").insert({
        "agent": session["login"],
        "ancien_materiel": request.form["materiel"],
        "statut": "en_attente",
        "date": datetime.now().isoformat()
    }).execute()

    add_historique(session["login"], "demande échange", request.form["materiel"])

    return redirect("/echanges")

@app.route("/admin/demande_echange", methods=["POST"])
def admin_demande_echange():

    if session.get("role") != "Admin":
        return redirect("/accueil")

    agent = request.form["agent"]
    materiel = request.form["materiel"]

    # création échange
    supabase.table("echanges").insert({
        "agent": agent,
        "ancien_materiel": materiel,
        "statut": "en_attente",
        "date": datetime.now().isoformat()
    }).execute()

    # notification ADMIN
    supabase.table("notifications").insert({
        "message": f"Demande échange pour {agent}",
        "lu": False,
        "type": "echange",
        "date": datetime.now().isoformat()
    }).execute()

    add_historique(agent, "demande échange (admin)", materiel)

    return redirect(f"/admin/agent/{agent}")


# ================= ECHANGES =================

@app.route("/echanges")
def echanges():

    e = supabase.table("echanges").select("*").order("date", desc=True).execute().data
    stock = supabase.table("materiels").select("*").eq("statut","stock").execute().data

    return render_template("echanges.html", echanges=e, stock=stock, **session)

@app.route("/valider/<int:id>", methods=["POST"])
def valider(id):

    nouveau = request.form["nouveau"]

    ex = supabase.table("echanges").select("*").eq("id", id).execute().data[0]

    supabase.table("materiels").update({
        "statut":"stock",
        "agent":None
    }).eq("numero_serie", ex["ancien_materiel"]).execute()

    supabase.table("materiels").update({
        "statut":"affecte",
        "agent":ex["agent"]
    }).eq("numero_serie", nouveau).execute()

    supabase.table("echanges").update({
        "statut":"valide",
        "nouveau_materiel":nouveau
    }).eq("id", id).execute()

    add_historique(ex["agent"], "échange validé", nouveau)

    return redirect("/echanges")
    
# ================= NOTIFICATIONS =================

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

    agent = {
        "nom": session.get("nom"),
        "prenom": session.get("prenom"),
        "login": session.get("login"),
        "role": session.get("role")
    }

    mats = supabase.table("materiels").select("*").eq("agent", session["login"]).execute().data

    hist = supabase.table("historique").select("*").eq("agent", session["login"]).order("date", desc=True).execute().data

    return render_template("ma_fiche.html", agent=agent, materiels=mats, historique=hist, **session)

# ================= FICHES AGENTS =================

@app.route("/fiches-agents")
def fiches_agents():

    agents = supabase.table("agents").select("*").execute().data
    return render_template("fiches_agents.html", agents=agents, **session)

@app.route("/admin/agent/<login>")
def fiche_agent_admin(login):

    if session.get("role") != "Admin":
        return redirect("/accueil")

    agent = supabase.table("agents").select("*").eq("login", login).execute().data[0]

    materiels = supabase.table("materiels").select("*").eq("agent", login).execute().data
    historique = supabase.table("historique").select("*").eq("agent", login).order("date", desc=True).execute().data

    return render_template("fiche_agent_admin.html", agent=agent, materiels=materiels, historique=historique, **session)

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
