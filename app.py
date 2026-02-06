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
        except Exception:
            session["nb_notifs"] = 0
    else:
        session["nb_notifs"] = 0


# ================= UTIL =================

def add_historique(agent, action, materiel):
    try:
        supabase.table("historique").insert({
            "agent": agent,
            "action": action,
            "materiel": materiel,
            "date": datetime.now().isoformat()
        }).execute()
    except Exception:
        # on ne bloque pas l'app si historique/RLS pose un souci
        pass


# ================= LOGIN =================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form["login"].strip().lower()
        password = request.form.get("password", "")

        agents = supabase.table("agents").select("*").eq("login", login_value).execute().data
        if agents:
            agent = agents[0]

            # première connexion
            if agent.get("password") is None:
                session.update(agent)
                return redirect("/premiere-connexion")

            # connexion normale
            if password == agent.get("password"):
                session.update(agent)
                return redirect("/accueil")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================= PREMIERE CONNEXION =================

@app.route("/premiere-connexion", methods=["GET", "POST"])
def premiere_connexion():
    if "login" not in session:
        return redirect("/")

    if request.method == "POST":
        new_pw = request.form.get("password", "").strip()
        if not new_pw:
            return render_template("premiere_connexion.html", error="Mot de passe requis.")

        supabase.table("agents").update({"password": new_pw}).eq("login", session["login"]).execute()
        return redirect("/accueil")

    return render_template("premiere_connexion.html")


# ================= ACCUEIL =================

@app.route("/accueil")
def accueil():
    if "login" not in session:
        return redirect("/")
    return render_template("index.html", now=datetime.now, **session)


# ================= INVENTAIRE =================

@app.route("/inventaire", methods=["GET", "POST"])
def inventaire():
    if "login" not in session:
        return redirect("/")

    if request.method == "POST":
        supabase.table("materiels").insert({
            "nom": request.form["nom"],
            "numero_serie": request.form["numero"],
            "type": request.form["type"],
            "date_controle": request.form.get("date") or None,
            "quantite": int(request.form["quantite"]),
            "statut": "stock"
        }).execute()

        return redirect("/inventaire")

    items = supabase.table("materiels").select("*").neq("statut", "reforme").execute().data
    agents = supabase.table("agents").select("*").execute().data

    return render_template("inventaire.html", items=items, agents=agents, **session)


# ================= ACTION MATERIEL =================
# (important : inventaire + fiche admin utilisent cette route)

@app.route("/action_materiel", methods=["POST"])
def action_materiel():
    if "login" not in session:
        return redirect("/")

    mid = request.form.get("id")
    action = request.form.get("action")
    qte = int(request.form.get("qte", 1))

    if not mid or not action:
        return redirect("/inventaire")

    mat_list = supabase.table("materiels").select("*").eq("id", mid).execute().data
    if not mat_list:
        return redirect("/inventaire")

    mat = mat_list[0]
    stock = mat.get("quantite") or 0

    if qte <= 0 or qte > stock:
        return redirect("/inventaire")

    # AFFECTER (depuis stock)
    if action == "affecter":
        agent_login = request.form.get("agent", "").strip()
        if not agent_login:
            return redirect("/inventaire")

        # retire du stock
        supabase.table("materiels").update({"quantite": stock - qte}).eq("id", mid).execute()

        # crée ligne affectée
        supabase.table("materiels").insert({
            "nom": mat["nom"],
            "numero_serie": mat.get("numero_serie"),
            "type": mat.get("type"),
            "date_controle": mat.get("date_controle"),
            "statut": "affecte",
            "agent": agent_login,
            "quantite": qte
        }).execute()

        add_historique(agent_login, "affectation", mat["nom"])

    # RETOUR STOCK (depuis fiche agent/admin)
    elif action == "stock":
        supabase.table("materiels").update({
            "statut": "stock",
            "agent": None
        }).eq("id", mid).execute()

        add_historique(session.get("login"), "retour stock", mat["nom"])

    # REFORME (retire qte)
    elif action == "reforme":
        supabase.table("materiels").update({"quantite": stock - qte}).eq("id", mid).execute()
        add_historique(session.get("login"), "réforme", mat["nom"])

    return redirect("/inventaire")


# ================= DEMANDE ECHANGE AGENT =================

@app.route("/demande_echange", methods=["POST"])
def demande_echange():
    if "login" not in session:
        return redirect("/")

    materiel = request.form.get("materiel", "").strip()
    commentaire = request.form.get("commentaire", "").strip()

    if not materiel or not commentaire:
        return redirect("/ma-fiche")

    # création demande
    supabase.table("echanges").insert({
        "agent": session["login"],
        "ancien_materiel": materiel,
        "commentaire": commentaire,
        "statut": "en_attente",
        "date": datetime.now().isoformat()
    }).execute()

    # notification admin (si RLS bloque, on ne casse pas)
    try:
        supabase.table("notifications").insert({
            "message": f"{session.get('prenom', session['login'])} demande un échange : {commentaire}",
            "lu": False,
            "date": datetime.now().isoformat()
        }).execute()
    except Exception:
        pass

    add_historique(session["login"], "demande échange", materiel)

    return redirect("/ma-fiche")


# ================= ECHANGES =================

@app.route("/echanges")
def echanges():
    if "login" not in session:
        return redirect("/")

    e = supabase.table("echanges").select("*").order("date", desc=True).execute().data
    stock = supabase.table("materiels").select("*").eq("statut", "stock").execute().data

    return render_template("echanges.html", echanges=e, stock=stock, **session)
