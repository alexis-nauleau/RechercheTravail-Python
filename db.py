"""Connexion à la base SQLite et création de la table."""
import sqlite3

from flask import current_app, g

# Les statuts possibles : code rangé en base -> texte affiché à l'écran.
STATUTS = {
    "a_postuler": "À postuler",
    "postule": "Postulé",
    "entretien": "Entretien",
    "offre": "Offre reçue",
    "refus": "Refus",
}

# On fabrique la liste "'a_postuler', 'postule', ..." pour la contrainte SQL ci-dessous.
# Ce texte n'assemble que NOS constantes, jamais une valeur venue de l'utilisateur :
# c'est la seule situation où construire du SQL avec un f-string est acceptable.
_STATUTS_SQL = ", ".join(f"'{code}'" for code in STATUTS)

# Le schéma : la description de la table.
#   PRIMARY KEY AUTOINCREMENT : un identifiant unique, attribué automatiquement
#   NOT NULL                  : la colonne ne peut pas rester vide
#   CHECK (...)               : la base REFUSE un statut qui n'est pas dans la liste,
#                               même si le code Python avait un défaut
#   dates                     : SQLite n'a pas de vrai type "date" ; on range du texte
#                               au format AAAA-MM-JJ
#   technologies              : un seul texte, les technos séparées par des virgules
#                               ("Python, Flask, SQL"). Simple, et suffisant ici.
#   IF NOT EXISTS             : relancer ne recrée pas la table et n'efface rien
SCHEMA = f"""
CREATE TABLE IF NOT EXISTS candidatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entreprise TEXT NOT NULL,
    poste TEXT NOT NULL,
    technologies TEXT,
    lien TEXT,
    statut TEXT NOT NULL DEFAULT 'a_postuler' CHECK (statut IN ({_STATUTS_SQL})),
    date_candidature TEXT,
    notes TEXT,
    cree_le TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    lien TEXT,
    utilisateur TEXT,
    mot_de_passe TEXT,
    cree_le TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_db():
    """Renvoie la connexion de la requête en cours (elle est créée au premier appel)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        # Avec row_factory, chaque ligne se lit par nom de colonne : ligne["entreprise"]
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(erreur=None):
    """Ferme la connexion à la fin de la requête (Flask appelle cette fonction seul)."""
    connexion = g.pop("db", None)
    if connexion is not None:
        connexion.close()


def init_db():
    """Crée la table si elle n'existe pas."""
    connexion = get_db()
    connexion.executescript(SCHEMA)
    connexion.commit()


def init_app(app):
    # "À la fin de chaque requête, appelle close_db"
    app.teardown_appcontext(close_db)