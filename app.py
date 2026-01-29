import json
import os
from flask import Flask, render_template, request, redirect, url_for, session

# =====================
# CONFIGURATION
# =====================

app = Flask(__name__)
app.secret_key = "sdis55-nautique"

FICHIER_PROFILS = "profils.json"
FICHIER_ECHANGES = "echanges.json"

materiels = []

# =====================
# FONCTIONS PROFILS
# =====================

def charger_profils():
    if os.path.exists(FICHIER_PROFILS):
        with open(FICHIER_PROFILS, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def sauvegarder_profils(profils):
    with open(FICHIER_PROFILS, "w", encoding="utf-8") as f:
        json.dump(profils, f, indent=2, ensure_ascii=False)

# =====================
# FONCTIONS ÉCHANGES
# =====================

def charger_echanges():
    if os.path.exists(FICHIER_ECHANGES):
        with open(FICHIER_ECHANGES, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def sauvegarder_echanges(echanges):
    with open(FICHIER_ECHANGES, "w", encoding="utf-8") as f:
        json.dump(echanges, f, indent=2, ensure_ascii=False)

# =====================
# ROUTES
# =====================

@app.route("/")
def index():
    role = session.get("role")
    if not role:
        return redirect(url_for("profil"))
    return render_template("index.html", materiels=materiels, role=role)

@app.route("/profil", methods=["GET", "POST"])
def profil():
    if request.method == "POST":
        session["role"] = request.form["role"]
        return redirect(url_for("index"))
    return render_template("profil.html")

@app.route("/changer_profil")
def changer_profil():
    session.pop("role", None)
    return redirect(url_for("profil"))

@app.route("/ajouter", methods=["POST"])
def ajouter():
    role = session.get("role")
    if not role:
        return redirect(url_for("profil"))

    materiels.append({
        "nom": request.form
