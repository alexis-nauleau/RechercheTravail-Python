import re
import unittest

import sites
from test_app import BaseTest  # la base jetable de test_app.py


class TestModeleSites(BaseTest):
    def test_ajouter_puis_lister_classe_sans_tenir_compte_des_majuscules(self):
        with self.app.app_context():
            sites.ajouter("indeed")
            sites.ajouter("LinkedIn")
            sites.ajouter("HelloWork")
            noms = [ligne["nom"] for ligne in sites.lister()]
        self.assertEqual(noms, ["HelloWork", "indeed", "LinkedIn"])

    def test_nom_obligatoire_et_limite(self):
        with self.app.app_context():
            with self.assertRaises(ValueError):
                sites.ajouter("   ")
            with self.assertRaises(ValueError):
                sites.ajouter("A" * 101)
            sites.ajouter("A" * 100)  # la limite elle-même est acceptée
            self.assertEqual(len(sites.lister()), 1)

    def test_refuse_un_lien_dangereux(self):
        with self.app.app_context():
            for lien in ("javascript:alert(1)", "ftp://example.com", "example.com"):
                with self.assertRaises(ValueError, msg=f"devrait refuser : {lien!r}"):
                    sites.ajouter("Indeed", lien=lien)
            self.assertEqual(sites.lister(), [])

    def test_le_mot_de_passe_est_conserve_a_l_identique(self):
        # Pas de nettoyage : espaces, apostrophes, guillemets et symboles font partie du mot de passe
        mot_de_passe = ' a b\'"<>& '
        with self.app.app_context():
            identifiant = sites.ajouter("Indeed", mot_de_passe=mot_de_passe)
            self.assertEqual(sites.obtenir(identifiant)["mot_de_passe"], mot_de_passe)

    def test_les_champs_facultatifs_vides_deviennent_rien(self):
        with self.app.app_context():
            identifiant = sites.ajouter("Indeed", lien="  ", utilisateur="  ", mot_de_passe="")
            ligne = sites.obtenir(identifiant)
        self.assertIsNone(ligne["lien"])
        self.assertIsNone(ligne["utilisateur"])
        self.assertIsNone(ligne["mot_de_passe"])

    def test_refuse_un_mot_de_passe_trop_long_ou_pas_un_texte(self):
        with self.app.app_context():
            sites.ajouter("Indeed", mot_de_passe="a" * 200)  # limite : OK
            with self.assertRaises(ValueError):
                sites.ajouter("LinkedIn", mot_de_passe="a" * 201)
            with self.assertRaises(ValueError):
                sites.ajouter("LinkedIn", mot_de_passe=12345)

    def test_modifier(self):
        with self.app.app_context():
            identifiant = sites.ajouter("Indeed", utilisateur="ancien")
            sites.modifier(identifiant, "Indeed France", utilisateur="nouveau",
                           mot_de_passe="demo-1")
            ligne = sites.obtenir(identifiant)
        self.assertEqual(ligne["nom"], "Indeed France")
        self.assertEqual(ligne["utilisateur"], "nouveau")
        self.assertEqual(ligne["mot_de_passe"], "demo-1")

    def test_modifier_un_site_inexistant_ou_invalide(self):
        with self.app.app_context():
            identifiant = sites.ajouter("Indeed")
            with self.assertRaises(ValueError):
                sites.modifier(999, "Indeed")
            with self.assertRaises(ValueError):
                sites.modifier(identifiant, "   ")
            self.assertEqual(sites.obtenir(identifiant)["nom"], "Indeed")  # inchangé

    def test_supprimer_retire_seulement_le_bon_site(self):
        with self.app.app_context():
            a_supprimer = sites.ajouter("Indeed")
            a_garder = sites.ajouter("LinkedIn")
            self.assertTrue(sites.supprimer(a_supprimer))
            self.assertEqual([ligne["id"] for ligne in sites.lister()], [a_garder])

    def test_supprimer_un_site_inexistant(self):
        with self.app.app_context():
            self.assertFalse(sites.supprimer(999))


