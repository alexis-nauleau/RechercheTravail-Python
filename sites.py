"""Les sites de recherche d'emploi (Indeed, LinkedIn...) : validation et accès à la base.

ATTENTION : mode démo. Les mots de passe sont rangés EN CLAIR dans la base. N'y mets
jamais un vrai mot de passe. (Pour de vrais mots de passe, il faudrait les chiffrer
avec coffre.py avant de les enregistrer.)
"""
# On réutilise les fonctions de vérification déjà écrites pour les candidatures.
# (Le "_" signifie "réservé à l'origine", on l'importe ici en connaissance de cause.)
from candidatures import _lien, _texte
from db import get_db

# Longueurs maximales, aussi lues par le formulaire (attribut maxlength).
LONGUEUR_MAX = {"nom": 100, "lien": 500, "utilisateur": 150, "mot_de_passe": 200}

_COLONNES = "id, nom, lien, utilisateur, mot_de_passe"


def _mot_de_passe(valeur):
    """Vérifie un mot de passe SANS le nettoyer : les espaces en font partie."""
    if valeur is not None and not isinstance(valeur, str):
        raise ValueError("Le champ « mot_de_passe » doit être un texte.")
    if not valeur:  # None ou "" : facultatif, rien à enregistrer
        return None
    if len(valeur) > LONGUEUR_MAX["mot_de_passe"]:
        raise ValueError(
            f"Le champ « mot_de_passe » dépasse {LONGUEUR_MAX['mot_de_passe']} caractères."
        )
    return valeur


def _valider(nom, lien, utilisateur, mot_de_passe):
    """Vérifie tous les champs et renvoie les valeurs propres dans un dictionnaire."""
    return {
        "nom": _texte(nom, "nom", obligatoire=True, maximum=LONGUEUR_MAX["nom"]),
        "lien": _lien(lien),
        "utilisateur": _texte(utilisateur, "utilisateur",
                              maximum=LONGUEUR_MAX["utilisateur"]),
        "mot_de_passe": _mot_de_passe(mot_de_passe),
    }


def lister():
    """Renvoie tous les sites, classés par nom (sans tenir compte des majuscules)."""
    # COLLATE NOCASE : "indeed" et "Indeed" sont classés ensemble, comme dans un annuaire.
    return get_db().execute(
        f"SELECT {_COLONNES} FROM sites ORDER BY nom COLLATE NOCASE, id"
    ).fetchall()


def obtenir(identifiant):
    """Renvoie UN site (par son id), ou None s'il n'existe pas."""
    return get_db().execute(
        f"SELECT {_COLONNES} FROM sites WHERE id = ?", (identifiant,)
    ).fetchone()


def ajouter(nom, lien=None, utilisateur=None, mot_de_passe=None):
    """Valide puis enregistre un site. Lève ValueError si un champ est invalide."""
    valeurs = _valider(nom, lien, utilisateur, mot_de_passe)
    connexion = get_db()
    curseur = connexion.execute(
        "INSERT INTO sites (nom, lien, utilisateur, mot_de_passe)"
        " VALUES (:nom, :lien, :utilisateur, :mot_de_passe)",
        valeurs,
    )
    connexion.commit()
    return curseur.lastrowid


def modifier(identifiant, nom, lien=None, utilisateur=None, mot_de_passe=None):
    """Valide puis met à jour un site existant. Lève ValueError sinon."""
    valeurs = _valider(nom, lien, utilisateur, mot_de_passe)
    valeurs["id"] = identifiant
    connexion = get_db()
    curseur = connexion.execute(
        "UPDATE sites SET nom = :nom, lien = :lien, utilisateur = :utilisateur,"
        " mot_de_passe = :mot_de_passe WHERE id = :id",
        valeurs,
    )
    connexion.commit()
    if curseur.rowcount == 0:
        raise ValueError("Ce site n'existe plus.")


def supprimer(identifiant):
    """Supprime un site. Renvoie True s'il existait, False sinon."""
    connexion = get_db()
    curseur = connexion.execute("DELETE FROM sites WHERE id = ?", (identifiant,))
    connexion.commit()
    return curseur.rowcount > 0