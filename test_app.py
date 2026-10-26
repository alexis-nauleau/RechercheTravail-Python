import os
import tempfile
import unittest

from app import create_app
from candidatures import ajouter, lister, separer_technologies


class BaseTest(unittest.TestCase):
    """Chaque test reçoit une application neuve, avec sa propre base jetable."""

    def setUp(self):
        # Un dossier temporaire, supprimé à la fin : la vraie base n'est jamais touchée
        self.dossier = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.app = create_app({
            "DATABASE": os.path.join(self.dossier.name, "test.db"),
            "TESTING": True,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.dossier.cleanup()


class TestModele(BaseTest):
    def test_ajouter_puis_lister(self):
        with self.app.app_context():
            identifiant = ajouter("Alpha SA", "Développeur", statut="postule",
                                  date_candidature="2026-10-20")
            lignes = lister()
        self.assertEqual(len(lignes), 1)
        self.assertEqual(lignes[0]["id"], identifiant)
        self.assertEqual(lignes[0]["entreprise"], "Alpha SA")
        self.assertEqual(lignes[0]["statut"], "postule")

    def test_refuse_entreprise_vide_ou_trop_longue(self):
        with self.app.app_context():
            with self.assertRaises(ValueError):
                ajouter("   ", "Développeur")
            with self.assertRaises(ValueError):
                ajouter("A" * 101, "Développeur")
            self.assertEqual(lister(), [])  # rien n'a été enregistré

    def test_refuse_statut_inconnu(self):
        with self.app.app_context():
            with self.assertRaises(ValueError):
                ajouter("Alpha SA", "Développeur", statut="inventé")

    def test_refuse_lien_dangereux(self):
        for lien in ("javascript:alert(1)", "ftp://example.com", "http://",
                     "//example.com", "example.com"):
            with self.app.app_context():
                with self.assertRaises(ValueError, msg=f"devrait refuser : {lien!r}"):
                    ajouter("Alpha SA", "Développeur", lien=lien)

    def test_refuse_date_invalide(self):
        for texte in ("2026-13-01", "2026-02-30", "2026-1-5", "20261026", "demain"):
            with self.app.app_context():
                with self.assertRaises(ValueError, msg=f"devrait refuser : {texte!r}"):
                    ajouter("Alpha SA", "Développeur", date_candidature=texte)

    def test_apostrophe_et_texte_piege_sont_stockes_tels_quels(self):
        piege = "'; DROP TABLE candidatures; --"
        with self.app.app_context():
            ajouter("L'Oréal", "Développeur")
            ajouter(piege, "Développeur")
            entreprises = {ligne["entreprise"] for ligne in lister()}
        # La requête paramétrée traite ces textes comme des DONNÉES : la table existe encore
        self.assertEqual(entreprises, {"L'Oréal", piege})

    # ---- Technologies ----

    def test_technologies_nettoyees(self):
        # Espaces en trop, vides, doublon (Python / python) : tout est normalisé
        with self.app.app_context():
            ajouter("Alpha SA", "Développeur", technologies="Python,  Flask , python, ,SQL")
            ligne = lister()[0]
        self.assertEqual(ligne["technologies"], "Python, Flask, SQL")

    def test_technologies_facultatives(self):
        with self.app.app_context():
            ajouter("Alpha SA", "Développeur")  # sans technologies
            ajouter("Beta SARL", "Développeur", technologies="  , ,  ")  # que des vides
            lignes = lister()
        self.assertEqual([ligne["technologies"] for ligne in lignes], [None, None])

    def test_accepte_dix_technologies_pas_onze(self):
        dix = ",".join(f"T{i}" for i in range(10))
        onze = ",".join(f"T{i}" for i in range(11))
        with self.app.app_context():
            ajouter("Alpha SA", "Développeur", technologies=dix)
            with self.assertRaises(ValueError):
                ajouter("Beta SARL", "Développeur", technologies=onze)
            self.assertEqual(len(lister()), 1)  # la 2e n'a pas été enregistrée

    def test_refuse_une_technologie_trop_longue(self):
        with self.app.app_context():
            ajouter("Alpha SA", "Développeur", technologies="a" * 30)  # limite : OK
            with self.assertRaises(ValueError):
                ajouter("Beta SARL", "Développeur", technologies="a" * 31)

    def test_refuse_technologies_qui_ne_sont_pas_un_texte(self):
        with self.app.app_context():
            with self.assertRaises(ValueError):
                ajouter("Alpha SA", "Développeur", technologies=["Python", "Flask"])

    def test_separer_technologies(self):
        self.assertEqual(separer_technologies("Python, Flask, SQL"),
                         ["Python", "Flask", "SQL"])
        self.assertEqual(separer_technologies(None), [])
        self.assertEqual(separer_technologies(""), [])


class TestPages(BaseTest):
    def test_accueil_vide(self):
        reponse = self.client.get("/")
        html = reponse.get_data(as_text=True)
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Dashboard", html)
        self.assertIn("Aucune candidature", html)

    def test_accueil_neutralise_le_html(self):
        with self.app.app_context():
            ajouter("<script>alert(1)</script>", "Développeur")
        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_lien_affiche_avec_rel(self):
        with self.app.app_context():
            ajouter("Gamma", "Développeur", lien="https://example.com/offre")
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('href="https://example.com/offre"', html)
        self.assertIn('rel="noopener noreferrer"', html)

    def test_filtre_par_statut(self):
        with self.app.app_context():
            ajouter("Alpha SA", "Développeur", statut="postule")
            ajouter("Beta SARL", "Développeur", statut="refus")
        html = self.client.get("/", query_string={"statut": "postule"}).get_data(as_text=True)
        self.assertIn("Alpha SA", html)
        self.assertNotIn("Beta SARL", html)

    def test_filtre_invalide_ignore(self):
        with self.app.app_context():
            ajouter("Alpha SA", "Développeur", statut="postule")
            ajouter("Beta SARL", "Développeur", statut="refus")
        reponse = self.client.get("/", query_string={"statut": "' OR 1=1 --"})
        html = reponse.get_data(as_text=True)
        self.assertEqual(reponse.status_code, 200)
        # Un statut inconnu est ignoré : on affiche tout, sans erreur
        self.assertIn("Alpha SA", html)
        self.assertIn("Beta SARL", html)

    def test_technologies_affichees_en_pastilles(self):
        with self.app.app_context():
            ajouter("Alpha SA", "Développeur", technologies="Python, Flask")
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('class="pastille">Python</span>', html)
        self.assertIn('class="pastille">Flask</span>', html)

    def test_technologies_neutralisent_le_html(self):
        with self.app.app_context():
            ajouter("Alpha SA", "Développeur", technologies="<script>alert(1)</script>")
        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()