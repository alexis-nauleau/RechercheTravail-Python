"""Lance l'application comme un programme : serveur local, puis ouverture du navigateur.

C'est ce fichier que PyInstaller transforme en .exe. Fermer la fenêtre noire arrête
le programme.
"""
import socket
import threading
import webbrowser

from app import create_app

HOTE = "127.0.0.1"  # le serveur n'écoute que sur ton PC, jamais depuis le réseau
PORT_DEPART = 5000


def port_libre(hote, port):
    """Dit si personne n'utilise déjà ce port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as essai:
        try:
            essai.bind((hote, port))
        except OSError:  # le port est déjà pris
            return False
    return True


def trouver_port(hote, depart, essais=20):
    """Renvoie le premier port libre à partir de "depart" (5000, puis 5001...)."""
    for port in range(depart, depart + essais):
        if port_libre(hote, port):
            return port
    raise RuntimeError("Aucun port libre trouvé.")


def main():
    app = create_app()
    port = trouver_port(HOTE, PORT_DEPART)
    adresse = f"http://{HOTE}:{port}"
    print(f"Application disponible sur {adresse}  (ferme cette fenêtre pour quitter)")
    # Après 1 seconde (le temps que le serveur démarre), on ouvre le navigateur.
    threading.Timer(1.0, webbrowser.open, args=(adresse,)).start()
    # debug=False : le mode debug n'a rien à faire dans un programme distribué.
    # use_reloader=False : sans ça, le serveur se relancerait en doublon.
    app.run(host=HOTE, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()