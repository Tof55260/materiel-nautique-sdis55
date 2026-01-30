import os
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__, template_folder="templates")
app.secret_key = "sdis55-nautique"

# =========================
# DONNÉES EN MÉMOIRE
# =========================

materiels = []
echanges = []
agents = []

# =========================
# CONNEXION (BYPASS ADMIN)
# =========================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form.get("login", "").strip()
        password = request.form.get("password", "").strip()

        # 🔓 BYPASS ADMIN GARANTI
        if login == "admin" and password == "admin55":
            session["login"] = "admin"
            session["nom"] = "BOUDOT"
            session["prenom"] = "Christophe"
            session["role"] = "Admin"
            return redirect(url_for("accueil"))

        return render_template("login.html", erreur="Identifiant ou mot de passe incorrect")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =========================
# ACCUEIL
# =========================

@app.route("/accueil")
def accueil():
    if "login" not in session:
        return redirect(url_for("login"))

    return render_template(
        "index.html",
        materiels=materiels,          # ✅ AJOUT CRITIQUE
        nom=session["nom"],
        prenom=session["prenom"],
        role=session["role"]
    )

# =========================
# ÉCHANGES
# =========================

@app.route("/echanges")
def page_echanges():
    if "login" not in session:
        return redirect(url_for("login"))

    return render_template(
        "echanges.html",
        echanges=echanges,            # ✅ AJOUT CRITIQUE
        nom=session["nom"],
        prenom=session["prenom"],
        role=session["role"]
    )

# =========================
# ADMIN
# =========================

@app.route("/admin/agents")
def admin_agents():
    if session.get("role") != "Admin":
        return redirect(url_for("accueil"))

    return render_template(
        "admin_agents.html",
        agents=agents                 # ✅ AJOUT CRITIQUE
    )

# =========================
# LANCEMENT
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

