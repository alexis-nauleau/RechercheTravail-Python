"""Chiffrement des identifiants avec un mot de passe maître.

Règle d'or : on n'écrit JAMAIS son propre algorithme de chiffrement. Ce fichier
assemble des briques éprouvées :
  - scrypt (fourni par Python) transforme le mot de passe maître en clé ;
  - Fernet (bibliothèque "cryptography") chiffre et authentifie les données.
"""
import base64  # encode des octets en texte sûr (lettres, chiffres, quelques symboles)
import hashlib  # contient scrypt
import secrets  # tirage au sort sécurisé

# On importe deux choses de la bibliothèque installée avec pip :
#   Fernet       : l'outil de chiffrement
#   InvalidToken : l'erreur qu'il lève quand un déchiffrement échoue
from cryptography.fernet import Fernet, InvalidToken

LONGUEUR_MIN_MAITRE = 12
TAILLE_SEL = 16

# Paramètres de scrypt : plus ils sont élevés, plus deviner un mot de passe coûte cher
# à un attaquant (et plus c'est lent pour toi : environ un dixième de seconde).
#   n = coût en calcul et en mémoire   r, p = réglages internes
#   dklen = longueur de la clé produite (32 octets, ce que Fernet exige)
#   maxmem = mémoire autorisée : la valeur par défaut de Python est trop juste pour n=2**15
# "2**15" signifie 2 puissance 15, donc 32768.
_SCRYPT = {"n": 2**15, "r": 8, "p": 1, "dklen": 32, "maxmem": 2**26}

# Un texte connu d'avance, chiffré avec la clé : s'il se déchiffre, la clé est la bonne.
_TEMOIN = "coffre-ok"


# Une classe vide qui hérite d'Exception : c'est un nouveau TYPE d'erreur.
# Le reste du code pourra écrire "except ErreurCoffre" sans attraper les autres erreurs.
class ErreurCoffre(Exception):
    """Clé incorrecte, ou données abîmées ou modifiées."""


def valider_mot_de_passe_maitre(mot_de_passe):
    """À appeler quand on CRÉE le mot de passe maître (pas quand on se connecte)."""
    if not isinstance(mot_de_passe, str) or len(mot_de_passe) < LONGUEUR_MIN_MAITRE:
        raise ValueError(
            f"Le mot de passe maître doit faire au moins {LONGUEUR_MIN_MAITRE} caractères."
        )


def nouveau_sel():
    """Un "sel" : des octets aléatoires, mélangés au mot de passe avant la
    transformation en clé. Il n'est PAS secret (on le range à côté des données) mais il
    doit être différent pour chaque coffre : deux personnes ayant le même mot de passe
    n'obtiennent ainsi pas la même clé."""
    return secrets.token_bytes(TAILLE_SEL)


def deriver_cle(mot_de_passe, sel):
    """Transforme le mot de passe maître en clé de chiffrement. Même mot de passe et
    même sel : toujours la même clé. Il est impossible de retrouver le mot de passe
    à partir de la clé."""
    # isinstance(sel, bytes) : le sel doit être des octets, pas un texte
    if not isinstance(mot_de_passe, str) or not isinstance(sel, bytes) or len(sel) != TAILLE_SEL:
        raise ValueError("Paramètres invalides.")
    # scrypt travaille sur des octets : on encode d'abord le mot de passe en UTF-8.
    # Le ** déballe le dictionnaire _SCRYPT en arguments nommés n=..., r=..., etc.
    brut = hashlib.scrypt(mot_de_passe.encode("utf-8"), salt=sel, **_SCRYPT)
    # Fernet attend la clé encodée en base64 (un texte sûr à manipuler)
    return base64.urlsafe_b64encode(brut)


def chiffrer(cle, texte):
    """Chiffre un texte. Renvoie un texte (le "jeton") qu'on peut ranger en base.

    Chiffrer deux fois le même texte donne deux jetons différents : Fernet ajoute un
    élément aléatoire à chaque fois."""
    if not isinstance(texte, str):
        raise ValueError("Seul un texte peut être chiffré.")
    # texte -> octets -> chiffrement -> octets chiffrés -> texte ASCII pour la base
    return Fernet(cle).encrypt(texte.encode("utf-8")).decode("ascii")


def dechiffrer(cle, jeton):
    """Déchiffre un jeton. Lève ErreurCoffre si la clé est fausse OU si le jeton a été
    modifié : Fernet vérifie une signature, une altération est toujours détectée."""
    # try / except : "essaie ; si l'une de ces erreurs se produit, saute au except".
    # Les trois erreurs entre parenthèses sont attrapées ensemble :
    #   InvalidToken : mauvaise clé ou jeton altéré
    #   ValueError   : clé mal formée, ou caractère non ASCII dans le jeton
    #   AttributeError : le jeton n'est pas un texte (None, par exemple)
    try:
        return Fernet(cle).decrypt(jeton.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, AttributeError):
        # On ne précise pas la cause : un attaquant n'a pas à savoir laquelle.
        # "from None" masque l'erreur technique d'origine.
        raise ErreurCoffre("Clé incorrecte ou données altérées.") from None


def creer_temoin(cle):
    """Le texte témoin chiffré, à ranger en base lors de la création du coffre."""
    return chiffrer(cle, _TEMOIN)


def cle_valide(cle, temoin):
    """Vrai si cette clé déchiffre bien le témoin, donc si le mot de passe est le bon."""
    try:
        return dechiffrer(cle, temoin) == _TEMOIN
    except ErreurCoffre:
        return False