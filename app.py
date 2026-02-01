@app.route("/debug_agents")
def debug_agents():
    return str(agents())
