"""Validation et accès aux candidatures.

Ce fichier contient trois choses :
  - des fonctions qui VÉRIFIENT ce qu'on veut enregistrer (_texte, _lien, _date,
    _technologies) ;
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
LONGUEUR_MAX = {"entreprise": 100, "poste": 150, "technologies": 500, "lien": 500,
                "notes": 2000}

# Pour les technologies : combien au maximum, et quelle longueur pour chacune.
MAX_TECHNOLOGIES = 10
LONGUEUR_TECHNOLOGIE = 30

# Les colonnes qu'on lit dans la table.
_COLONNES = "id, entreprise, poste, technologies, lien, statut, date_candidature, notes"
# L'ordre d'affichage : les plus récentes d'abord.
# COALESCE prend la première valeur non vide : la date de candidature si elle existe,
# sinon la date de création de la ligne (substr garde les 10 premiers caractères,
# donc AAAA-MM-JJ). "DESC" signifie du plus grand au plus petit, donc du plus récent
# au plus ancien. "id DESC" départage deux lignes de même date.
_ORDRE = "ORDER BY COALESCE(date_candidature, substr(cree_le, 1, 10)) DESC, id DESC"


def _texte(valeur, nom, obligatoire=False, maximum=None):
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
    # "maximum" permet à un autre fichier (sites.py) de fixer sa propre limite.
    limite = LONGUEUR_MAX[nom] if maximum is None else maximum
    if len(texte) > limite:
        raise ValueError(f"Le champ « {nom} » dépasse {limite} caractères.")
    return texte or None


def _technologies(valeur):
    """Nettoie une liste de technologies écrite "Python, Flask, SQL".

    On la découpe aux virgules, on enlève les espaces et les vides, on supprime les
    doublons (sans tenir compte des majuscules), puis on la recolle proprement.
    """
    # _texte vérifie déjà le type et la longueur totale du champ.
    texte = _texte(valeur, "technologies")
    if texte is None:
        return None

    # Une "liste" Python se note avec des crochets. On la remplit technologie par technologie.
    gardees = []
    deja_vues = set()  # un "set" retient des éléments sans doublon, très rapide à interroger
    for morceau in texte.split(","):  # .split(",") coupe le texte à chaque virgule
        techno = morceau.strip()
        if not techno:  # "Python,,SQL" : le morceau vide est simplement ignoré
            continue
        if len(techno) > LONGUEUR_TECHNOLOGIE:
            raise ValueError(
                f"Une technologie dépasse {LONGUEUR_TECHNOLOGIE} caractères."
            )
        # casefold() met en minuscules : "python" et "Python" comptent pour un seul.
        cle = techno.casefold()
        if cle not in deja_vues:
            deja_vues.add(cle)
            gardees.append(techno)

    if len(gardees) > MAX_TECHNOLOGIES:
        raise ValueError(f"Au maximum {MAX_TECHNOLOGIES} technologies.")
    # ", ".join(liste) recolle les éléments avec ", " entre chacun. Vide -> None.
    return ", ".join(gardees) or None


def separer_technologies(texte):
    """Transforme "Python, Flask" (rangé en base) en liste ["Python", "Flask"].

    Sert à l'affichage : une pastille par technologie.
    """
    if not texte:
        return []
    # Compréhension de liste : "pour chaque morceau du texte coupé, garde-le s'il n'est pas vide"
    return [morceau.strip() for morceau in texte.split(",") if morceau.strip()]


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

def _valider(entreprise, poste, lien, statut, date_candidature, notes, technologies):
    """Vérifie TOUS les champs et renvoie les valeurs propres, dans un dictionnaire.

    Utilisée par ajouter() ET par modifier() : les règles sont écrites une seule fois.
    Lève ValueError dès qu'un champ est invalide.
    """
    valeurs = {
        "entreprise": _texte(entreprise, "entreprise", obligatoire=True),
        "poste": _texte(poste, "poste", obligatoire=True),
        "technologies": _technologies(technologies),
        "lien": _lien(lien),
        "notes": _texte(notes, "notes"),
        "date_candidature": _date(date_candidature),
        "statut": statut,
    }
    # "statut not in STATUTS" : le statut doit être l'une des clés du dictionnaire
    if statut not in STATUTS:
        raise ValueError("Statut inconnu.")
    return valeurs


def ajouter(entreprise, poste, lien=None, statut="a_postuler", date_candidature=None,
            notes=None, technologies=None):
    """Valide puis enregistre une candidature. Lève ValueError si un champ est invalide."""
    valeurs = _valider(entreprise, poste, lien, statut, date_candidature, notes,
                       technologies)
    connexion = get_db()
    # Les ":nom" sont remplis par le dictionnaire de même nom. Comme avec les "?",
    # aucune valeur n'est collée dans le texte SQL : pas d'injection possible.
    curseur = connexion.execute(
        "INSERT INTO candidatures"
        " (entreprise, poste, technologies, lien, statut, date_candidature, notes)"
        " VALUES (:entreprise, :poste, :technologies, :lien, :statut,"
        " :date_candidature, :notes)",
        valeurs,
    )
    connexion.commit()  # sans commit, l'ajout est perdu à la fermeture de la connexion
    return curseur.lastrowid  # l'identifiant de la ligne qui vient d'être créée


def obtenir(identifiant):
    """Renvoie UNE candidature (par son id), ou None si elle n'existe pas."""
    return get_db().execute(
        f"SELECT {_COLONNES} FROM candidatures WHERE id = ?", (identifiant,)
    ).fetchone()  # fetchone : une seule ligne (ou None)


def modifier(identifiant, entreprise, poste, lien=None, statut="a_postuler",
             date_candidature=None, notes=None, technologies=None):
    """Valide puis met à jour une candidature existante. Lève ValueError sinon."""
    valeurs = _valider(entreprise, poste, lien, statut, date_candidature, notes,
                       technologies)
    valeurs["id"] = identifiant  # ajoute l'id au dictionnaire, pour le ":id" ci-dessous
    connexion = get_db()
    curseur = connexion.execute(
        "UPDATE candidatures SET entreprise = :entreprise, poste = :poste,"
        " technologies = :technologies, lien = :lien, statut = :statut,"
        " date_candidature = :date_candidature, notes = :notes"
        " WHERE id = :id",
        valeurs,
    )
    connexion.commit()
    # rowcount = nombre de lignes touchées. 0 : l'id n'existe pas (ou plus).
    if curseur.rowcount == 0:
        raise ValueError("Cette candidature n'existe plus.")


def supprimer(identifiant):
    """Supprime une candidature. Renvoie True si elle existait, False sinon."""
    connexion = get_db()
    curseur = connexion.execute("DELETE FROM candidatures WHERE id = ?", (identifiant,))
    connexion.commit()
    return curseur.rowcount > 0