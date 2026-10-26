# ============================================================
# À QUOI SERT CE FICHIER ?
# Il vérifie que generateur.py fait bien son travail. Il ne fabrique aucun mot de
# passe pour toi : il lance les fonctions du générateur et contrôle les résultats.
# Pour le lancer : python -m unittest -v
# ("-m" veut dire "lance ce module", "-v" affiche le détail de chaque test.)
# unittest trouve tout seul les fichiers dont le nom commence par "test".
# ============================================================

# Modules fournis avec Python, rien à installer :
import contextlib  # outils pour le bloc "with" (ici : rediriger ce que le programme affiche)
import io  # contient StringIO, un "faux fichier" gardé en mémoire
import string  # les listes de lettres et de chiffres toutes prêtes
import unittest  # le module de tests de Python

# Traduction : "Depuis le fichier generateur.py (sans le .py), importe ces noms."
# Les parenthèses permettent d'écrire la liste sur plusieurs lignes.
# C'est l'équivalent du require('./app') de Node, mais on choisit ce qu'on récupère.
from generateur import (AMBIGUS, LONGUEUR_MAX, LONGUEUR_MIN, SYMBOLES,
                        construire_jeux, generer, main)


# ============================================================
# GROUPE 1 : tester la fonction generer()
# ============================================================
# Traduction : "Je crée un groupe de tests nommé TestGenerer. Il hérite de
# unittest.TestCase", ce qui lui donne les outils self.assertEqual, self.assertTrue...
class TestGenerer(unittest.TestCase):

    # Un test. "self" doit toujours être le premier paramètre d'une méthode de classe.
    def test_longueur_respectee(self):
        # Traduction : "pour chaque valeur n du groupe (8, 16, 64, 128)".
        # Les parenthèses avec des virgules forment un "tuple" : une liste qu'on ne
        # peut pas modifier.
        for n in (LONGUEUR_MIN, 16, 64, LONGUEUR_MAX):
            # len(texte) compte les caractères.
            # assertEqual(a, b) : le test réussit si a == b, sinon il échoue.
            self.assertEqual(len(generer(n)), n)

    def test_contient_chaque_type_meme_au_minimum(self):
        # 200 essais à la longueur minimale : sans le tirage forcé de generer(), un type
        # manquerait presque à coup sûr au moins une fois sur ces 200.
        # Le "_" est le nom d'une variable dont on n'a pas besoin : on répète juste 200 fois.
        for _ in range(200):
            mdp = generer(LONGUEUR_MIN)
            # any(...) répond "vrai" si AU MOINS UN élément respecte la condition.
            # Lecture : "existe-t-il un caractère c du mot de passe qui est une minuscule ?"
            # "c in texte" vaut vrai si le caractère c se trouve dans le texte.
            # assertTrue(x) : le test réussit si x est vrai.
            self.assertTrue(any(c in string.ascii_lowercase for c in mdp))
            self.assertTrue(any(c in string.ascii_uppercase for c in mdp))
            self.assertTrue(any(c in string.digits for c in mdp))
            self.assertTrue(any(c in SYMBOLES for c in mdp))

    def test_sans_symboles(self):
        for _ in range(100):
            # .isalnum() répond "vrai" si le texte ne contient QUE des lettres et des chiffres.
            # Si un symbole s'était glissé dedans, ce serait faux et le test échouerait.
            self.assertTrue(generer(32, symboles=False).isalnum())

    def test_sans_ambigus(self):
        for _ in range(200):
            mdp = generer(32, sans_ambigus=True)
            # assertFalse(x) : le test réussit si x est faux.
            # Lecture : "aucun caractère du mot de passe n'est dans la liste des ambigus".
            self.assertFalse(any(c in AMBIGUS for c in mdp))

    def test_uniquement_des_caracteres_autorises(self):
        # Les jeux autorisés sans symboles, recollés en un seul texte. Le "*" n'est pas
        # nécessaire ici : on passe symboles=False par son nom.
        autorises = "".join(construire_jeux(symboles=False))
        for _ in range(100):
            # all(...) répond "vrai" si TOUS les éléments respectent la condition.
            # Lecture : "chaque caractère du mot de passe fait partie des autorisés".
            self.assertTrue(all(c in autorises for c in generer(40, symboles=False)))

    def test_refuse_une_longueur_invalide(self):
        # On essaie plusieurs valeurs INVALIDES, de natures différentes :
        #   0 et -1               : trop petites
        #   LONGUEUR_MIN - 1      : juste en dessous du minimum (7)
        #   LONGUEUR_MAX + 1      : juste au-dessus du maximum (129)
        #   "16"                  : un texte, pas un nombre
        #   16.0                  : un nombre à virgule, pas un entier
        #   True                  : un booléen (Python le prend pour 1 si on n'y prend garde)
        for n in (0, -1, LONGUEUR_MIN - 1, LONGUEUR_MAX + 1, "16", 16.0, True):
            # "with self.assertRaises(ValueError):" se lit : "dans ce bloc, je m'ATTENDS
            # à une erreur ValueError. Le test réussit si elle se produit, et échoue
            # si le code se déroule sans erreur."
            # msg=... est le message affiché si l'erreur n'a PAS eu lieu.
            # f"...{n!r}" insère la valeur n telle qu'on l'écrirait dans le code :
            # "16" avec ses guillemets, ce qui distingue le texte "16" du nombre 16.
            with self.assertRaises(ValueError, msg=f"devrait refuser : {n!r}"):
                generer(n)

    def test_refuse_si_aucun_type_choisi(self):
        with self.assertRaises(ValueError):
            generer(16, minuscules=False, majuscules=False, chiffres=False, symboles=False)

    def test_les_mots_de_passe_sont_differents(self):
        # 100 tirages de 16 caractères : une collision serait un signe de défaut grave.
        # Les accolades { ... for ... } fabriquent un "set" (ensemble) : une collection
        # où chaque valeur n'existe qu'une seule fois. Si deux mots de passe étaient
        # identiques, l'ensemble en contiendrait moins de 100.
        # Le "_" : on n'utilise pas la variable de la boucle.
        self.assertEqual(len({generer(16) for _ in range(100)}), 100)


