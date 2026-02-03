from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "sdis55"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------- LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        login = request.form["login"]
        password = request.form["password"]

        users = supabase.table("users").select("*").eq("login", login).execute().data

        if not users:
            return render_template("login.html", error="Utilisateur inconnu")

        user = users[0]

        if user["password"] != password:
            return render_template("login.html", error="Mot de passe incorrect")

        session["login"] = user["login"]
        session["nom"] = user["nom"]
        session["prenom"] = user["prenom"]
        session["role"] = user["role"]

        return redirect(url_for("accueil"))

    return render_template("login.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- ACCUEIL ----------------

@app.route("/accueil")
def accueil():

    if not session.get("login"):
        return redirect(url_for("login"))

    return render_template("index.html", **session)


# ---------------- INVENTAIRE ----------------

@app.route("/inventaire")
def inventaire():

    if not session.get("login"):
        return redirect(url_for("login"))

    items = supabase.table("materiel").select("*").execute().data

    return render_template("inventaire.html", items=items, **session)


# ---------------- ECHANGES ----------------

@app.route("/echanges")
def echanges():

    if not session.get("login"):
        return redirect(url_for("login"))

    return render_template("echanges.html", **session)


# ---------------- MA FICHE ----------------

@app.route("/ma-fiche")
def ma_fiche():

    if not session.get("login"):
        return redirect(url_for("login"))

    nom = session["nom"]

    materiel = supabase.table("affectations").select("*").eq("agent", nom).execute().data

    return render_template(
        "ma_fiche.html",
        materiel=materiel,
        **session
    )


# ---------------- FICHES AGENTS (ADMIN) ----------------

@app.route("/fiches-agents")
def fiches_agents():

    if session.get("role") != "Admin":
        return redirect(url_for("accueil"))

    agents = supabase.table("users").select("*").execute().data

    return render_template("fiches_agents.html", agents=agents, **session)


# ---------------- ADMIN ----------------

@app.route("/admin/agents")
def admin_agents():

    if session.get("role") != "Admin":
        return redirect(url_for("accueil"))

    agents = supabase.table("users").select("*").execute().data

    return render_template("admin_agents.html", agents=agents, **session)


# ---------------- MAIN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
