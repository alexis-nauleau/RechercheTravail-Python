"""Dashboard de suivi de candidatures (Flask)."""
import hmac
import os
import secrets
from datetime import date

from flask import (Flask, abort, flash, redirect, render_template, request, session,
                   url_for)

import db
from candidatures import LONGUEUR_MAX, ajouter, lister, separer_technologies

# Les champs du formulaire, dans l'ordre. On ne lit QUE ceux-là dans ce que le
# navigateur envoie : un champ en plus, glissé par quelqu'un, est ignoré.
CHAMPS = ("entreprise", "poste", "technologies", "lien", "statut",
          "date_candidature", "notes")


def _charger_cle_secrete(dossier):
    """Lit la clé secrète dans instance/secret_key, et la crée au premier lancement.

    Flask s'en sert pour signer le cookie de session : sans elle, impossible de
    retenir le jeton anti-CSRF. Elle doit rester sur ton PC (jamais dans Git).
    """
    chemin = os.path.join(dossier, "secret_key")
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as fichier:
            return fichier.read().strip()
    # secrets.token_hex(32) : 64 caractères hexadécimaux issus du hasard sécurisé
    cle = secrets.token_hex(32)
    with open(chemin, "w", encoding="utf-8") as fichier:
        fichier.write(cle)
    return cle


def create_app(config=None):
    """Fabrique l'application. Les tests passent leur propre config (une base jetable).

    "config=None" signifie : le paramètre est facultatif. create_app() fonctionne
    toujours, et create_app({...}) aussi.
    """
    app = Flask(__name__)

    # app.instance_path est un dossier "instance" à côté de ce fichier, réservé aux
    # données de l'application. Il est exclu de Git (ligne "instance/" du .gitignore).
    app.config["DATABASE"] = os.path.join(app.instance_path, "candidatures.db")
    # Le cookie de session n'est pas envoyé quand un AUTRE site déclenche une requête
    # vers le nôtre : une première barrière contre le CSRF.
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    # Si on a reçu une config (les tests), elle REMPLACE les valeurs par défaut :
    # c'est ce qui permet aux tests d'utiliser une base temporaire, et jamais la vraie.
    if config:
        app.config.update(config)
    # Crée le dossier de la base s'il n'existe pas (exist_ok=True : pas d'erreur s'il existe)
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    # Pas de clé fournie (lancement normal) : on utilise celle du fichier instance/secret_key
    if not app.config.get("SECRET_KEY"):
        os.makedirs(app.instance_path, exist_ok=True)
        app.config["SECRET_KEY"] = _charger_cle_secrete(app.instance_path)

    db.init_app(app)
    # Au démarrage, on s'assure que la table existe. Un "contexte d'application" est
    # nécessaire pour utiliser get_db() en dehors d'une requête.
    with app.app_context():
        db.init_db()

    # Un "filtre" Jinja : dans la page, {{ texte | techs }} appelle cette fonction.
    app.add_template_filter(separer_technologies, "techs")

    # ---- Protection CSRF ----
    def jeton_csrf():
        """Renvoie le jeton de cette session (il est créé au premier appel)."""
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    def jeton_valide():
        """Le jeton reçu du formulaire doit être celui qu'on a rangé dans la session."""
        attendu = session.get("csrf")
        recu = request.form.get("csrf", "")
        # Pas de jeton en session : on refuse (sinon "" == "" passerait !).
        # compare_digest compare sans révéler, par le temps de calcul, où le texte diffère.
        return bool(attendu) and hmac.compare_digest(attendu, recu)

    # Rend jeton_csrf() utilisable dans toutes les pages : {{ jeton_csrf() }}
    app.jinja_env.globals["jeton_csrf"] = jeton_csrf

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

    # Cette page accepte deux "méthodes" : GET (afficher le formulaire)
    # et POST (recevoir ce qui a été rempli).
    @app.route("/nouvelle", methods=["GET", "POST"])
    def nouvelle():
        # Valeurs de départ du formulaire : vides, sauf un statut et la date du jour.
        valeurs = {nom: "" for nom in CHAMPS}
        valeurs["statut"] = "postule"
        valeurs["date_candidature"] = date.today().isoformat()
        erreur = None

        if request.method == "POST":
            # 1) Le jeton d'abord : sans lui, on ne regarde même pas le reste.
            if not jeton_valide():
                abort(400)  # 400 = "requête incorrecte"
            # 2) On relit les champs (le texte reçu, tel quel) pour pouvoir les réafficher.
            valeurs = {nom: request.form.get(nom, "") for nom in CHAMPS}
            try:
                # **valeurs : "déballe" le dictionnaire en ajouter(entreprise=..., poste=...)
                ajouter(**valeurs)
            except ValueError as probleme:
                erreur = str(probleme)  # le message écrit dans candidatures.py
            else:
                # flash : un message affiché UNE fois, sur la page suivante
                flash("Candidature ajoutée.")
                # 303 : "va voir cette autre page" (évite de renvoyer le formulaire
                # si on actualise la page)
                return redirect(url_for("accueil"), code=303)

        page = render_template(
            "nouvelle.html",
            valeurs=valeurs,
            erreur=erreur,
            statuts=db.STATUTS,
            longueurs=LONGUEUR_MAX,
        )
        # En cas d'erreur de saisie, on répond 400 ; sinon 200 (le défaut).
        return (page, 400) if erreur else page

    # Une commande de terminal : python -m flask --app app seed
    @app.cli.command("seed")
    def seed():
        """Ajoute des candidatures FICTIVES, seulement si la table est vide."""
        if lister():
            print("La table contient déjà des données : rien n'a été ajouté.")
            return
        # Chaque exemple est un dictionnaire : nom du paramètre -> valeur.
        exemples = [
            {"entreprise": "Entreprise Exemple A", "poste": "Développeur web",
             "technologies": "HTML, CSS, JavaScript", "lien": "https://example.com/offre-1",
             "statut": "postule", "date_candidature": "2026-10-20",
             "notes": "Donnée fictive."},
            {"entreprise": "Entreprise Exemple B", "poste": "Développeur Python",
             "technologies": "Python, Flask, SQL", "lien": "https://example.com/offre-2",
             "statut": "entretien", "date_candidature": "2026-10-22",
             "notes": "Donnée fictive. Entretien à préparer."},
            {"entreprise": "Entreprise Exemple C", "poste": "Intégrateur",
             "technologies": "HTML, CSS", "statut": "a_postuler"},
            {"entreprise": "Entreprise Exemple D", "poste": "Développeur Node",
             "technologies": "Node.js, Vue.js, PostgreSQL",
             "lien": "https://example.com/offre-4", "statut": "refus",
             "date_candidature": "2026-10-10", "notes": "Donnée fictive."},
        ]
        for exemple in exemples:
            ajouter(**exemple)
        print(f"{len(exemples)} candidatures fictives ajoutées.")

    return app


if __name__ == "__main__":
    # debug=True : acceptable ici car le serveur n'écoute que sur ton PC (127.0.0.1).
    # Ne l'active JAMAIS sur un serveur accessible depuis Internet.
    create_app().run(host="127.0.0.1", port=5000, debug=True)