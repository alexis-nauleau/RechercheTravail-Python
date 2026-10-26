"""Dashboard de suivi de candidatures (Flask)."""
import os

from flask import Flask, render_template, request

import db
from candidatures import ajouter, lister


def create_app(config=None):
    """Fabrique l'application. Les tests passent leur propre config (une base jetable).

    "config=None" signifie : le paramètre est facultatif. create_app() fonctionne
    toujours, et create_app({...}) aussi.
    """
    app = Flask(__name__)

    # app.instance_path est un dossier "instance" à côté de ce fichier, réservé aux
    # données de l'application. Il est exclu de Git (ligne "instance/" du .gitignore).
    app.config["DATABASE"] = os.path.join(app.instance_path, "candidatures.db")
    # Si on a reçu une config (les tests), elle REMPLACE les valeurs par défaut :
    # c'est ce qui permet aux tests d'utiliser une base temporaire, et jamais la vraie.
    if config:
        app.config.update(config)
    # Crée le dossier de la base s'il n'existe pas (exist_ok=True : pas d'erreur s'il existe)
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    db.init_app(app)
    # Au démarrage, on s'assure que la table existe. Un "contexte d'application" est
    # nécessaire pour utiliser get_db() en dehors d'une requête.
    with app.app_context():
        db.init_db()

    @app.get("/")
    def accueil():
        # request.args lit ce qui suit le "?" dans l'adresse : /?statut=postule
        statut = request.args.get("statut")
        # Un statut inconnu est ignoré : on affiche tout plutôt qu'une erreur
        if statut not in db.STATUTS:
            statut = None
        return render_template(
            "index.html",
            candidatures=lister(statut),
            statuts=db.STATUTS,
            filtre=statut,
        )

    # Une commande de terminal : python -m flask --app app seed
    @app.cli.command("seed")
    def seed():
        """Ajoute des candidatures FICTIVES, seulement si la table est vide."""
        if lister():
            print("La table contient déjà des données : rien n'a été ajouté.")
            return
        exemples = [
            ("Entreprise Exemple A", "Développeur web", "https://example.com/offre-1",
             "postule", "2026-10-20", "Donnée fictive."),
            ("Entreprise Exemple B", "Développeur Python", "https://example.com/offre-2",
             "entretien", "2026-10-22", "Donnée fictive. Entretien à préparer."),
            ("Entreprise Exemple C", "Intégrateur", None, "a_postuler", None, None),
            ("Entreprise Exemple D", "Développeur Node", "https://example.com/offre-4",
             "refus", "2026-10-10", "Donnée fictive."),
        ]
        for entreprise, poste, lien, statut, date_candidature, notes in exemples:
            ajouter(entreprise, poste, lien, statut, date_candidature, notes)
        print(f"{len(exemples)} candidatures fictives ajoutées.")

    return app


if __name__ == "__main__":
    # debug=True : acceptable ici car le serveur n'écoute que sur ton PC (127.0.0.1).
    # Ne l'active JAMAIS sur un serveur accessible depuis Internet.
    create_app().run(host="127.0.0.1", port=5000, debug=True)