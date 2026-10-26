import unittest

from coffre import (LONGUEUR_MIN_MAITRE, TAILLE_SEL, ErreurCoffre, chiffrer, cle_valide,
                    creer_temoin, dechiffrer, deriver_cle, nouveau_sel,
                    valider_mot_de_passe_maitre)

MAITRE = "phrase-de-passe-de-test-longue"


class TestMotDePasseMaitre(unittest.TestCase):
    def test_refuse_trop_court_ou_mauvais_type(self):
        # "" (vide), un mot court, un texte à un caractère de la longueur minimale,
        # None, et un nombre : aucun n'est un mot de passe maître valable
        for valeur in ("", "court", "a" * (LONGUEUR_MIN_MAITRE - 1), None, 123456789012):
            with self.assertRaises(ValueError, msg=f"devrait refuser : {valeur!r}"):
                valider_mot_de_passe_maitre(valeur)

    def test_accepte_la_longueur_minimale(self):
        valider_mot_de_passe_maitre("a" * LONGUEUR_MIN_MAITRE)  # ne doit pas lever d'erreur


class TestCle(unittest.TestCase):
    def test_sel_a_la_bonne_taille_et_different_a_chaque_fois(self):
        # Les accolades { ... for ... } fabriquent un "set" : chaque valeur n'y existe
        # qu'une fois. 50 sels tous différents donnent donc un ensemble de 50.
        sels = {nouveau_sel() for _ in range(50)}
        self.assertEqual(len(sels), 50)
        self.assertTrue(all(len(s) == TAILLE_SEL for s in sels))

    def test_meme_mot_de_passe_et_meme_sel_donnent_la_meme_cle(self):
        sel = nouveau_sel()
        self.assertEqual(deriver_cle(MAITRE, sel), deriver_cle(MAITRE, sel))

    def test_un_autre_sel_ou_un_autre_mot_de_passe_change_la_cle(self):
        sel = nouveau_sel()
        self.assertNotEqual(deriver_cle(MAITRE, sel), deriver_cle(MAITRE, nouveau_sel()))
        self.assertNotEqual(deriver_cle(MAITRE, sel), deriver_cle(MAITRE + "x", sel))

    def test_refuse_des_parametres_invalides(self):
        with self.assertRaises(ValueError):
            deriver_cle(MAITRE, b"trop-court")
        with self.assertRaises(ValueError):
            deriver_cle(MAITRE, "pas des octets")
        with self.assertRaises(ValueError):
            deriver_cle(None, nouveau_sel())


class TestChiffrement(unittest.TestCase):
    # @classmethod : cette méthode appartient à la CLASSE, pas à un test. unittest
    # l'appelle UNE SEULE FOIS avant tous les tests du groupe. "cls" désigne la classe.
    # scrypt est volontairement lent : on calcule les clés une fois, pas à chaque test.
    @classmethod
    def setUpClass(cls):
        cls.sel = nouveau_sel()
        cls.cle = deriver_cle(MAITRE, cls.sel)
        cls.autre_cle = deriver_cle("une-autre-phrase-de-passe", cls.sel)

    def test_aller_retour_avec_accents_et_symboles(self):
        for texte in ("motdepasse", "É!@#é ü 日本語 €", "", "x" * 5000):
            self.assertEqual(dechiffrer(self.cle, chiffrer(self.cle, texte)), texte)

    def test_le_jeton_ne_contient_pas_le_texte_en_clair(self):
        jeton = chiffrer(self.cle, "mon-mot-de-passe-secret")
        self.assertNotIn("mon-mot-de-passe-secret", jeton)

    def test_deux_chiffrements_du_meme_texte_different(self):
        self.assertNotEqual(chiffrer(self.cle, "abc"), chiffrer(self.cle, "abc"))

    def test_une_mauvaise_cle_est_refusee(self):
        jeton = chiffrer(self.cle, "secret")
        with self.assertRaises(ErreurCoffre):
            dechiffrer(self.autre_cle, jeton)

    def test_un_jeton_modifie_est_refuse(self):
        jeton = chiffrer(self.cle, "secret")
        milieu = len(jeton) // 2
        # On remplace un caractère du milieu par "A" (ou par "B" s'il était déjà "A")
        altere = jeton[:milieu] + ("A" if jeton[milieu] != "A" else "B") + jeton[milieu + 1:]
        with self.assertRaises(ErreurCoffre):
            dechiffrer(self.cle, altere)

    def test_un_jeton_absurde_est_refuse(self):
        for jeton in ("", "pas-un-jeton", "@@@@"):
            with self.assertRaises(ErreurCoffre, msg=f"devrait refuser : {jeton!r}"):
                dechiffrer(self.cle, jeton)

    def test_refuse_de_chiffrer_autre_chose_qu_un_texte(self):
        with self.assertRaises(ValueError):
            chiffrer(self.cle, 12345)


class TestTemoin(unittest.TestCase):
    def test_le_bon_mot_de_passe_ouvre_le_coffre_pas_un_autre(self):
        sel = nouveau_sel()
        temoin = creer_temoin(deriver_cle(MAITRE, sel))
        self.assertTrue(cle_valide(deriver_cle(MAITRE, sel), temoin))
        self.assertFalse(cle_valide(deriver_cle(MAITRE + "!", sel), temoin))


if __name__ == "__main__":
    unittest.main()