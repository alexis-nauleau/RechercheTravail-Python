import os
import socket
import unittest

from chemins import dossier_instance
from lancer import port_libre, trouver_port


class TestChemins(unittest.TestCase):
    def test_en_developpement_on_garde_le_dossier_par_defaut(self):
        self.assertIsNone(dossier_instance(frozen=False))

    def test_en_exe_on_utilise_le_profil_utilisateur(self):
        chemin = dossier_instance(frozen=True, environ={"LOCALAPPDATA": r"C:\Profil\Local"})
        self.assertEqual(chemin, os.path.join(r"C:\Profil\Local", "RechercheTravail"))

    def test_en_exe_sans_variable_on_retombe_sur_le_dossier_personnel(self):
        chemin = dossier_instance(frozen=True, environ={})
        self.assertTrue(chemin.startswith(os.path.expanduser("~")))
        self.assertTrue(chemin.endswith("RechercheTravail"))


class TestPort(unittest.TestCase):
    def test_un_port_occupe_est_detecte_et_on_en_prend_un_autre(self):
        # On occupe volontairement un port (0 : le système en choisit un libre)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupe:
            occupe.bind(("127.0.0.1", 0))
            occupe.listen()
            port = occupe.getsockname()[1]
            self.assertFalse(port_libre("127.0.0.1", port))
            self.assertGreater(trouver_port("127.0.0.1", port), port)

    def test_un_port_libre_est_renvoye_tel_quel(self):
        # On repère un port libre, on le libère, puis on vérifie qu'il est proposé
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as essai:
            essai.bind(("127.0.0.1", 0))
            port = essai.getsockname()[1]
        self.assertEqual(trouver_port("127.0.0.1", port), port)


if __name__ == "__main__":
    unittest.main()