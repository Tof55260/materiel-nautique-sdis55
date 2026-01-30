import json
import os
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__, template_folder="templates")
app.secret_key = "sdis55-nautique"

FICHIER_ECHANGES = "echanges.json"

materiels = []

# ======================
# OUTILS JSON
# ======================

def charger_json(fichier):
    if not os.path.exists(fichier):
        return []
    try:
        with open(fichier, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def sauvegarder_json(fichier, data):
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ======================
# IDENTIFICATION OBLIGATOIRE
# ======================

@app.route("/", methods=["GET", "POST"])
def identification():
    if request.method == "POST":
        session["nom"] = request.form["nom"]
        session["prenom"] = request.form["prenom"]
        session["role"] = request.form["role"]
        return redirect(url_for("index"))

    return render_template("identification.html")

# ======================
# PAGES PRINCIPALES
# ======================

@app.route("/accueil")
def index():
    if "nom" not in session:
        return redirect(url_for("identification"))

    return render_template(
        "index.html",
        materiels=materiels,
        nom=session["nom"],
        prenom=session["prenom"],
        role=session["role"]
    )

@app.route("/changer_profil")
def changer_profil():
    session.clear()
    return redirect(url_for("identification"))

@app.route("/ajouter", methods=["POST"])
def ajouter():
    if "nom" not in session:
        return redirect(url_for("identification"))

    materiels.append({
        "nom": request.form["nom"],
        "type": request.form["type"],
        "controle": request.form["controle"],
        "ajoute_par": f"{session['prenom']} {session['nom']}"
    })

    return redirect(url_for("index"))

# ======================
# ÉCHANGES
# ======================

@app.route("/echanges", methods=["GET", "POST"])
def echanges():
    if "nom" not in session:
        return redirect(url_for("identification"))

    echanges = charger_json(FICHIER_ECHANGES)

    if request.method == "POST":
        echanges.append({
            "id": len(echanges) + 1,
            "agent": f"{session['prenom']} {session['nom']}",
            "profil": session["role"],
            "materiel": request.form["materiel"],
            "motif": request.form["motif"],
            "statut": "En attente"
        })
        sauvegarder_json(FICHIER_ECHANGES, echanges)

    return render_template(
        "echanges.html",
        echanges=echanges,
        nom=session["nom"],
        prenom=session["prenom"],
        role=session["role"]
    )

@app.route("/echanges/<int:id>/<action>")
def changer_statut(id, action):
    if session.get("role") != "chef":
        return redirect(url_for("echanges"))

    echanges = charger_json(FICHIER_ECHANGES)

    for e in echanges:
        if e["id"] == id:
            if action == "valider":
                e["statut"] = "Validé"
            elif action == "refuser":
                e["statut"] = "Refusé"

    sauvegarder_json(FICHIER_ECHANGES, echanges)
    return redirect(url_for("echanges"))

# ======================
# LANCEMENT
# ======================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
