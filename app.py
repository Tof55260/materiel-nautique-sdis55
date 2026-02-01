from flask import Flask, render_template, request, redirect, session
from datetime import datetime, date
from supabase import create_client

app = Flask(__name__)
app.secret_key = "sdis55"

SUPABASE_URL = "https://vylcvdfgrcikppxfpztj.supabase.co"
SUPABASE_KEY = "sb_publishable_aDwaBA4DNt4gjIy0ODE23g_eGWA3Az3"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- HELPERS ----------------

def require_login():
    return "login" in session

def require_admin():
    return session.get("role") == "Admin"

def agents():
    return supabase.table("agents").select("*").execute().data

def get_agent(login):
    r = supabase.table("agents").select("*").eq("login", login).execute().data
    return r[0] if r else None

def materiels_magasin():
    # On récupère tout le magasin (même stock=0), pour afficher des choix
    return supabase.table("materiels").select("*").execute().data

def full_name(agent_row):
    prenom = (agent_row.get("prenom") or "").strip()
    nom = (agent_row.get("nom") or "").strip()
    return (prenom + " " + nom).strip()

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

def affectations_for(login, fullname):
    # Compat : certaines lignes ont agent="login", d’autres agent="Prenom Nom"
    # PostgREST OR filter
    filt = f"agent.eq.{login},agent.eq.{fullname}"
    return supabase.table("affectations").select("*").or_(filt).execute().data

def historique_for(login, fullname):
    filt = f"agent.eq.{login},agent.eq.{fullname}"
    return (
        supabase.table("historique")
        .select("*")
        .or_(filt)
        .order("date", desc=True)
        .execute()
        .data
    )

# ---------------- LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
def connexion():
    if request.method == "POST":
        a = get_agent(request.form["login"])
        if a and a.get("password") == request.form["password"]:
            session.clear()
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
    if not require_login():
        return redirect("/")
    return render_template("index.html", **session)

# ---------------- MON COMPTE ----------------

@app.route("/mon-compte")
def mon_compte():
    if not require_login():
        return redirect("/")
    return render_template("mon_compte.html", **session)

# ---------------- ADMIN AGENTS ----------------

@app.route("/admin/agents", methods=["GET", "POST"])
def admin_agents():
    if not require_admin():
        return redirect("/accueil")

    if request.method == "POST":
        supabase.table("agents").insert({
            "login": request.form["login"].strip(),
            "nom": request.form["nom"].strip(),
            "prenom": request.form["prenom"].strip(),
            "role": request.form["role"].strip(),
            "password": request.form["password"]
        }).execute()

    return render_template("admin_agents.html", agents=agents(), **session)

@app.route("/admin/supprimer/<login>")
def supprimer_agent(login):
    if not require_admin():
        return redirect("/accueil")
    supabase.table("agents").delete().eq("login", login).execute()
    return redirect("/admin/agents")

# ---------------- FICHES AGENTS ----------------

@app.route("/fiches-agents")
def fiches_agents():
    if not require_admin():
        return redirect("/accueil")
    return render_template("fiches_agents.html", agents=agents(), **session)

@app.route("/fiche-agent/<login>")
def fiche_agent(login):
    if not require_admin():
        return redirect("/accueil")

    a = get_agent(login)
    if not a:
        return redirect("/fiches-agents")

    fullname = full_name(a)

    mats = affectations_for(a["login"], fullname)
    for m in mats:
        m["epi"] = epi_status(m.get("controle") or "")

    magasin = materiels_magasin()
    for x in magasin:
        x["epi"] = epi_status(x.get("controle") or "")

    hist = historique_for(a["login"], fullname)

    return render_template(
        "fiche_agent.html",
        agent=a,
        agent_fullname=fullname,
        materiels=mats,
        magasin=magasin,
        hist=hist,
        **session
    )

# ---------------- ACTION MATERIEL ----------------

@app.route("/materiel/action", methods=["POST"])
def action_materiel():
    if not require_admin():
        return redirect("/accueil")

    aff_id = request.form["id"]
    agent_login = request.form["agent_login"].strip()
    agent_fullname = request.form.get("agent_fullname", "").strip()

    materiel = request.form.get("materiel", "").strip()
    action = request.form.get("action", "").strip()
    remplace = request.form.get("remplace", "").strip()
    controle = request.form.get("controle", "").strip()

    # 1) retire la ligne d’affectation
    supabase.table("affectations").delete().eq("id", aff_id).execute()

    # 2) stock magasin : on ne fait rien ici (pour éviter de casser ton stock existant),
    # on trace surtout l’historique.
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if action == "stock":
        libelle = "Retour magasin"
    elif action == "reforme":
        libelle = "Réforme"
    elif action == "echange":
        # On réaffecte un remplaçant à l’agent (on stocke en login)
        if remplace:
            supabase.table("affectations").insert({
                "agent": agent_login,
                "materiel": remplace,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "controle": controle
            }).execute()
            libelle = f"Échange → {remplace}"
        else:
            libelle = "Échange (sans remplaçant)"
    else:
        libelle = "Action inconnue"

    # 3) historique : on écrit en login (standard)
    supabase.table("historique").insert({
        "agent": agent_login,
        "materiel": materiel,
        "action": libelle,
        "date": now
    }).execute()

    return redirect(f"/fiche-agent/{agent_login}")

# ---------------- INVENTAIRE ----------------

@app.route("/inventaire")
def inventaire():
    if not require_login():
        return redirect("/")
    # ton inventaire existant reste tel quel (template gère l’affichage)
    mats = materiels_magasin()
    for m in mats:
        m["epi"] = epi_status(m.get("controle") or "")
    return render_template("inventaire.html", materiels=mats, agents=agents(), **session)

# ---------------- MA FICHE ----------------

@app.route("/ma-fiche")
def ma_fiche():
    if not require_login():
        return redirect("/")

    # compat login + ancien prénom nom
    a = get_agent(session["login"]) or {}
    fullname = full_name(a) if a else (session.get("prenom", "") + " " + session.get("nom", "")).strip()

    mats = affectations_for(session["login"], fullname)
    for m in mats:
        m["epi"] = epi_status(m.get("controle") or "")

    hist = historique_for(session["login"], fullname)

    return render_template("ma_fiche.html", materiels=mats, hist=hist, **session)

# ---------------- ECHANGES ----------------

@app.route("/echanges")
def echanges():
    if not require_login():
        return redirect("/")
    return render_template("echanges.html", **session)

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
