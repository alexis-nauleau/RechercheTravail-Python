"""Où ranger les données de l'application (la base, la clé secrète)."""
import os
import sys

NOM_APPLICATION = "RechercheTravail"


def dossier_instance(frozen=None, environ=None):
    """Renvoie le dossier des données, ou None pour garder le choix par défaut de Flask.

    "frozen" signifie "tourne comme un .exe fabriqué par PyInstaller". Dans ce cas, le
    dossier du programme est temporaire : on range les données dans le profil de
    l'utilisateur, qui, lui, est conservé. Les deux paramètres existent pour pouvoir
    tester cette fonction sans fabriquer d'exe.
    """
    if frozen is None:
        # PyInstaller ajoute l'attribut "frozen" à sys quand on tourne en .exe
        frozen = getattr(sys, "frozen", False)
    if not frozen:
        return None  # en développement : le dossier "instance" habituel
    if environ is None:
        environ = os.environ
    # LOCALAPPDATA : par exemple C:\Users\TonNom\AppData\Local
    base = environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(base, NOM_APPLICATION)