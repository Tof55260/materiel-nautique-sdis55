from flask import Flask, render_template, request, redirect, session
from supabase import create_client
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key="secret"

SUPABASE_URL=os.environ.get("SUPABASE_URL")
SUPABASE_KEY=os.environ.get("SUPABASE_KEY")

supabase=create_client(SUPABASE_URL,SUPABASE_KEY)

# ---------------- LOGIN ----------------

@app.route("/",methods=["GET","POST"])
def login():
    if request.method=="POST":
        a=supabase.table("agents").select("*").eq("login",request.form["login"]).execute().data
        if a and a[0]["password"]==request.form["password"]:
            session.update(a[0])
            return redirect("/accueil")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- ACCUEIL ----------------

from datetime import datetime

@app.route("/accueil")
def accueil():
    return render_template("index.html", now=datetime.now, **session)

# ---------------- INVENTAIRE ----------------

@app.route("/inventaire")
def inventaire():
    items=supabase.table("materiels").select("*").execute().data
    return render_template("inventaire.html",items=items,**session)

@app.route("/ajouter_materiel",methods=["POST"])
def ajouter_materiel():
    supabase.table("materiels").insert({
        "nom":request.form["nom"],
        "type":request.form["type"],
        "serie":request.form["serie"],
        "controle_epi":request.form["controle"],
        "statut":"stock"
    }).execute()
    return redirect("/inventaire")

# ---------------- DEMANDE AGENT ----------------

@app.route("/demande_echange",methods=["POST"])
def demande_echange():
    supabase.table("echanges").insert({
        "agent":session["login"],
        "ancien_materiel":request.form["materiel"],
        "statut":"en_attente",
        "date":datetime.now().isoformat()
    }).execute()

    supabase.table("notifications").insert({
        "message":f"{session['prenom']} demande un échange",
        "lu":False,
        "date":datetime.now().isoformat()
    }).execute()

    return redirect("/echanges")

# ---------------- ÉCHANGES ----------------

@app.route("/echanges")
def echanges():
    e=supabase.table("echanges").select("*").order("date",desc=True).execute().data
    stock=supabase.table("materiels").select("*").eq("statut","stock").execute().data
    return render_template("echanges.html",echanges=e,stock=stock,**session)

@app.route("/valider/<int:id>",methods=["POST"])
def valider(id):

    nouveau=request.form["nouveau"]

    ex=supabase.table("echanges").select("*").eq("id",id).execute().data[0]

    # ancien retourne stock
    supabase.table("materiels").update({"statut":"stock","agent":None}).eq("serie",ex["ancien_materiel"]).execute()

    # nouveau affecté
    supabase.table("materiels").update({"statut":"affecte","agent":ex["agent"]}).eq("serie",nouveau).execute()

    supabase.table("echanges").update({
        "statut":"valide",
        "nouveau_materiel":nouveau
    }).eq("id",id).execute()

    return redirect("/echanges")

# ---------------- MA FICHE ----------------

@app.route("/ma-fiche")
def ma_fiche():
    m=supabase.table("materiels").select("*").eq("agent",session["login"]).execute().data
    return render_template("ma_fiche.html",materiels=m,**session)
@app.route("/fiches-agents")
def fiches_agents():
    agents = supabase.table("agents").select("*").execute().data
    return render_template("fiches_agents.html", agents=agents, **session)
 @app.route("/fiches-agents")
def fiches_agents():
    if session.get("role") != "Admin":
        return redirect(url_for("accueil"))

    agents = supabase.table("agents").select("*").execute().data
    return render_template("fiches_agents.html", agents=agents, **session)

@app.route("/admin/agents")
def admin_agents():
    if session.get("role") != "Admin":
        return redirect(url_for("accueil"))

    agents = supabase.table("agents").select("*").execute().data
    return render_template("admin_agents.html", agents=agents, **session)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
