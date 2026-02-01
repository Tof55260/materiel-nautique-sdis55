from flask import Flask, render_template, request, redirect, session, send_file
from datetime import datetime, date
from supabase import create_client
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "sdis55"

SUPABASE_URL = "https://vylcvdfgrcikppxfpztj.supabase.co"
SUPABASE_KEY = "sb_publishable_aDwaBA4DNt4gjIy0ODE23g_eGWA3Az3"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def agents():
    return supabase.table("agents").select("*").execute().data

def get_agent(login):
    r = supabase.table("agents").select("*").eq("login", login).execute().data
    return r[0] if r else None

def materiels():
    return supabase.table("materiels").select("*").execute().data

def affectations(login):
    return supabase.table("affectations").select("*").eq("agent", login).execute().data

def historique(login):
    return supabase.table("historique").select("*").eq("agent", login).order("date", desc=True).execute().data

def epi(d):
    try:
        delta = (datetime.strptime(d, "%Y-%m-%d").date() - date.today()).days
        if delta < 0: return "expired"
        if delta < 30: return "warning"
        return "ok"
    except:
        return "ok"

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        a=get_agent(request.form["login"])
        if a and a["password"]==request.form["password"]:
            session.update(a)
            return redirect("/accueil")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/accueil")
def accueil():
    return render_template("index.html",**session)

@app.route("/inventaire",methods=["GET","POST"])
def inventaire():
    if session["role"]=="Admin" and request.method=="POST":
        supabase.table("materiels").insert({
            "nom":request.form["nom"],
            "type":request.form["type"],
            "stock":int(request.form["stock"]),
            "controle":request.form["controle"]
        }).execute()

    mats=materiels()
    for m in mats: m["epi"]=epi(m.get("controle"))
    return render_template("inventaire.html",materiels=mats,agents=agents(),**session)

@app.route("/fiches-agents")
def fiches_agents():
    return render_template("fiches_agents.html",agents=agents(),**session)

@app.route("/fiche-agent/<login>")
def fiche_agent(login):
    a=get_agent(login)
    mats=affectations(login)
    hist=historique(login)
    mag=materiels()
    for m in mats: m["epi"]=epi(m.get("controle"))
    return render_template("fiche_agent.html",agent=a,materiels=mats,magasin=mag,hist=hist,**session)

@app.route("/materiel/action",methods=["POST"])
def action_materiel():
    id=request.form["id"]
    agent=request.form["agent"]
    mat=request.form["materiel"]
    action=request.form["action"]
    repl=request.form.get("remplace","")

    supabase.table("affectations").delete().eq("id",id).execute()

    if action=="stock":
        supabase.table("materiels").update({"stock":"stock+1"}).eq("nom",mat).execute()

    if action=="echange" and repl:
        supabase.table("affectations").insert({
            "agent":agent,
            "materiel":repl,
            "date":datetime.now().strftime("%Y-%m-%d")
        }).execute()

    supabase.table("historique").insert({
        "agent":agent,
        "materiel":mat,
        "action":action,
        "date":datetime.now().strftime("%Y-%m-%d %H:%M")
    }).execute()

    return redirect(f"/fiche-agent/{agent}")

@app.route("/admin/agents",methods=["GET","POST"])
def admin_agents():
    if request.method=="POST":
        supabase.table("agents").insert({
            "login":request.form["login"],
            "nom":request.form["nom"],
            "prenom":request.form["prenom"],
            "role":request.form["role"],
            "password":request.form["password"]
        }).execute()
    return render_template("admin_agents.html",agents=agents(),**session)

@app.route("/admin/supprimer/<login>")
def supprimer(login):
    supabase.table("agents").delete().eq("login",login).execute()
    return redirect("/admin/agents")

@app.route("/ma-fiche")
def ma_fiche():
    mats=affectations(session["login"])
    hist=historique(session["login"])
    for m in mats: m["epi"]=epi(m.get("controle"))
    return render_template("ma_fiche.html",materiels=mats,hist=hist,**session)

@app.route("/echanges")
def echanges():
    return render_template("echanges.html",**session)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