class TestPagesSites(BaseTest):
    def _ajouter(self, nom="Indeed", **champs):
        with self.app.app_context():
            return sites.ajouter(nom, **champs)

    def _jeton(self, adresse):
        """Ouvre une page contenant un formulaire et lit son jeton caché."""
        html = self.client.get(adresse).get_data(as_text=True)
        trouve = re.search(r'name="csrf" value="([^"]+)"', html)
        self.assertIsNotNone(trouve, "le jeton devrait être dans la page")
        return trouve.group(1)

    def test_liste_vide(self):
        reponse = self.client.get("/recherche")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Aucun site enregistré", reponse.get_data(as_text=True))

    def test_le_mot_de_passe_est_masque_et_n_apparait_qu_une_fois(self):
        self._ajouter(utilisateur="demo", mot_de_passe="Secret-Demo-123")
        html = self.client.get("/recherche").get_data(as_text=True)
        self.assertIn('type="password"', html)   # le champ est masqué
        self.assertEqual(html.count("Secret-Demo-123"), 1)  # jamais écrit en clair ailleurs

    def test_la_liste_neutralise_le_html(self):
        self._ajouter(nom="<script>alert(1)</script>", utilisateur="<b>x</b>")
        html = self.client.get("/recherche").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn("<b>x</b>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_ajout_par_le_formulaire(self):
        jeton = self._jeton("/recherche/nouveau")
        reponse = self.client.post("/recherche/nouveau", data={
            "csrf": jeton, "nom": "Indeed", "lien": "https://fr.indeed.com",
            "utilisateur": "demo", "mot_de_passe": "demo-1"})
        self.assertEqual(reponse.status_code, 303)
        with self.app.app_context():
            ligne = sites.lister()[0]
        self.assertEqual(ligne["nom"], "Indeed")
        self.assertEqual(ligne["mot_de_passe"], "demo-1")
        self.assertIn("Site ajouté.", self.client.get("/recherche").get_data(as_text=True))

    def test_ajout_sans_jeton_refuse(self):
        self.client.get("/recherche/nouveau")  # une session existe, mais pas de jeton envoyé
        reponse = self.client.post("/recherche/nouveau", data={"nom": "Indeed"})
        self.assertEqual(reponse.status_code, 400)
        with self.app.app_context():
            self.assertEqual(sites.lister(), [])

    def test_ajout_invalide_reaffiche_le_formulaire(self):
        jeton = self._jeton("/recherche/nouveau")
        reponse = self.client.post("/recherche/nouveau", data={
            "csrf": jeton, "nom": "", "utilisateur": "demo"})
        html = reponse.get_data(as_text=True)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("obligatoire", html)
        self.assertIn('value="demo"', html)  # ce qui a été tapé est conservé
        with self.app.app_context():
            self.assertEqual(sites.lister(), [])

    def test_le_formulaire_de_modification_est_prerempli(self):
        identifiant = self._ajouter(utilisateur="demo", mot_de_passe="demo-1")
        html = self.client.get(f"/recherche/{identifiant}/modifier").get_data(as_text=True)
        self.assertIn('value="Indeed"', html)
        self.assertIn('value="demo"', html)
        self.assertIn('value="demo-1"', html)

    def test_modification_par_le_formulaire(self):
        identifiant = self._ajouter()
        adresse = f"/recherche/{identifiant}/modifier"
        reponse = self.client.post(adresse, data={
            "csrf": self._jeton(adresse), "nom": "Indeed France", "utilisateur": "nouveau"})
        self.assertEqual(reponse.status_code, 303)
        with self.app.app_context():
            self.assertEqual(sites.obtenir(identifiant)["nom"], "Indeed France")
        self.assertIn("Site modifié.", self.client.get("/recherche").get_data(as_text=True))

    def test_suppression_demande_confirmation_sans_supprimer(self):
        identifiant = self._ajouter()
        reponse = self.client.get(f"/recherche/{identifiant}/supprimer")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Indeed", reponse.get_data(as_text=True))
        with self.app.app_context():
            self.assertIsNotNone(sites.obtenir(identifiant))  # un GET ne supprime rien

    def test_suppression_par_le_formulaire(self):
        identifiant = self._ajouter()
        adresse = f"/recherche/{identifiant}/supprimer"
        reponse = self.client.post(adresse, data={"csrf": self._jeton(adresse)})
        self.assertEqual(reponse.status_code, 303)
        with self.app.app_context():
            self.assertIsNone(sites.obtenir(identifiant))
        self.assertIn("Site supprimé.", self.client.get("/recherche").get_data(as_text=True))

    def test_suppression_sans_jeton_refusee(self):
        identifiant = self._ajouter()
        adresse = f"/recherche/{identifiant}/supprimer"
        self.client.get(adresse)
        self.assertEqual(self.client.post(adresse, data={}).status_code, 400)
        self.assertEqual(self.client.post(adresse, data={"csrf": "faux"}).status_code, 400)
        with self.app.app_context():
            self.assertIsNotNone(sites.obtenir(identifiant))

    def test_pages_inexistantes(self):
        self.assertEqual(self.client.get("/recherche/999/modifier").status_code, 404)
        self.assertEqual(self.client.get("/recherche/999/supprimer").status_code, 404)

    def test_l_accueil_propose_le_lien_vers_la_recherche(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('href="/recherche"', html)


if __name__ == "__main__":
    unittest.main()