# ============================================================
# UNE FONCTION D'AIDE (ce n'est pas un test)
# Son nom ne commence pas par "test" et elle n'est pas dans une classe de tests :
# unittest ne la lance donc pas toute seule. Elle sert aux tests du groupe 2.
# ============================================================
def lancer(args):
    """Appelle main() en capturant ce qu'il affiche."""
    # StringIO fabrique un "faux terminal" gardé en mémoire : on y envoie ce que le
    # programme affiche, au lieu de l'afficher à l'écran, pour pouvoir le vérifier.
    # Une affectation multiple : sortie reçoit le premier, erreur le second.
    sortie, erreur = io.StringIO(), io.StringIO()

    # "with A, B:" utilise deux choses en même temps.
    # redirect_stdout : pendant ce bloc, tout ce que print() affiche normalement
    # va dans "sortie". redirect_stderr : pareil, pour la sortie des erreurs.
    # À la fin du bloc, tout revient à la normale automatiquement.
    with contextlib.redirect_stdout(sortie), contextlib.redirect_stderr(erreur):
        code = main(args)

    # .getvalue() lit tout ce qui a été capturé. La fonction renvoie trois valeurs
    # d'un coup (un "tuple") : le code de retour, ce qui a été affiché, et les erreurs.
    return code, sortie.getvalue(), erreur.getvalue()


# ============================================================
# GROUPE 2 : tester la ligne de commande (la fonction main)
# ============================================================
class TestLigneDeCommande(unittest.TestCase):

    def test_commande_normale(self):
        # On appelle main avec ["-l", "20", "-n", "3"], comme si on avait tapé
        # python generateur.py -l 20 -n 3.
        # Cette ligne "déballe" les trois valeurs renvoyées par lancer() dans trois variables.
        code, sortie, erreur = lancer(["-l", "20", "-n", "3"])
        self.assertEqual(code, 0)  # 0 = tout s'est bien passé

        # .splitlines() découpe le texte affiché en une liste de lignes
        lignes = sortie.splitlines()
        self.assertEqual(len(lignes), 3)  # 3 mots de passe demandés, 3 lignes
        # Chaque ligne doit faire exactement 20 caractères
        self.assertTrue(all(len(ligne) == 20 for ligne in lignes))

        # assertIn(a, b) : réussit si a se trouve dans b.
        # L'estimation de force va sur la sortie des ERREURS, pas sur la sortie normale :
        # ainsi, si on redirige la sortie vers un fichier, seuls les mots de passe y vont.
        self.assertIn("Entropie", erreur)
        # assertNotIn : l'inverse, réussit si a ne se trouve PAS dans b
        self.assertNotIn("Entropie", sortie)

    def test_longueur_invalide_renvoie_2(self):
        # -l 3 est trop court (le minimum est 8)
        code, sortie, erreur = lancer(["-l", "3"])
        self.assertEqual(code, 2)  # 2 = une erreur a eu lieu
        self.assertEqual(sortie, "")  # aucun mot de passe n'a été affiché
        self.assertIn("Erreur", erreur)  # un message d'erreur a bien été écrit

    def test_aucun_type_renvoie_2(self):
        # Le "_" ne retient que le code : on ignore les deux autres valeurs renvoyées
        code, _, _ = lancer(["--sans-minuscules", "--sans-majuscules",
                             "--sans-chiffres", "--sans-symboles"])
        self.assertEqual(code, 2)


# ============================================================
# LE POINT D'ENTRÉE (le même principe que dans generateur.py)
# ============================================================
# Cette condition permet de lancer ce fichier directement (python test_generateur.py).
# unittest.main() trouve alors tous les groupes de tests du fichier et les exécute.
# Avec "python -m unittest", cette ligne n'est pas utilisée.
if __name__ == "__main__":
    unittest.main()