from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("connecter"))

app.secret_key = "sdis55"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_agents():
    return supabase.table("agents").select("*").execute().data

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        login = request.form["login"]
        password = request.form["password"]

        res = supabase.table("agents").select("*").eq("login", login).execute().data

        if res and res[0]["password"] == password:
            a = res[0]
            session["login"]=a["login"]
            session["nom"]=a["nom"]
            session["prenom"]=a["prenom"]
            session["role"]=a["role"]
            return redirect("/accueil")

        return render_template("login.html", erreur="Identifiant ou mot de passe incorrect")

    return render_template("login.html")

@app.route("/deconnexion")
def deconnexion():
    session.clear()
    return redirect("/")

@app.route("/accueil")
def accueil():
    if "login" not in session: return redirect("/")
    return render_template("index.html", **session)

@app.route("/echanges")
def echanges():
    if "login" not in session: return redirect("/")
    return render_template("echanges.html", **session)

@app.route("/inventaire")
def inventaire():
    if "login" not in session: return redirect("/")
    return render_template("inventaire.html", **session)

@app.route("/fiches-agents")
def fiches_agents():
    if "login" not in session: return redirect("/")
    return render_template("fiches_agents.html", agents=get_agents(), **session)

@app.route("/ma-fiche")
def ma_fiche():
    if "login" not in session:
        return redirect(url_for("connexion"))

    agent = session["login"]

    materiel = supabase.table("affectations")\
        .select("*")\
        .eq("agent", agent)\
        .execute().data

    return render_template(
        "ma_fiche.html",
        materiel=materiel,
        agent=session
    )


@app.route("/admin/agents")
def admin_agents():
    if session.get("role")!="Admin": return redirect("/accueil")
    return render_template("admin_agents.html", agents=get_agents(), **session)
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

