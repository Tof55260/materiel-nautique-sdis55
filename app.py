from flask import Flask, request
from supabase import create_client

SUPABASE_URL = "https://vylcvdfgrcikppxfpztj.supabase.co"
SUPABASE_KEY = "sb_publishable_aDwaBA4DNt4gjIy0ODE23g_eGWA3Az3"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

print("APP LOGIN SIMPLE OK")

@app.route("/", methods=["GET","POST"])
def login():

    msg=""

    if request.method=="POST":

        login=request.form["login"]
        pwd=request.form["password"]

        agents = supabase.table("agents").select("*").execute().data

        print("AGENTS:", agents)

        for a in agents:

            if a["login"]==login:

                if a["password"] == pwd:
                    return "<h1>LOGIN OK</h1>"

                else:
                    msg="Mauvais mot de passe"

        if not msg:
            msg="Login introuvable"

    return f"""
    <form method='POST'>
        <input name='login'><br>
        <input type='password' name='password'><br>
        <button>Connexion</button>
        <p>{msg}</p>
    </form>
    """

@app.route("/agents")
def agents():
    return str(supabase.table("agents").select("*").execute().data)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
