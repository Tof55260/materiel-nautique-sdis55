from flask import Flask, render_template, request, redirect, url_for, session
import os

app = Flask(__name__, template_folder="templates")
app.secret_key = "sdis55-nautique"

materiels = []

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

    nom = request.form["nom"]
    type_m = request.form["type"]
    controle_mois = request.form["controle"]

    materiels.append({
        "nom": nom,
        "type": type_m,
        "controle": controle_mois,
        "ajoute_par": role
    })

    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
