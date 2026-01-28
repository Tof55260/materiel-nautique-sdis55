from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__, template_folder="templates")


materiels = []

@app.route("/")
def index():
    return render_template("index.html", materiels=materiels)

@app.route("/ajouter", methods=["POST"])
def ajouter():
    nom = request.form["nom"]
    type_m = request.form["type"]
    controle_mois = request.form["controle"]
    materiels.append({
        "nom": nom,
        "type": type_m,
        "controle": controle_mois
    })
    return redirect(url_for("index"))

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

