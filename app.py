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
        agent = request.form.get("agent") or None
        statut = "affecte" if agent else "stock"

        supabase.table("materiels").insert({
            "nom": request.form["nom"],
            "numero_serie": request.form["numero"],
            "type": request.form["type"],
            "date_controle": request.form["date"] or None,
            "quantite": int(request.form["quantite"]),
            "statut": statut,
            "agent": agent
        }).execute()

        if agent:
            add_historique(agent, "affectation directe", request.form["nom"])

        return redirect("/inventaire")

    items = supabase.table("materiels").select("*").neq("statut", "reforme").execute().data
    agents = supabase.table("agents").select("*").execute().data
    return render_template("inventaire.html", items=items, agents=agents, **session)


# ================= ACTION MATERIEL =================
# inventaire + fiche admin utilisent cette route

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

        supabase.table("materiels").update({"quantite": stock - qte}).eq("id", mid).execute()

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

    # RETOUR STOCK
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

    supabase.table("echanges").insert({
        "agent": session["login"],
        "ancien_materiel": materiel,
        "commentaire": commentaire,
        "statut": "en_attente",
        "date": datetime.now().isoformat()
    }).execute()

    # notif admin (si RLS bloque, on ignore)
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

    eid = request.form.get("id")
    nouveau = request.form.get("nouveau")

    if not eid or not nouveau:
        return redirect("/echanges")

    e_list = supabase.table("echanges").select("*").eq("id", eid).execute().data
    if not e_list:
        return redirect("/echanges")

    e = e_list[0]

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

    mats = supabase.table("materiels") \
        .select("*") \
        .eq("agent", session["login"]) \
        .eq("statut", "affecte") \
        .execute().data

    hist = supabase.table("historique") \
        .select("*") \
        .eq("agent", session["login"]) \
        .order("date", desc=True) \
        .execute().data

    my_echanges = supabase.table("echanges") \
        .select("*") \
        .eq("agent", session["login"]) \
        .order("date", desc=True) \
        .execute().data

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

    materiels = supabase.table("materiels") \
        .select("*") \
        .eq("agent", login) \
        .eq("statut", "affecte") \
        .execute().data

    historique = supabase.table("historique") \
        .select("*") \
        .eq("agent", login) \
        .order("date", desc=True) \
        .execute().data

    echanges_agent = supabase.table("echanges") \
        .select("*") \
        .eq("agent", login) \
        .order("date", desc=True) \
        .execute().data

    return render_template(
        "fiche_agent_admin.html",
        agent=agent,
        materiels=materiels,
        historique=historique,
        echanges=echanges_agent,
        **session
    )


# validation/refus depuis fiche agent admin
@app.route("/admin/demande_echange", methods=["POST"])
def admin_demande_echange():
    if session.get("role") != "Admin":
        return redirect("/accueil")

    eid = request.form.get("id")
    action = request.form.get("action")  # valide / refuse

    if not eid or action not in ["valide", "refuse"]:
        return redirect("/echanges")

    supabase.table("echanges").update({"statut": action}).eq("id", eid).execute()
    return redirect("/admin/agent/" + request.form.get("agent", session.get("login", "")))


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

    supabase.table("materiels").update({
        "agent": None,
        "statut": "stock"
    }).eq("agent", login_value).execute()

    try:
        supabase.table("historique").delete().eq("agent", login_value).execute()
    except Exception:
        pass

    try:
        supabase.table("echanges").delete().eq("agent", login_value).execute()
    except Exception:
        pass

    supabase.table("agents").delete().eq("login", login_value).execute()
    return redirect("/admin/agents")
@app.route("/admin/agents/reset_password", methods=["POST"])
def reset_password():

    if session.get("role") != "Admin":
        return redirect("/accueil")

    login_value = request.form.get("login")

    if not login_value:
        return redirect("/admin/agents")

    # empêche reset de soi-même
    if login_value == session.get("login"):
        return redirect("/admin/agents")

    supabase.table("agents").update({
        "password": None
    }).eq("login", login_value).execute()

    return redirect("/admin/agents")
from datetime import date as dt_date

def current_year():
    return datetime.now().year

def can_edit_interventions():
    return session.get("role") in ["Admin", "CU"]

def role_allows_plongeur(role: str) -> bool:
    # CU => plongeur + sas
    # Plongeur => plongeur + sas
    # SAS => sas only
    return role in ["CU", "Plongeur"]

def role_allows_sas(role: str) -> bool:
    return role in ["CU", "Plongeur", "SAS"]

def agents_for_roles():
    """
    Retourne 3 listes d'agents filtrées pour les sélections :
    - cu_list : role == CU
    - plongeurs_list : role in (Plongeur, CU)
    - sas_list : role in (SAS, Plongeur, CU)
    """
    all_agents = supabase.table("agents").select("login,nom,prenom,role").execute().data or []

    cu_list = [a for a in all_agents if a.get("role") == "CU"]
    plongeurs_list = [a for a in all_agents if role_allows_plongeur(a.get("role", ""))]
    sas_list = [a for a in all_agents if role_allows_sas(a.get("role", ""))]

    # tri alpha pour confort
    keyfn = lambda a: (a.get("nom",""), a.get("prenom",""))
    cu_list.sort(key=keyfn)
    plongeurs_list.sort(key=keyfn)
    sas_list.sort(key=keyfn)

    return cu_list, plongeurs_list, sas_list


