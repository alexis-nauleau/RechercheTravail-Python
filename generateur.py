"""Générateur de mots de passe aléatoires (ligne de commande).

Ce texte entre trois guillemets, tout en haut du fichier, s'appelle une "docstring" :
c'est la description du fichier. Python la garde en mémoire, ce n'est pas un simple
commentaire.

On utilise le module "secrets", conçu pour la sécurité. Le module "random" ne doit
JAMAIS servir à fabriquer un mot de passe : ses résultats sont prévisibles.
"""

import argparse  # lit les options tapées dans le terminal (--longueur, --sans-symboles...)
import math  # fonctions mathématiques (ici : le logarithme)
import secrets  # tirage au sort sécurisé, adapté aux mots de passe
import string  # contient des listes de lettres et de chiffres toutes prêtes
import sys  # accès au système : sorties du programme, code de retour


# LES CONSTANTES
# En Python, on écrit en MAJUSCULES le nom d'une valeur qu'on ne changera jamais.

MINUSCULES = string.ascii_lowercase
MAJUSCULES = string.ascii_uppercase
CHIFFRES = string.digits
SYMBOLES = "!@#$%^&*()-_=+[]{};:,.?"
AMBIGUS = "Il1O0o"

LONGUEUR_MIN = 8
LONGUEUR_MAX = 128


# FONCTION 1 : construire_jeux
# Elle décide QUELS types de caractères on a le droit d'utiliser.
# Traduction : "Définis une fonction nommée construire_jeux, avec cinq paramètres.
# Chaque paramètre a une valeur par défaut : si on n'en donne pas, c'est celle-là
# qui sert." 
def construire_jeux(minuscules=True, majuscules=True, chiffres=True, symboles=True,
                    sans_ambigus=False):
    """Renvoie la liste des jeux de caractères retenus (chaînes non vides)."""
    candidats = []
    # .append() ajoute un élément à la fin de la liste.
    if minuscules:
        candidats.append(MINUSCULES)
    if majuscules:
        candidats.append(MAJUSCULES)
    if chiffres:
        candidats.append(CHIFFRES)
    if symboles:
        candidats.append(SYMBOLES)

    # La liste, pas le therme tableau qu'on va renvoyer, vide pour l'instant
    jeux = []

    # Traduction : "Pour chaque jeu de la liste candidats, fais ce qui suit."
    for jeu in candidats:
        if sans_ambigus:
            # On reconstruit le jeu en retirant les caractères ambigus.
            #   "".join(...)          : recolle tous les caractères gardés en un seul texte
            # Exemple : "abc0" devient "abc" (le 0 est retiré).
            jeu = "".join(c for c in jeu if c not in AMBIGUS)
        # en Python, un texte non vide compte comme "vrai".
        if jeu:
            jeux.append(jeu)

    return jeux


