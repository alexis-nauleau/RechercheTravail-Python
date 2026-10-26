import re
import unittest

from candidatures import lister
from test_app import BaseTest  # on réutilise la base jetable de test_app.py


class TestFormulaire(BaseTest):
    def _jeton(self):
        """Ouvre le formulaire comme le ferait un navigateur, et lit le jeton caché."""
        html = self.client.get("/nouvelle").get_data(as_text=True)
        trouve = re.search(r'name="csrf" value="([^"]+)"', html)
        self.assertIsNotNone(trouve, "le jeton devrait être dans la page")
        return trouve.group(1)

    def _envoyer(self, **champs):
        """Envoie le formulaire avec le bon jeton, puis les champs donnés."""
        donnees = {"csrf": self._jeton(), "entreprise": "Alpha SA", "poste": "Développeur"}
        donnees.update(champs)
        return self.client.post("/nouvelle", data=donnees)

    def test_la_page_du_formulaire_s_affiche(self):
        reponse = self.client.get("/nouvelle")
        html = reponse.get_data(as_text=True)
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Nouvelle candidature", html)
        self.assertIn('name="csrf"', html)

    def test_ajout_valide(self):
        reponse = self._envoyer(technologies="Python, Flask", statut="entretien")
        self.assertEqual(reponse.status_code, 303)  # redirigé vers l'accueil
        with self.app.app_context():
            lignes = lister()
        self.assertEqual(len(lignes), 1)
        self.assertEqual(lignes[0]["entreprise"], "Alpha SA")
        self.assertEqual(lignes[0]["technologies"], "Python, Flask")
        self.assertEqual(lignes[0]["statut"], "entretien")
        # Le message flash apparaît sur l'accueil
        accueil = self.client.get("/").get_data(as_text=True)
        self.assertIn("Candidature ajoutée.", accueil)

    def test_refuse_sans_jeton(self):
        self.client.get("/nouvelle")  # une session existe, mais on n'envoie pas de jeton
        reponse = self.client.post("/nouvelle", data={"entreprise": "Alpha SA", "poste": "Dev"})
        self.assertEqual(reponse.status_code, 400)
        with self.app.app_context():
            self.assertEqual(lister(), [])

    def test_refuse_un_mauvais_jeton(self):
        self.client.get("/nouvelle")
        reponse = self.client.post("/nouvelle", data={
            "csrf": "faux", "entreprise": "Alpha SA", "poste": "Dev"})
        self.assertEqual(reponse.status_code, 400)
        with self.app.app_context():
            self.assertEqual(lister(), [])

    def test_refuse_sans_session_meme_avec_un_jeton_vide(self):
        # Un site pirate n'a pas notre cookie de session : "" ne doit pas valoir "".
        reponse = self.client.post("/nouvelle", data={
            "csrf": "", "entreprise": "Alpha SA", "poste": "Dev"})
        self.assertEqual(reponse.status_code, 400)
        with self.app.app_context():
            self.assertEqual(lister(), [])

    def test_donnees_invalides_reaffichent_le_formulaire(self):
        reponse = self._envoyer(entreprise="   ", poste="Mon poste")
        html = reponse.get_data(as_text=True)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("obligatoire", html)       # le message d'erreur
        self.assertIn("Mon poste", html)         # ce qui avait été tapé est conservé
        with self.app.app_context():
            self.assertEqual(lister(), [])

    def test_lien_dangereux_refuse(self):
        reponse = self._envoyer(lien="javascript:alert(1)")
        self.assertEqual(reponse.status_code, 400)
        with self.app.app_context():
            self.assertEqual(lister(), [])

    def test_le_texte_reaffiche_est_neutralise(self):
        piege = '"><script>alert(1)</script>'
        reponse = self._envoyer(entreprise="", poste=piege)  # entreprise vide : erreur
        html = reponse.get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()