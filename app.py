import json
import os
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__, template_folder="templates")
app.secret_key = "sdis55-nautique"

FICHIER_ECHANGES = "echanges.json"

materiels = []

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
        "nom": request.form["nom"],
        "type": request.form["type"],
        "controle": request.form["controle"],
        "ajoute_par": role
    })

    return redirect(url_for("index"))

@app.route("/echanges", methods=["GET", "POST"])
def echanges():
    role = session.get("role")
    if not role:
        return redirect(url_for("profil"))

    echanges = charger_json(FICHIER_ECHANGES)

    if request.method == "POST":
        echanges.append({
            "id": len(echanges) + 1,
            "agent": request.form["agent"],
            "materiel": request.form["materiel"],
            "motif": request.form["motif"],
            "statut": "En attente"
        })
        sauvegarder_json(FICHIER_ECHANGES, echanges)

    return render_template("echanges.html", echanges=echanges, role=role)

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