# FONCTION 2 : generer
# Le "*" qui suit veut dire : "tout ce qui vient après doit être écrit avec son nom".
def generer(longueur=16, *, minuscules=True, majuscules=True, chiffres=True,
            symboles=True, sans_ambigus=False):
    """Fabrique un mot de passe. Lève ValueError si les paramètres sont invalides."""

    # bool est un sous-type de int en Python : True passerait pour 1 sans ce test.
    # Traduction : "si longueur est un booléen, OU si longueur n'est PAS un entier,
    # alors c'est invalide".
    # isinstance(x, int) répond à la question "x est-il un nombre entier ?".
    if isinstance(longueur, bool) or not isinstance(longueur, int):
        # "raise" déclenche une erreur : la fonction s'arrête ici.
        # ValueError est le type d'erreur de Python pour "valeur inacceptable".
        raise ValueError("La longueur doit être un nombre entier.")

    # En Python, on peut chaîner les comparaisons : "a <= x <= b" veut dire
    # "x est compris entre a et b". Le "not" devant s'applique à toute la phrase.
    if not LONGUEUR_MIN <= longueur <= LONGUEUR_MAX:
        # Le "f" devant les guillemets crée un "f-string" : ce qui est entre { } est
        # remplacé par sa valeur. Ici : "entre 8 et 128".
        raise ValueError(
            f"La longueur doit être comprise entre {LONGUEUR_MIN} et {LONGUEUR_MAX}."
        )

    # On demande à la fonction 1 la liste des jeux autorisés
    jeux = construire_jeux(minuscules, majuscules, chiffres, symboles, sans_ambigus)
    # Traduction : "si la liste jeux est vide" (on a tout désactivé)
    if not jeux:
        raise ValueError("Choisis au moins un type de caractères.")

    # --- Fabrication du mot de passe, en trois temps ---

    # 1. Un caractère de chaque type retenu : tous les types demandés sont présents.
    # Lecture : "pour chaque jeu de la liste jeux, tire un caractère au hasard dedans".
    # secrets.choice(jeu) choisit UN caractère au hasard, de façon sécurisée.
    # Les crochets autour créent une nouvelle liste avec tous ces caractères.
    # Exemple avec 4 jeux : ["k", "R", "7", "!"]
    caracteres = [secrets.choice(jeu) for jeu in jeux]

    # 2. Le reste est tiré dans l'ensemble des caractères autorisés.
    # "".join(jeux) recolle tous les jeux en un seul grand texte de caractères possibles.
    tous = "".join(jeux)
    # "+=" signifie "ajoute à la liste". range(n) produit les nombres de 0 à n-1.
    # On veut tirer (longueur - nombre déjà tirés) caractères : exemple 16 - 4 = 12.
    # Le "_" est le nom habituel d'une variable dont on n'a pas besoin : ici, on se
    # contente de répéter l'opération autant de fois que nécessaire.
    caracteres += [secrets.choice(tous) for _ in range(longueur - len(caracteres))]

    # 3. On mélange, sinon les premiers caractères suivraient toujours le même ordre
    # de types (minuscule, majuscule, chiffre, symbole, puis le reste).
    # SystemRandom utilise la source aléatoire du système d'exploitation.
    # .shuffle() mélange la liste sur place (il ne renvoie rien).
    secrets.SystemRandom().shuffle(caracteres)

    # On recolle la liste de caractères en un seul texte et on le renvoie
    return "".join(caracteres)


# ============================================================
# FONCTION 3 : entropie_bits
# Elle estime la FORCE du mot de passe.
# ============================================================
def entropie_bits(longueur, jeux):
    """Estimation de la force : longueur x log2(taille de l'alphabet).

    C'est un ordre de grandeur. Imposer un caractère de chaque type la réduit très
    légèrement. Elle ne vaut que pour un mot de passe VRAIMENT aléatoire : une phrase
    que tu choisis toi-même n'a pas cette force.
    """
    # len(texte) donne le nombre de caractères : la taille de l'alphabet utilisé.
    # math.log2(x) calcule le logarithme en base 2 : combien de "bits" (de oui/non)
    # il faut pour désigner un caractère parmi x. Multiplié par la longueur, on obtient
    # la force totale. Plus le nombre est grand, plus le mot de passe est dur à deviner.
    return longueur * math.log2(len("".join(jeux)))


# ============================================================
# FONCTION 4 : lire_arguments
# Elle lit ce que l'utilisateur tape dans le terminal après le nom du programme.
# Exemple : python generateur.py -l 24 --sans-symboles
# ============================================================
# "argv=None" : par défaut, argparse lit ce que tape l'utilisateur. Les tests, eux,
# passent directement une liste d'arguments pour simuler une commande.
def lire_arguments(argv=None):
    # On crée le "lecteur d'options", avec une description affichée dans l'aide (-h)
    p = argparse.ArgumentParser(description="Génère des mots de passe aléatoires.")

    # add_argument déclare une option :
    #   "-l", "--longueur" : deux écritures possibles, courte et longue
    #   type=int           : convertit ce qui est tapé en nombre entier
    #   default=16         : valeur si l'utilisateur ne précise rien
    #   help=...           : texte affiché dans l'aide
    # Ici, f"..." insère les constantes dans le texte d'aide.
    p.add_argument("-l", "--longueur", type=int, default=16,
                   help=f"longueur ({LONGUEUR_MIN} à {LONGUEUR_MAX}, défaut 16)")
    p.add_argument("-n", "--nombre", type=int, default=1,
                   help="combien de mots de passe (1 à 50, défaut 1)")

    # action="store_true" : une option sans valeur, un simple interrupteur.
    # Absente, elle vaut False. Présente (python generateur.py --sans-chiffres), elle vaut True.
    p.add_argument("--sans-minuscules", action="store_true")
    p.add_argument("--sans-majuscules", action="store_true")
    p.add_argument("--sans-chiffres", action="store_true")
    p.add_argument("--sans-symboles", action="store_true",
                   help="utile pour les sites qui refusent certains symboles")
    p.add_argument("--sans-ambigus", action="store_true",
                   help="écarte les caractères qu'on confond (I l 1 O 0 o)")

    # parse_args lit réellement les arguments et renvoie un objet où chaque option
    # est accessible par son nom. Les tirets deviennent des tirets bas :
    # --sans-minuscules est lu par a.sans_minuscules.
    # Si l'utilisateur tape n'importe quoi (-l abc), argparse affiche l'erreur et
    # arrête le programme de lui-même.
    return p.parse_args(argv)


