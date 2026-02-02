from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = "sdis55"

print("APP BASE STABLE OK")

def agents():
    return supabase.table("agents").select("*").execute().data

# ================= LOGIN =================

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        login = request.form["login"]
        password = request.form["password"]

        a = supabase.table("agents").select("*").eq("login", login).execute().data

        if a and a[0]["password"] == password:
            session["login"] = login
            session["nom"] = a[0]["nom"]
            session["prenom"] = a[0]["prenom"]
            session["role"] = a[0]["role"]
            return redirect(url_for("accueil"))

        return render_template("login.html", erreur="Identifiant ou mot de passe incorrect")

    return render_template("login.html")

@app.route("/deconnexion")
def deconnexion():
    session.clear()
    return redirect("/")

# ================= PAGES =================

@app.route("/accueil")
def accueil():
    if "login" not in session:
        return redirect("/")
    return render_template("index.html", **session)

@app.route("/echanges")
def echanges():
    if "login" not in session:
        return redirect("/")
    return render_template("echanges.html", **session)

@app.route("/inventaire")
def inventaire():
    if "login" not in session:
        return redirect("/")
    return render_template("inventaire.html", **session)

@app.route("/fiches-agents")
def fiches_agents():
    if "login" not in session:
        return redirect("/")
    return render_template("fiches_agents.html", agents=agents(), **session)

@app.route("/ma-fiche")
def ma_fiche():
    if "login" not in session:
        return redirect("/")
    return render_template("ma_fiche.html", **session)

@app.route("/admin/agents")
def admin_agents():
    if session.get("role") != "Admin":
        return redirect("/accueil")
    return render_template("admin_agents.html", agents=agents(), **session)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