# ================= ACCUEIL (compteur interventions) =================

# ⚠️ Remplace ta route /accueil par celle-ci si tu veux le compteur
@app.route("/accueil")
def accueil():

    if "login" not in session:
        return redirect("/")

    y = current_year()
    try:
        # Compte des interventions de l'année
        rows = supabase.table("interventions").select("id").eq("annee", y).execute().data or []
        nb_interventions = len(rows)
    except Exception:
        nb_interventions = 0

    return render_template(
        "index.html",
        now=datetime.now,
        nb_interventions=nb_interventions,
        annee_interventions=y,
        **session
    )


# ================= INTERVENTIONS =================

@app.route("/interventions", methods=["GET", "POST"])
def interventions():

    if "login" not in session:
        return redirect("/")

    # année affichée
    y = request.args.get("annee")
    try:
        y = int(y) if y else current_year()
    except ValueError:
        y = current_year()

    # création (Admin/CU uniquement)
    if request.method == "POST":
        if not can_edit_interventions():
            return redirect("/interventions?annee=" + str(y))

        numero = request.form.get("numero", "").strip()
        date_str = request.form.get("date", "").strip()
        lieu = request.form.get("lieu", "").strip()
        motif = request.form.get("motif", "").strip()

        cu = request.form.get("cu") or None
        plongeurs = request.form.getlist("plongeurs")  # multi
        sas = request.form.getlist("sas")              # multi

        if not (numero and date_str and lieu and motif):
            return redirect("/interventions?annee=" + str(y))

        # année calculée depuis la date
        try:
            y_insert = int(date_str[:4])
        except Exception:
            y_insert = y

        supabase.table("interventions").insert({
            "numero": numero,
            "date": date_str,
            "lieu": lieu,
            "motif": motif,
            "annee": y_insert,
            "cu": cu,
            "plongeurs": plongeurs,
            "sas": sas
        }).execute()

        return redirect("/interventions?annee=" + str(y_insert))

    # GET : affichage
    interventions_list = supabase.table("interventions") \
        .select("*") \
        .eq("annee", y) \
        .order("date", desc=True) \
        .execute().data or []

    # années disponibles pour le filtre
    years_rows = supabase.table("interventions").select("annee").execute().data or []
    years = sorted({r.get("annee") for r in years_rows if r.get("annee")}, reverse=True)
    if not years:
        years = [current_year()]

    cu_list, plongeurs_list, sas_list = agents_for_roles()

    # mapping login -> "Prenom NOM"
    all_agents = supabase.table("agents").select("login,nom,prenom").execute().data or []
    name_map = {a["login"]: f"{a.get('prenom','')} {a.get('nom','')}".strip() for a in all_agents}

    return render_template(
        "interventions.html",
        interventions=interventions_list,
        years=years,
        selected_year=y,
        can_edit=can_edit_interventions(),
        cu_list=cu_list,
        plongeurs_list=plongeurs_list,
        sas_list=sas_list,
        name_map=name_map,
        **session
    )


@app.route("/interventions/<int:interv_id>/edit", methods=["GET", "POST"])
def edit_intervention(interv_id):

    if "login" not in session:
        return redirect("/")

    if not can_edit_interventions():
        return redirect("/interventions")

    rows = supabase.table("interventions").select("*").eq("id", interv_id).execute().data or []
    if not rows:
        return redirect("/interventions")

    itv = rows[0]

    if request.method == "POST":
        numero = request.form.get("numero", "").strip()
        date_str = request.form.get("date", "").strip()
        lieu = request.form.get("lieu", "").strip()
        motif = request.form.get("motif", "").strip()

        cu = request.form.get("cu") or None
        plongeurs = request.form.getlist("plongeurs")
        sas = request.form.getlist("sas")

        if not (numero and date_str and lieu and motif):
            return redirect(f"/interventions/{interv_id}/edit")

        try:
            y_insert = int(date_str[:4])
        except Exception:
            y_insert = itv.get("annee") or current_year()

        supabase.table("interventions").update({
            "numero": numero,
            "date": date_str,
            "lieu": lieu,
            "motif": motif,
            "annee": y_insert,
            "cu": cu,
            "plongeurs": plongeurs,
            "sas": sas
        }).eq("id", interv_id).execute()

        return redirect("/interventions?annee=" + str(y_insert))

    cu_list, plongeurs_list, sas_list = agents_for_roles()

    return render_template(
        "intervention_edit.html",
        itv=itv,
        can_edit=True,
        cu_list=cu_list,
        plongeurs_list=plongeurs_list,
        sas_list=sas_list,
        **session
    )




# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