@app.route("/admin/traiter_echange", methods=["POST"])
def traiter_echange():

    if session.get("role") != "Admin":
        return redirect("/accueil")

    eid = request.form["id"]
    nouveau = request.form["nouveau"]

    e = supabase.table("echanges").select("*").eq("id", eid).execute().data[0]

    # ancien retourne stock
    supabase.table("materiels").update({
        "agent": None,
        "statut": "stock"
    }).eq("numero_serie", e["ancien_materiel"]).execute()

    # nouveau affecté agent
    supabase.table("materiels").update({
        "agent": e["agent"],
        "statut": "affecte"
    }).eq("numero_serie", nouveau).execute()

    # échange traité
    supabase.table("echanges").update({
        "statut": "traite",
        "nouveau_materiel": nouveau
    }).eq("id", eid).execute()

    add_historique(e["agent"], "échange traité", nouveau)

    return redirect("/echanges")


# ================= MA FICHE =================

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

    mats = supabase.table("materiels").select("*").eq("agent", session["login"]).execute().data
    hist = supabase.table("historique").select("*").eq("agent", session["login"]).order("date", desc=True).execute().data

    # suivi demandes échange
    my_echanges = supabase.table("echanges").select("*").eq("agent", session["login"]).order("date", desc=True).execute().data

    return render_template(
        "ma_fiche.html",
        agent=agent,
        materiels=mats,
        historique=hist,
        echanges=my_echanges,
        **session
    )


# ================= NOTIFICATIONS =================

@app.route("/notifications")
def notifications():
    if session.get("role") != "Admin":
        return redirect("/accueil")

    notes = supabase.table("notifications").select("*").order("date", desc=True).execute().data
    return render_template("notifications.html", notifications=notes, **session)


@app.route("/notifications/lu/<int:id>")
def notif_lu(id):
    if session.get("role") != "Admin":
        return redirect("/accueil")

    supabase.table("notifications").update({"lu": True}).eq("id", id).execute()
    return redirect("/notifications")


# ================= FICHES AGENTS =================

@app.route("/fiches-agents")
def fiches_agents():
    if session.get("role") != "Admin":
        return redirect("/accueil")

    agents = supabase.table("agents").select("*").execute().data
    return render_template("fiches_agents.html", agents=agents, **session)


# ================= FICHE AGENT ADMIN =================

@app.route("/admin/agent/<login>")
def fiche_agent_admin(login):
    if session.get("role") != "Admin":
        return redirect("/accueil")

    agent_data = supabase.table("agents").select("*").eq("login", login).execute().data
    if not agent_data:
        return redirect("/fiches-agents")

    agent = agent_data[0]

    materiels = supabase.table("materiels").select("*").eq("agent", login).execute().data
    historique = supabase.table("historique").select("*").eq("agent", login).order("date", desc=True).execute().data
    echanges_agent = supabase.table("echanges").select("*").eq("agent", login).order("date", desc=True).execute().data

    return render_template(
        "fiche_agent_admin.html",
        agent=agent,
        materiels=materiels,
        historique=historique,
        echanges=echanges_agent,
        **session
    )
@app.route("/admin/demande_echange", methods=["POST"])
def admin_demande_echange():

    if session.get("role") != "Admin":
        return redirect("/accueil")

    eid = request.form.get("id")
    action = request.form.get("action")   # valide / refuse

    if not eid or action not in ["valide", "refuse"]:
        return redirect("/echanges")

    # mise à jour statut
    supabase.table("echanges").update({
        "statut": action
    }).eq("id", eid).execute()

    # notif agent (optionnel mais sympa)
    try:
        supabase.table("notifications").insert({
            "message": f"Demande d’échange {action}",
            "lu": False,
            "date": datetime.now().isoformat()
        }).execute()
    except:
        pass

    return redirect("/echanges")


# ================= ADMIN AGENTS =================

@app.route("/admin/agents")
def admin_agents():
    if session.get("role") != "Admin":
        return redirect("/accueil")

    agents = supabase.table("agents").select("*").execute().data
    return render_template("admin_agents.html", agents=agents, **session)


@app.route("/admin/agents/create", methods=["POST"])
def create_agent():
    if session.get("role") != "Admin":
        return redirect("/accueil")

    nom = request.form["nom"].strip().lower()
    prenom = request.form["prenom"].strip().lower()
    naissance = request.form["naissance"]
    role = request.form["role"]

    base_login = (prenom[0] + nom).replace(" ", "").replace("-", "")
    login_value = base_login

    # anti-doublon : a, a1, a2...
    i = 1
    while True:
        existing = supabase.table("agents").select("login").eq("login", login_value).execute().data
        if not existing:
            break
        login_value = f"{base_login}{i}"
        i += 1

    supabase.table("agents").insert({
        "nom": nom.capitalize(),
        "prenom": prenom.capitalize(),
        "naissance": naissance,
        "role": role,
        "login": login_value,
        "password": None
    }).execute()

    return redirect("/admin/agents")


@app.route("/admin/agents/delete", methods=["POST"])
def delete_agent():
    if session.get("role") != "Admin":
        return redirect("/accueil")

    login_value = request.form.get("login")

    if not login_value or login_value == session.get("login"):
        return redirect("/admin/agents")

    # remet matériel affecté en stock
    supabase.table("materiels").update({
        "agent": None,
        "statut": "stock"
    }).eq("agent", login_value).execute()

    # supprime traces liées
    try:
        supabase.table("historique").delete().eq("agent", login_value).execute()
    except Exception:
        pass

    try:
        supabase.table("echanges").delete().eq("agent", login_value).execute()
    except Exception:
        pass

    # supprime agent
    supabase.table("agents").delete().eq("login", login_value).execute()

    return redirect("/admin/agents")


# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
