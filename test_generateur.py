import contextlib
import io
import string
import unittest

from generateur import (AMBIGUS, LONGUEUR_MAX, LONGUEUR_MIN, SYMBOLES,
                        construire_jeux, generer, main)


class TestGenerer(unittest.TestCase):
    def test_longueur_respectee(self):
        for n in (LONGUEUR_MIN, 16, 64, LONGUEUR_MAX):
            self.assertEqual(len(generer(n)), n)

    def test_contient_chaque_type_meme_au_minimum(self):
        # 200 essais à la longueur minimale : sans le tirage forcé, un type
        # manquerait presque à coup sûr au moins une fois
        for _ in range(200):
            mdp = generer(LONGUEUR_MIN)
            self.assertTrue(any(c in string.ascii_lowercase for c in mdp))
            self.assertTrue(any(c in string.ascii_uppercase for c in mdp))
            self.assertTrue(any(c in string.digits for c in mdp))
            self.assertTrue(any(c in SYMBOLES for c in mdp))

    def test_sans_symboles(self):
        for _ in range(100):
            self.assertTrue(generer(32, symboles=False).isalnum())

    def test_sans_ambigus(self):
        for _ in range(200):
            mdp = generer(32, sans_ambigus=True)
            self.assertFalse(any(c in AMBIGUS for c in mdp))

    def test_uniquement_des_caracteres_autorises(self):
        autorises = "".join(construire_jeux(symboles=False))
        for _ in range(100):
            self.assertTrue(all(c in autorises for c in generer(40, symboles=False)))

    def test_refuse_une_longueur_invalide(self):
        for n in (0, -1, LONGUEUR_MIN - 1, LONGUEUR_MAX + 1, "16", 16.0, True):
            with self.assertRaises(ValueError, msg=f"devrait refuser : {n!r}"):
                generer(n)

    def test_refuse_si_aucun_type_choisi(self):
        with self.assertRaises(ValueError):
            generer(16, minuscules=False, majuscules=False, chiffres=False, symboles=False)

    def test_les_mots_de_passe_sont_differents(self):
        # 100 tirages de 16 caractères : une collision serait un signe de défaut grave
        self.assertEqual(len({generer(16) for _ in range(100)}), 100)


def lancer(args):
    """Appelle main() en capturant ce qu'il affiche."""
    sortie, erreur = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(sortie), contextlib.redirect_stderr(erreur):
        code = main(args)
    return code, sortie.getvalue(), erreur.getvalue()


class TestLigneDeCommande(unittest.TestCase):
    def test_commande_normale(self):
        code, sortie, erreur = lancer(["-l", "20", "-n", "3"])
        self.assertEqual(code, 0)
        lignes = sortie.splitlines()
        self.assertEqual(len(lignes), 3)
        self.assertTrue(all(len(ligne) == 20 for ligne in lignes))
        self.assertIn("Entropie", erreur)  # l'estimation va sur stderr, pas sur stdout
        self.assertNotIn("Entropie", sortie)

    def test_longueur_invalide_renvoie_2(self):
        code, sortie, erreur = lancer(["-l", "3"])
        self.assertEqual(code, 2)
        self.assertEqual(sortie, "")
        self.assertIn("Erreur", erreur)

    def test_aucun_type_renvoie_2(self):
        code, _, _ = lancer(["--sans-minuscules", "--sans-majuscules",
                             "--sans-chiffres", "--sans-symboles"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()