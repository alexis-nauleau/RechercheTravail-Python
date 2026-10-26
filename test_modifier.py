import re
import unittest

from candidatures import ajouter, lister, modifier, obtenir, supprimer
from test_app import BaseTest  # la base jetable de test_app.py


class TestModeleModifierSupprimer(BaseTest):
    def test_modifier_change_les_champs(self):
        with self.app.app_context():
            identifiant = ajouter("Alpha SA", "Développeur", statut="postule")
            modifier(identifiant, "Alpha Groupe", "Lead dev", statut="entretien",
                     technologies="Python, Flask")
            ligne = obtenir(identifiant)
        self.assertEqual(ligne["entreprise"], "Alpha Groupe")
        self.assertEqual(ligne["poste"], "Lead dev")
        self.assertEqual(ligne["statut"], "entretien")
        self.assertEqual(ligne["technologies"], "Python, Flask")

    def test_modifier_applique_les_memes_regles_que_ajouter(self):
        with self.app.app_context():
            identifiant = ajouter("Alpha SA", "Développeur")
            with self.assertRaises(ValueError):
                modifier(identifiant, "Alpha SA", "Développeur", date_candidature="demain")
            with self.assertRaises(ValueError):
                modifier(identifiant, "   ", "Développeur")
            with self.assertRaises(ValueError):
                modifier(identifiant, "Alpha SA", "Développeur", lien="javascript:alert(1)")
            # Rien n'a été modifié par ces tentatives
            self.assertEqual(obtenir(identifiant)["entreprise"], "Alpha SA")
            self.assertIsNone(obtenir(identifiant)["date_candidature"])

    def test_modifier_une_candidature_inexistante(self):
        with self.app.app_context():
            with self.assertRaises(ValueError):
                modifier(999, "Alpha SA", "Développeur")

    def test_supprimer_retire_seulement_la_bonne_ligne(self):
        with self.app.app_context():
            a_supprimer = ajouter("Alpha SA", "Développeur")
            a_garder = ajouter("Beta SARL", "Développeur")
            self.assertTrue(supprimer(a_supprimer))
            self.assertIsNone(obtenir(a_supprimer))
            self.assertEqual([ligne["id"] for ligne in lister()], [a_garder])

    def test_supprimer_une_candidature_inexistante(self):
        with self.app.app_context():
            self.assertFalse(supprimer(999))


class TestPagesModifierSupprimer(BaseTest):
    def _ajouter(self, **champs):
        """Crée une candidature et renvoie son id."""
        champs.setdefault("entreprise", "Alpha SA")
        champs.setdefault("poste", "Développeur")
        with self.app.app_context():
            return ajouter(**champs)

    def _jeton(self, adresse):
        """Ouvre une page contenant un formulaire et lit son jeton caché."""
        html = self.client.get(adresse).get_data(as_text=True)
        trouve = re.search(r'name="csrf" value="([^"]+)"', html)
        self.assertIsNotNone(trouve, "le jeton devrait être dans la page")
        return trouve.group(1)

    def test_accueil_propose_modifier_et_supprimer(self):
        identifiant = self._ajouter()
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn(f"/candidature/{identifiant}/modifier", html)
        self.assertIn(f"/candidature/{identifiant}/supprimer", html)

    def test_le_formulaire_de_modification_est_prerempli(self):
        identifiant = self._ajouter(technologies="Python, Flask")
        html = self.client.get(f"/candidature/{identifiant}/modifier").get_data(as_text=True)
        self.assertIn('value="Alpha SA"', html)
        self.assertIn('value="Python, Flask"', html)

    def test_modification_par_le_formulaire(self):
        identifiant = self._ajouter()
        adresse = f"/candidature/{identifiant}/modifier"
        reponse = self.client.post(adresse, data={
            "csrf": self._jeton(adresse), "entreprise": "Alpha Groupe",
            "poste": "Lead dev", "statut": "entretien"})
        self.assertEqual(reponse.status_code, 303)
        with self.app.app_context():
            self.assertEqual(obtenir(identifiant)["entreprise"], "Alpha Groupe")
            self.assertEqual(obtenir(identifiant)["statut"], "entretien")
        self.assertIn("Candidature modifiée.", self.client.get("/").get_data(as_text=True))

    def test_modification_sans_jeton_refusee(self):
        identifiant = self._ajouter()
        adresse = f"/candidature/{identifiant}/modifier"
        self.client.get(adresse)  # une session existe, mais on n'envoie pas de jeton
        reponse = self.client.post(adresse, data={"entreprise": "Pirate", "poste": "X"})
        self.assertEqual(reponse.status_code, 400)
        with self.app.app_context():
            self.assertEqual(obtenir(identifiant)["entreprise"], "Alpha SA")

    def test_modification_invalide_ne_change_rien(self):
        identifiant = self._ajouter()
        adresse = f"/candidature/{identifiant}/modifier"
        reponse = self.client.post(adresse, data={
            "csrf": self._jeton(adresse), "entreprise": "", "poste": "Nouveau poste"})
        html = reponse.get_data(as_text=True)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("obligatoire", html)
        self.assertIn("Nouveau poste", html)  # ce qui a été tapé est conservé
        with self.app.app_context():
            self.assertEqual(obtenir(identifiant)["poste"], "Développeur")  # base intacte

    def test_modifier_une_page_inexistante(self):
        self.assertEqual(self.client.get("/candidature/999/modifier").status_code, 404)

    def test_suppression_demande_confirmation_sans_supprimer(self):
        identifiant = self._ajouter()
        reponse = self.client.get(f"/candidature/{identifiant}/supprimer")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Alpha SA", reponse.get_data(as_text=True))
        with self.app.app_context():
            self.assertIsNotNone(obtenir(identifiant))  # un GET ne supprime rien

    def test_suppression_par_le_formulaire(self):
        identifiant = self._ajouter()
        adresse = f"/candidature/{identifiant}/supprimer"
        reponse = self.client.post(adresse, data={"csrf": self._jeton(adresse)})
        self.assertEqual(reponse.status_code, 303)
        with self.app.app_context():
            self.assertIsNone(obtenir(identifiant))
        self.assertIn("Candidature supprimée.", self.client.get("/").get_data(as_text=True))

    def test_suppression_sans_jeton_refusee(self):
        identifiant = self._ajouter()
        adresse = f"/candidature/{identifiant}/supprimer"
        self.client.get(adresse)
        self.assertEqual(self.client.post(adresse, data={}).status_code, 400)
        self.assertEqual(self.client.post(adresse, data={"csrf": "faux"}).status_code, 400)
        with self.app.app_context():
            self.assertIsNotNone(obtenir(identifiant))

    def test_supprimer_une_page_inexistante(self):
        self.assertEqual(self.client.get("/candidature/999/supprimer").status_code, 404)
        jeton = self._jeton("/nouvelle")
        reponse = self.client.post("/candidature/999/supprimer", data={"csrf": jeton})
        self.assertEqual(reponse.status_code, 404)

    def test_confirmation_neutralise_le_html(self):
        identifiant = self._ajouter(entreprise="<script>alert(1)</script>")
        html = self.client.get(f"/candidature/{identifiant}/supprimer").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()