# ============================================================
# FONCTION 5 : main
# C'est le chef d'orchestre : elle appelle les autres dans l'ordre.
# ============================================================
def main(argv=None):
    # "a" contient toutes les options lues : a.longueur, a.nombre, a.sans_symboles...
    a = lire_arguments(argv)

    # dict(...) crée un dictionnaire : des paires "nom = valeur" (comme un objet JavaScript).
    # "not x" inverse un booléen : si l'utilisateur a mis --sans-symboles (True),
    # alors symboles vaut not True, donc False.
    options = dict(
        minuscules=not a.sans_minuscules,
        majuscules=not a.sans_majuscules,
        chiffres=not a.sans_chiffres,
        symboles=not a.sans_symboles,
        sans_ambigus=a.sans_ambigus,
    )

    # try / except : "essaie ce bloc ; si une ValueError se produit, saute au except".
    # C'est l'équivalent du try / catch de JavaScript.
    try:
        # Vérifie que le nombre demandé est entre 1 et 50
        if not 1 <= a.nombre <= 50:
            raise ValueError("Le nombre doit être compris entre 1 et 50.")

        # Le "**" avant options "déballe" le dictionnaire en arguments nommés :
        # construire_jeux(**options) revient à écrire
        # construire_jeux(minuscules=..., majuscules=..., chiffres=..., ...)
        jeux = construire_jeux(**options)

        # Traduction : "répète a.nombre fois". Le "_" signifie qu'on n'utilise pas
        # la variable de la boucle.
        for _ in range(a.nombre):
            # print affiche dans le terminal. Même déballage ** pour passer les options.
            print(generer(a.longueur, **options))

    # Traduction : "si une ValueError a eu lieu, "e" contient l'erreur". Elle peut
    # venir de generer() (longueur invalide, aucun type choisi) ou du test ci-dessus.
    except ValueError as e:
        # file=sys.stderr envoie le message sur la sortie des ERREURS, distincte de
        # la sortie normale. Ainsi, si on redirige la sortie vers un fichier, les
        # messages d'erreur ne s'y mélangent pas.
        print(f"Erreur : {e}", file=sys.stderr)
        # Le programme se termine par le code 2. Par convention : 0 = tout va bien,
        # tout autre nombre = il y a eu un problème.
        return 2

    # L'estimation va sur stderr : si tu rediriges la sortie, seuls les mots de passe passent.
    # Dans {...:.0f}, le ".0f" signifie "affiche le nombre avec 0 chiffre après la virgule".
    print(f"Entropie estimée : {entropie_bits(a.longueur, jeux):.0f} bits", file=sys.stderr)
    return 0


# ============================================================
# LE POINT D'ENTRÉE
# ============================================================
# __name__ est une variable que Python remplit tout seul :
#   - quand tu lances "python generateur.py", elle vaut "__main__"
#   - quand un AUTRE fichier fait "import generateur" (c'est le cas des tests),
#     elle vaut "generateur"
# Cette condition veut donc dire : "lance main() seulement si on a lancé CE fichier
# directement". Sans elle, importer le fichier dans les tests lancerait le programme.
# sys.exit(...) arrête le programme en transmettant le code renvoyé par main()
# (0 ou 2).
if __name__ == "__main__":
    sys.exit(main())