"""Validation et accès aux candidatures.

Ce fichier contient trois choses :
  - des fonctions qui VÉRIFIENT ce qu'on veut enregistrer (_texte, _lien, _date) ;
  - une fonction qui LIT les candidatures (lister) ;
  - une fonction qui ENREGISTRE une candidature (ajouter).
Le reste de l'application n'a jamais besoin de connaître le SQL : elle passe par ici.
"""
# "from X import Y" charge UN élément précis d'un module (ou d'un autre fichier du projet).
from datetime import date  # le type "date" de Python
from urllib.parse import urlparse  # découpe une adresse web en morceaux

# STATUTS et get_db viennent de db.py : la liste des statuts autorisés, et la fonction
# qui ouvre la connexion à la base.
from db import STATUTS, get_db

# Longueurs maximales de chaque champ texte. Sans limite, quelqu'un pourrait enregistrer
# un texte énorme. Les accolades { } forment un "dictionnaire" : des paires nom -> valeur.
LONGUEUR_MAX = {"entreprise": 100, "poste": 150, "lien": 500, "notes": 2000}

# Les colonnes qu'on lit dans la table.
_COLONNES = "id, entreprise, poste, lien, statut, date_candidature, notes"
# L'ordre d'affichage : les plus récentes d'abord.
# COALESCE prend la première valeur non vide : la date de candidature si elle existe,
# sinon la date de création de la ligne (substr garde les 10 premiers caractères,
# donc AAAA-MM-JJ). "DESC" signifie du plus grand au plus petit, donc du plus récent
# au plus ancien. "id DESC" départage deux lignes de même date.
_ORDRE = "ORDER BY COALESCE(date_candidature, substr(cree_le, 1, 10)) DESC, id DESC"


def _texte(valeur, nom, obligatoire=False):
    """Nettoie un champ texte. Renvoie None si le champ est vide et facultatif.

    Le "_" devant le nom est une convention : "cette fonction est réservée à ce fichier,
    ne l'utilise pas depuis l'extérieur".
    """
    # Si on reçoit autre chose qu'un texte (un nombre, une liste...), on refuse.
    if valeur is not None and not isinstance(valeur, str):
        # f"...{nom}..." remplace {nom} par sa valeur : « entreprise », « poste »...
        raise ValueError(f"Le champ « {nom} » doit être un texte.")
    # (valeur or "") remplace None par un texte vide ; .strip() enlève les espaces
    # au début et à la fin.
    texte = (valeur or "").strip()
    if obligatoire and not texte:
        raise ValueError(f"Le champ « {nom} » est obligatoire.")
    if len(texte) > LONGUEUR_MAX[nom]:
        raise ValueError(f"Le champ « {nom} » dépasse {LONGUEUR_MAX[nom]} caractères.")
    # "texte or None" : un texte vide devient None (rien), sinon on garde le texte
    return texte or None


def _lien(valeur):
    """N'accepte que des adresses http:// ou https://.

    Une adresse comme "javascript:alert(1)" placée dans un lien exécuterait du code
    quand on clique : même avec la neutralisation du HTML, c'est un risque réel.
    """
    texte = _texte(valeur, "lien")
    if texte is None:  # lien facultatif : rien n'est saisi, rien n'est enregistré
        return None
    # urlparse découpe l'adresse en morceaux. Pour "https://example.com/offre" :
    #   scheme = "https"   netloc = "example.com"   path = "/offre"
    analysee = urlparse(texte)
    # On refuse si le début n'est ni http ni https, ou s'il n'y a pas de nom de site.
    if analysee.scheme not in ("http", "https") or not analysee.netloc:
        raise ValueError("Le lien doit commencer par http:// ou https://.")
    return texte


def _date(valeur):
    """N'accepte que le format AAAA-MM-JJ, avec une date qui existe."""
    if valeur is not None and not isinstance(valeur, str):
        raise ValueError("Date invalide (format AAAA-MM-JJ).")
    texte = (valeur or "").strip()
    if not texte:  # date facultative : vide, donc rien à enregistrer
        return None
    # try / except : "essaie ce bloc ; si une ValueError se produit, saute au except".
    try:
        # date.fromisoformat lit "2026-10-26" et refuse "2026-02-30" (ce jour n'existe pas)
        analysee = date.fromisoformat(texte)
    except ValueError:
        # "from None" masque l'erreur technique d'origine : on ne montre que notre message
        raise ValueError("Date invalide (format AAAA-MM-JJ).") from None
    # Les versions récentes de Python acceptent aussi "20261026". On exige l'écriture
    # exacte, pour que tout ce qui est rangé en base ait la même forme.
    if analysee.isoformat() != texte:
        raise ValueError("Date invalide (format AAAA-MM-JJ).")
    return texte


def lister(statut=None):
    """Renvoie les candidatures, éventuellement filtrées sur un statut."""
    connexion = get_db()
    # Les f-strings ci-dessous n'assemblent que des constantes de ce fichier
    # (_COLONNES et _ORDRE), jamais une valeur venue de l'utilisateur.
    if statut is None:
        # .execute envoie la requête SQL ; .fetchall() récupère toutes les lignes
        return connexion.execute(f"SELECT {_COLONNES} FROM candidatures {_ORDRE}").fetchall()
    # La valeur du statut passe par le "?" : elle est transmise À PART du texte SQL.
    # Même une valeur piégée comme "' OR 1=1 --" ne peut pas modifier la requête.
    # Le (statut,) avec la virgule est un "tuple" d'un seul élément.
    return connexion.execute(
        f"SELECT {_COLONNES} FROM candidatures WHERE statut = ? {_ORDRE}", (statut,)
    ).fetchall()


def ajouter(entreprise, poste, lien=None, statut="a_postuler", date_candidature=None,
            notes=None):
    """Valide puis enregistre une candidature. Lève ValueError si un champ est invalide."""
    # On vérifie CHAQUE champ avant d'écrire quoi que ce soit en base.
    # Si l'un d'eux est invalide, une ValueError est levée et on ne va pas plus loin.
    entreprise = _texte(entreprise, "entreprise", obligatoire=True)
    poste = _texte(poste, "poste", obligatoire=True)
    lien = _lien(lien)
    notes = _texte(notes, "notes")
    date_candidature = _date(date_candidature)
    # "statut not in STATUTS" : le statut doit être l'une des clés du dictionnaire
    if statut not in STATUTS:
        raise ValueError("Statut inconnu.")

    connexion = get_db()
    # Les six "?" sont remplis, dans l'ordre, par les six valeurs du tuple.
    # Aucune valeur n'est collée dans le texte SQL : c'est ce qui empêche l'injection SQL.
    curseur = connexion.execute(
        "INSERT INTO candidatures (entreprise, poste, lien, statut, date_candidature, notes)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (entreprise, poste, lien, statut, date_candidature, notes),
    )
    connexion.commit()  # sans commit, l'ajout est perdu à la fermeture de la connexion
    return curseur.lastrowid  # l'identifiant de la ligne qui vient d'être créée