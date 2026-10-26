"""Dashboard de suivi de candidatures (Flask)."""
import hmac
import os
import secrets
from datetime import date

from flask import (Flask, abort, flash, redirect, render_template, request, session,
                   url_for)
from chemins import dossier_instance
import db
import sites
from candidatures import (LONGUEUR_MAX, ajouter, lister, modifier, obtenir,
                          separer_technologies, supprimer)

# Les champs des formulaires, dans l'ordre. On ne lit QUE ceux-là dans ce que le
# navigateur envoie : un champ en plus, glissé par quelqu'un, est ignoré.
CHAMPS = ("entreprise", "poste", "technologies", "lien", "statut",
          "date_candidature", "notes")
CHAMPS_SITE = ("nom", "lien", "utilisateur", "mot_de_passe")


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
        # instance_path=None : Flask garde son dossier "instance" habituel (développement).
    # En .exe, on lui donne un dossier du profil utilisateur (voir chemins.py).
    app = Flask(__name__, instance_path=dossier_instance())

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
    # Au démarrage, on s'assure que les tables existent. Un "contexte d'application" est
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

    # ---- Le formulaire, commun à toutes les sections ----
    def formulaire(titre, action, bouton, valeurs, enregistrer, message,
                   champs=CHAMPS, gabarit="formulaire.html", retour="accueil",
                   longueurs=LONGUEUR_MAX):
        """Affiche le formulaire (GET) ou traite son envoi (POST).

        valeurs     : ce qu'on met dans les champs au départ
        enregistrer : la fonction à appeler avec les valeurs reçues (ajout ou modification)
        message     : le texte affiché après un succès
        champs      : les noms des champs à lire dans ce que le navigateur envoie
        gabarit     : la page HTML à afficher
        retour      : la page où l'on revient après un succès
        """
        erreur = None
        if request.method == "POST":
            # 1) Le jeton d'abord : sans lui, on ne regarde même pas le reste.
            if not jeton_valide():
                abort(400)  # 400 = "requête incorrecte"
            # 2) On relit les champs (le texte reçu, tel quel) pour pouvoir les réafficher.
            valeurs = {nom: request.form.get(nom, "") for nom in champs}
            try:
                enregistrer(valeurs)
            except ValueError as probleme:
                erreur = str(probleme)  # le message écrit dans candidatures.py / sites.py
            else:
                # flash : un message affiché UNE fois, sur la page suivante
                flash(message)
                # 303 : "va voir cette autre page" (évite de renvoyer le formulaire
                # si on actualise la page)
                return redirect(url_for(retour), code=303)

        page = render_template(
            gabarit,
            titre=titre,
            action=action,
            bouton=bouton,
            valeurs=valeurs,
            erreur=erreur,
            statuts=db.STATUTS,
            longueurs=longueurs,
        )
        # En cas d'erreur de saisie, on répond 400 ; sinon 200 (le défaut).
        return (page, 400) if erreur else page

    # ---------------------------------------------------------------
    # Section 1 : les candidatures
    # ---------------------------------------------------------------
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
        # Valeurs de départ : vides, sauf un statut et la date du jour.
        valeurs = {nom: "" for nom in CHAMPS}
        valeurs["statut"] = "postule"
        valeurs["date_candidature"] = date.today().isoformat()
        return formulaire(
            titre="Nouvelle candidature",
            action=url_for("nouvelle"),
            bouton="Enregistrer",
            valeurs=valeurs,
            # lambda : une mini-fonction écrite sur une ligne. Ici : "reçois v,
            # appelle ajouter(**v)" (** déballe le dictionnaire en paramètres nommés).
            enregistrer=lambda v: ajouter(**v),
            message="Candidature ajoutée.",
        )

    # <int:identifiant> : la partie de l'adresse est lue comme un nombre entier.
    # /candidature/abc/modifier donne donc directement une erreur 404.
    @app.route("/candidature/<int:identifiant>/modifier", methods=["GET", "POST"])
    def modifier_candidature(identifiant):
        ligne = obtenir(identifiant)
        if ligne is None:
            abort(404)  # 404 = "page introuvable"
        # On préremplit avec ce qui est en base ("or ''" : None devient un champ vide).
        valeurs = {nom: ligne[nom] or "" for nom in CHAMPS}
        return formulaire(
            titre="Modifier la candidature",
            action=url_for("modifier_candidature", identifiant=identifiant),
            bouton="Enregistrer les modifications",
            valeurs=valeurs,
            enregistrer=lambda v: modifier(identifiant, **v),
            message="Candidature modifiée.",
        )

    @app.route("/candidature/<int:identifiant>/supprimer", methods=["GET", "POST"])
    def supprimer_candidature(identifiant):
        ligne = obtenir(identifiant)
        if ligne is None:
            abort(404)
        if request.method == "POST":
            if not jeton_valide():
                abort(400)
            supprimer(identifiant)
            flash("Candidature supprimée.")
            return redirect(url_for("accueil"), code=303)
        # GET : on ne supprime RIEN, on demande seulement confirmation.
        return render_template(
            "supprimer.html",
            titre="Supprimer cette candidature ?",
            libelle=f"{ligne['entreprise']} — {ligne['poste']}",
            action=url_for("supprimer_candidature", identifiant=identifiant),
            retour=url_for("accueil"),
        )

    # ---------------------------------------------------------------
    # Section 2 : les sites de recherche d'emploi
    # ---------------------------------------------------------------
    @app.get("/recherche")
    def recherche():
        return render_template("recherche.html", sites=sites.lister())

    @app.route("/recherche/nouveau", methods=["GET", "POST"])
    def nouveau_site():
        return formulaire(
            titre="Nouveau site de recherche",
            action=url_for("nouveau_site"),
            bouton="Enregistrer",
            valeurs={nom: "" for nom in CHAMPS_SITE},
            enregistrer=lambda v: sites.ajouter(**v),
            message="Site ajouté.",
            champs=CHAMPS_SITE,
            gabarit="site_formulaire.html",
            retour="recherche",
            longueurs=sites.LONGUEUR_MAX,
        )

    @app.route("/recherche/<int:identifiant>/modifier", methods=["GET", "POST"])
    def modifier_site(identifiant):
        ligne = sites.obtenir(identifiant)
        if ligne is None:
            abort(404)
        return formulaire(
            titre="Modifier le site",
            action=url_for("modifier_site", identifiant=identifiant),
            bouton="Enregistrer les modifications",
            valeurs={nom: ligne[nom] or "" for nom in CHAMPS_SITE},
            enregistrer=lambda v: sites.modifier(identifiant, **v),
            message="Site modifié.",
            champs=CHAMPS_SITE,
            gabarit="site_formulaire.html",
            retour="recherche",
            longueurs=sites.LONGUEUR_MAX,
        )

    @app.route("/recherche/<int:identifiant>/supprimer", methods=["GET", "POST"])
    def supprimer_site(identifiant):
        ligne = sites.obtenir(identifiant)
        if ligne is None:
            abort(404)
        if request.method == "POST":
            if not jeton_valide():
                abort(400)
            sites.supprimer(identifiant)
            flash("Site supprimé.")
            return redirect(url_for("recherche"), code=303)
        return render_template(
            "supprimer.html",
            titre="Supprimer ce site ?",
            libelle=ligne["nom"],
            action=url_for("supprimer_site", identifiant=identifiant),
            retour=url_for("recherche"),
        )

    # Une commande de terminal : python -m flask --app app seed
    @app.cli.command("seed")
    def seed():
        """Ajoute des données FICTIVES, section par section, seulement si elle est vide."""
        if lister():
            print("Candidatures : la table contient déjà des données, rien ajouté.")
        else:
            # Chaque exemple est un dictionnaire : nom du paramètre -> valeur.
            exemples = [
                {"entreprise": "Entreprise Exemple A", "poste": "Développeur web",
                 "technologies": "HTML, CSS, JavaScript",
                 "lien": "https://example.com/offre-1", "statut": "postule",
                 "date_candidature": "2026-10-20", "notes": "Donnée fictive."},
                {"entreprise": "Entreprise Exemple B", "poste": "Développeur Python",
                 "technologies": "Python, Flask, SQL",
                 "lien": "https://example.com/offre-2", "statut": "entretien",
                 "date_candidature": "2026-10-22",
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

        if sites.lister():
            print("Sites : la table contient déjà des données, rien ajouté.")
        else:
            # Identifiants et mots de passe INVENTÉS : ne mets jamais les vrais ici.
            exemples_sites = [
                {"nom": "Indeed", "lien": "https://fr.indeed.com",
                 "utilisateur": "demo@example.com", "mot_de_passe": "demo-indeed-1"},
                {"nom": "LinkedIn", "lien": "https://www.linkedin.com/jobs",
                 "utilisateur": "demo@example.com", "mot_de_passe": "demo-linkedin-2"},
                {"nom": "HelloWork", "lien": "https://www.hellowork.com",
                 "utilisateur": "demo_user", "mot_de_passe": "demo-hellowork-3"},
                {"nom": "Welcome to the Jungle",
                 "lien": "https://www.welcometothejungle.com",
                 "utilisateur": "demo_user", "mot_de_passe": "demo-wttj-4"},
            ]
            for exemple in exemples_sites:
                sites.ajouter(**exemple)
            print(f"{len(exemples_sites)} sites fictifs ajoutés.")

    return app


if __name__ == "__main__":
    # debug=True : acceptable ici car le serveur n'écoute que sur ton PC (127.0.0.1).
    # Ne l'active JAMAIS sur un serveur accessible depuis Internet.
    create_app().run(host="127.0.0.1", port=5000, debug=True)