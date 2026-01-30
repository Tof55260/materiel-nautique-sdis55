<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Gestion du matériel nautique</title>

    <!-- CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">

    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>

    <!-- ===== EN-TÊTE ===== -->
    <header class="header">
        <div class="header-left">
            <img src="{{ url_for('static', filename='images/logo_nautique.png') }}"
                 alt="Logo Nautique"
                 class="logo">
            <h1>Matériel Nautique SDIS 55</h1>
        </div>
    </header>

    <!-- ===== MENU ===== -->
    <nav class="menu">
        <a href="{{ url_for('index') }}">🏠 Accueil</a>
        <a href="{{ url_for('echanges') }}">🔁 Échanges</a>
        <a href="{{ url_for('changer_profil') }}">👤 Changer de profil</a>
    </nav>

    <!-- ===== CONTENU PRINCIPAL ===== -->
    <main class="container">

        <h2>Bienvenue</h2>
        <p>
            Profil connecté :
            <strong>{{ role }}</strong>
        </p>

        <!-- ===== AJOUT MATÉRIEL ===== -->
        <section class="card">
            <h3>➕ Ajouter un matériel</h3>

            <form method="POST" action="{{ url_for('ajouter') }}" class="form">
                <label>
                    Nom du matériel
                    <input type="text" name="nom" required>
                </label>

                <label>
                    Type
                    <input type="text" name="type" required>
                </label>

                <label>
                    Prochain contrôle (en mois)
                    <input type="number" name="controle" min="1" required>
                </label>

                <button type="submit">Ajouter</button>
            </form>
        </section>

        <!-- ===== LISTE MATÉRIEL ===== -->
        <section class="card">
            <h3>📦 Matériel en stock</h3>

            {% if materiels %}
                <table class="table">
                    <thead>
                        <tr>
                            <th>Nom</th>
                            <th>Type</th>
                            <th>Contrôle (mois)</th>
                            <th>Ajouté par</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for m in materiels %}
                        <tr>
                            <td>{{ m.nom }}</td>
                            <td>{{ m.type }}</td>
                            <td>{{ m.controle }}</td>
                            <td>{{ m.ajoute_par }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <p>Aucun matériel enregistré.</p>
            {% endif %}
        </section>

    </main>

    <!-- ===== PIED DE PAGE ===== -->
    <footer class="footer">
        <p>Équipe nautique SDIS 55 — Application interne</p>
    </footer>

</body>
</html>
