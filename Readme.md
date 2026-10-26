# Recherche d'emploi — tableau de bord local en Python

Application web **locale** (Flask + SQLite) pour suivre ses candidatures et garder la liste des sites de recherche d'emploi (Indeed, LinkedIn, HelloWork…). 

Ce projet est aussi un **projet d'apprentissage de Python** : le code est abondamment commenté en français, chaque fonctionnalité est couverte par des tests, et le travail a été découpé en branches Git comme dans un projet professionnel.

> ⚠️ **Mode démo.** La section « Sites de recherche » range les mots de passe **en clair** dans la base. N'y enregistrer que de faux identifiants. Voir [Sécurité](#sécurité) pour le détail et les limites.

---

## Sommaire

1. [Fonctionnalités](#fonctionnalités)
2. [Prérequis](#prérequis)
3. [Installation pas à pas](#installation-pas-à-pas)
4. [Lancer l'application](#lancer-lapplication)
5. [Utilisation](#utilisation)
6. [Lancer les tests](#lancer-les-tests)
7. [Structure du projet](#structure-du-projet)
8. [Comment ça fonctionne](#comment-ça-fonctionne)
9. [Sécurité](#sécurité)
10. [Fabriquer un .exe (Windows)](#fabriquer-un-exe-windows)
11. [Le générateur de mots de passe](#le-générateur-de-mots-de-passe)
12. [Workflow Git](#workflow-git)
13. [Dépannage](#dépannage)
14. [Limites et pistes d'amélioration](#limites-et-pistes-damélioration)

---

## Fonctionnalités

**Candidatures**

- Ajouter, modifier et supprimer une candidature (entreprise, poste, technologies demandées, lien de l'offre, statut, date, notes).
- Cinq statuts : *À postuler*, *Postulé*, *Entretien*, *Offre reçue*, *Refus*, avec un filtre par statut.
- Technologies affichées sous forme de pastilles, nettoyées automatiquement (espaces, doublons, 10 au maximum).
- Tri par date de candidature, les plus récentes d'abord.

**Sites de recherche**

- Liste de sites (nom, adresse, utilisateur, mot de passe) avec ajout, modification et suppression.
- Le mot de passe est masqué ; il s'affiche uniquement quand on clique dans le champ, et il est alors sélectionné pour être copié (`Ctrl+C`).

**Sur toutes les pages d'écriture**

- Protection contre le CSRF (jeton secret dans chaque formulaire).
- Confirmation avant toute suppression (une page dédiée, pas de suppression par simple lien).
- Messages de confirmation (« Candidature ajoutée. ») et messages d'erreur clairs ; ce qui a été saisi est conservé en cas d'erreur.

**Autour de l'application**

- Un générateur de mots de passe en ligne de commande (`generateur.py`).
- Un module de chiffrement (`coffre.py`, scrypt + Fernet), testé mais **pas encore branché** dans l'application.
- Un lanceur pour fabriquer un `.exe` Windows avec PyInstaller.

---

## Prérequis

| Outil | Version | Remarque |
|---|---|---|
| Python | 3.15 (version de développement) | Le code n'utilise rien de très récent ; une version 3.10 ou plus récente devrait suffire, mais seule la 3.15 a été testée. |
| Git | récent | Pour cloner le dépôt. |
| Un navigateur | n'importe lequel | Pour afficher l'application. |

Les commandes ci-dessous sont écrites pour **PowerShell sous Windows**. Les équivalents macOS / Linux sont indiqués quand ils diffèrent.

Vérifier les versions installées :

```powershell
python --version
git --version
```

---

## Installation pas à pas

### 1. Récupérer le code

```powershell
git clone https://github.com/alexis-nauleau/RechercheTravail-Python.git
cd RechercheTravail-Python
```

Les branches : `main` (version stable), `dev` (développement en cours). Par défaut, `git clone` se place sur `main`.

### 2. Créer un environnement virtuel

Un environnement virtuel isole les bibliothèques du projet de celles du reste de l'ordinateur.

```powershell
python -m venv .venv
```

Cela crée le dossier `.venv` (ignoré par Git).

### 3. Activer l'environnement

```powershell
.venv\Scripts\Activate.ps1
```

*macOS / Linux :* `source .venv/bin/activate`

Le terminal affiche alors `(.venv)` au début de la ligne. À refaire à chaque nouveau terminal (VS Code le fait automatiquement s'il a détecté l'environnement).

Si PowerShell refuse d'exécuter le script (« l'exécution de scripts est désactivée »), autoriser les scripts **pour cette session seulement** :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
```

### 4. Installer les dépendances

```powershell
pip install -r requirements.txt
```

Principales dépendances : **Flask** (le serveur web) et **cryptography** (utilisée par `coffre.py`). Le fichier épingle les versions exactes qui ont servi au développement.

### 5. (Facultatif) Ajouter des données fictives

```powershell
python -m flask --app app seed
```

Cette commande ajoute quelques candidatures et quatre sites **fictifs**. Elle remplit chaque section **seulement si celle-ci est vide** : relancer la commande ne crée pas de doublons.

---

## Lancer l'application

```powershell
python app.py
```

Puis ouvrir <http://127.0.0.1:5000> dans le navigateur. Arrêter le serveur avec `Ctrl+C`.

- Le serveur n'écoute que sur `127.0.0.1` : il n'est **pas** accessible depuis le réseau.
- `python app.py` démarre en mode *debug* (rechargement automatique à chaque modification de fichier). Ce mode ne doit jamais être activé sur un serveur accessible depuis Internet.
- La base de données est créée automatiquement dans le dossier `instance/` au premier lancement.

---

## Utilisation

### Les pages

| Adresse | Méthode | Rôle |
|---|---|---|
| `/` | GET | Liste des candidatures. `/?statut=postule` filtre par statut. |
| `/nouvelle` | GET, POST | Formulaire d'ajout d'une candidature. |
| `/candidature/<id>/modifier` | GET, POST | Modifier une candidature (formulaire prérempli). |
| `/candidature/<id>/supprimer` | GET, POST | GET : demande de confirmation. POST : suppression. |
| `/recherche` | GET | Liste des sites de recherche. |
| `/recherche/nouveau` | GET, POST | Ajouter un site. |
| `/recherche/<id>/modifier` | GET, POST | Modifier un site. |
| `/recherche/<id>/supprimer` | GET, POST | Confirmation puis suppression d'un site. |

### Règles de saisie

Toute saisie est vérifiée côté serveur (les attributs `required` et `maxlength` du navigateur ne servent qu'au confort).

**Candidature**

| Champ | Règle |
|---|---|
| Entreprise | Obligatoire, 100 caractères maximum. |
| Poste | Obligatoire, 150 caractères maximum. |
| Technologies | Facultatif. Séparées par des virgules, 10 au maximum, 30 caractères chacune, doublons supprimés sans tenir compte des majuscules (500 caractères au total). |
| Lien | Facultatif. Doit commencer par `http://` ou `https://` (500 caractères). |
| Statut | L'un des cinq statuts. |
| Date | Facultative. Format `AAAA-MM-JJ`, date qui existe réellement. |
| Notes | Facultatif, 2000 caractères maximum. |

**Site de recherche**

| Champ | Règle |
|---|---|
| Nom | Obligatoire, 100 caractères maximum. |
| Adresse | Facultative, `http://` ou `https://` uniquement. |
| Utilisateur | Facultatif, 150 caractères maximum. |
| Mot de passe | Facultatif, 200 caractères maximum, enregistré **tel quel** (les espaces comptent). |

---

## Lancer les tests

Les tests utilisent le module `unittest`, fourni avec Python. Chaque test reçoit une base de données **temporaire** : la vraie base n'est jamais touchée.

```powershell
python -m unittest -v
```

Résultat attendu : une ligne `OK` à la fin. Pour lancer un seul fichier ou un seul test :

```powershell
python -m unittest test_sites -v
python -m unittest test_app.TestModele.test_ajouter_puis_lister -v
```

| Fichier de test | Ce qu'il vérifie |
|---|---|
| `test_generateur.py` | Le générateur de mots de passe : longueur, types de caractères, options, codes de retour. |
| `test_coffre.py` | Dérivation de clé, chiffrement / déchiffrement, rejet des jetons modifiés, vérification du mot de passe maître. |
| `test_app.py` | Validation et accès aux candidatures, pages d'accueil, filtre, neutralisation du HTML, technologies. |
| `test_formulaire.py` | Formulaire d'ajout : jeton CSRF, erreurs de saisie, conservation de la saisie. |
| `test_modifier.py` | Modification et suppression des candidatures, page de confirmation, erreurs 404. |
| `test_sites.py` | Section « Sites de recherche » : validation, tri, mots de passe masqués, CSRF, modification, suppression. |
| `test_exe.py` | Dossier de données du `.exe` et recherche d'un port libre. |

Cas de sécurité testés explicitement : injection SQL (`'; DROP TABLE …`), injection HTML (`<script>`), lien `javascript:`, requête sans jeton CSRF, jeton vide sans session.

---

## Structure du projet

```text
.
├── app.py               Application Flask : routes, protection CSRF, commande « seed »
├── db.py                Connexion SQLite, schéma des tables, liste des statuts
├── candidatures.py      Validation et accès à la base pour les candidatures
├── sites.py             Validation et accès à la base pour les sites de recherche
├── chemins.py           Où ranger les données (dossier instance, ou profil utilisateur en .exe)
├── lancer.py            Lanceur : serveur local + ouverture du navigateur (cible du .exe)
├── generateur.py        Générateur de mots de passe (ligne de commande)
├── coffre.py            Chiffrement scrypt + Fernet (testé, non branché à l'application)
├── templates/
│   ├── index.html           Liste des candidatures
│   ├── formulaire.html      Formulaire des candidatures
│   ├── recherche.html       Liste des sites de recherche
│   ├── site_formulaire.html Formulaire des sites
│   └── supprimer.html       Page de confirmation de suppression (commune)
├── test_*.py            Tests (un fichier par sujet)
├── requirements.txt     Dépendances épinglées
├── .gitignore           Fichiers exclus de Git
└── instance/            (créé au lancement, ignoré par Git) base de données et clé secrète
```

---

## Comment ça fonctionne

### Les couches

```text
Navigateur ──► app.py (routes) ──► candidatures.py / sites.py ──► db.py ──► SQLite
                   │                    (validation + SQL)
                   └──► templates/*.html (affichage)
```

- **`app.py`** reçoit les requêtes, vérifie le jeton CSRF, appelle la couche de données et choisit la page à afficher. Il ne contient aucun SQL.
- **`candidatures.py` et `sites.py`** valident chaque champ **avant** d'écrire en base, puis exécutent le SQL. Les règles de validation sont écrites une seule fois (`_valider`) et servent à l'ajout comme à la modification.
- **`db.py`** ouvre la connexion (une par requête, fermée automatiquement) et décrit les tables.
- **Les gabarits** (`templates/`) utilisent Jinja, qui neutralise automatiquement le HTML.

### La base de données

SQLite : un simple fichier (`instance/candidatures.db`), sans serveur à installer. Deux tables, créées automatiquement (`CREATE TABLE IF NOT EXISTS`).

`candidatures` : `id`, `entreprise`, `poste`, `technologies`, `lien`, `statut` (contrainte `CHECK` : la base refuse un statut inconnu), `date_candidature`, `notes`, `cree_le`.

`sites` : `id`, `nom`, `lien`, `utilisateur`, `mot_de_passe`, `cree_le`.

> `CREATE TABLE IF NOT EXISTS` ne **modifie pas** une table qui existe déjà. Si le schéma change (nouvelle colonne), supprimer `instance/candidatures.db` (en développement, avec des données fictives) pour qu'il soit recréé.

### Le cycle d'un formulaire

1. `GET /nouvelle` : la page s'affiche avec un jeton CSRF caché, rangé aussi dans la session (cookie signé).
2. `POST /nouvelle` : le serveur compare le jeton reçu à celui de la session. Différent ou absent : erreur 400, rien n'est lu.
3. Les champs sont validés. En cas d'erreur, le formulaire se réaffiche (code 400) avec le message et la saisie.
4. En cas de succès, la ligne est enregistrée, un message « flash » est préparé, et le navigateur est redirigé (code 303) vers la liste. Actualiser la page ne renvoie donc pas le formulaire.

---

## Sécurité

Ce qui est en place :

| Risque | Parade |
|---|---|
| Injection SQL | Requêtes paramétrées (`?` et `:nom`) : aucune valeur saisie n'est collée dans le texte SQL. Les rares f-strings SQL n'assemblent que des constantes du code. |
| Injection HTML / XSS | Neutralisation automatique par Jinja (`{{ … }}`) ; aucun `\|safe` dans les gabarits. Testé avec `<script>`. |
| Liens dangereux (`javascript:`) | Seules les adresses `http://` et `https://` sont acceptées, à l'enregistrement **et** à l'affichage. Les liens externes portent `rel="noopener noreferrer"`. |
| CSRF (un autre site qui enverrait un formulaire vers `127.0.0.1:5000`) | Jeton secret par session, comparé en temps constant ; cookie de session en `SameSite=Lax`. |
| Suppression accidentelle | Page de confirmation, puis suppression par POST uniquement. |
| Données énormes | Longueurs maximales vérifiées côté serveur. |
| Clé secrète dans Git | Elle est générée dans `instance/secret_key`, dossier exclu par `.gitignore`. |

Ce qui **n'est pas** protégé, volontairement ou non :

- **Pas de connexion.** Toute personne qui peut ouvrir `127.0.0.1:5000` sur l'ordinateur voit et modifie les données.
- **Les mots de passe des sites sont en clair** dans la base SQLite, et présents dans le HTML de la page (visibles par « afficher le code source »). Les masquer à l'écran évite seulement qu'on les lise par-dessus l'épaule. **Ne jamais y enregistrer un vrai mot de passe.**
- `coffre.py` (scrypt + Fernet) permettrait de les chiffrer ; il n'est pas encore branché, car cela suppose un mot de passe maître, une session et une gestion de la clé en mémoire.

---

## Fabriquer un .exe (Windows)

Permet de lancer l'application par un double-clic, sans installer Python. L'exécutable démarre le serveur local, puis ouvre le navigateur.

### Particularités

- En `.exe`, le dossier du programme est **temporaire**. Les données sont donc rangées dans `%LOCALAPPDATA%\RechercheTravail` (voir `chemins.py`), et non dans `instance/`. Les données de `python app.py` et celles de l'exe sont **deux bases distinctes**.
- Si le port 5000 est occupé, le lanceur prend le suivant (5001…).
- La fenêtre noire qui reste ouverte est normale : la fermer arrête l'application.

### Construction

PyInstaller est un outil de fabrication, pas une dépendance de l'application : il n'est pas dans `requirements.txt`.

```powershell
pip install pyinstaller
pyinstaller --onefile --name RechercheTravail --add-data "templates;templates" lancer.py
```

Le résultat est `dist\RechercheTravail.exe`. Les dossiers `build/`, `dist/` et le fichier `.spec` sont ignorés par Git.

### Remarques

- Windows SmartScreen peut afficher « Windows a protégé votre ordinateur » : l'exécutable n'est pas signé. Cliquer sur « Informations complémentaires » puis « Exécuter quand même ». Certains antivirus signalent à tort les exécutables PyInstaller.
- Le résultat ne fonctionne que sous Windows, avec la même architecture que la machine de construction.
- Pour reprendre des données de développement dans l'exe :

  ```powershell
  mkdir $env:LOCALAPPDATA\RechercheTravail -Force
  copy instance\candidatures.db $env:LOCALAPPDATA\RechercheTravail\
  ```

---

## Le générateur de mots de passe

`generateur.py` génère des mots de passe aléatoires avec le module `secrets` de Python (conçu pour la sécurité, contrairement à `random`). Il garantit au moins un caractère de chaque type choisi.

```powershell
python generateur.py                         # un mot de passe de 16 caractères
python generateur.py -l 24                   # 24 caractères
python generateur.py -l 24 -n 3              # trois mots de passe
python generateur.py --sans-symboles         # pour les sites qui refusent certains symboles
python generateur.py --sans-ambigus          # écarte les caractères qu'on confond (I l 1 O 0 o)
python generateur.py --help                  # toutes les options
```

Options de type : `--sans-majuscules`, `--sans-minuscules`, `--sans-chiffres`, `--sans-symboles`. Le programme retourne le code 2 et un message si les options sont incohérentes (aucun type de caractère choisi, longueur invalide).

---

## Workflow Git

Le projet suit une organisation par branches :

```text
main        version stable
 └── dev    intégration : tout est testé ici avant de passer sur main
      └── feat/...   une branche par fonctionnalité (generateur, dashboard, coffre, formulaire, recherche, exe)
```

Cycle de travail :

```powershell
git switch dev
git pull
git switch -c feat/ma-fonctionnalite     # nouvelle branche de travail

# ... écrire du code et des tests ...
python -m unittest -v                    # tout doit être OK

git status
git add fichier1 fichier2
git commit -m "feat: description courte"
git push -u origin feat/ma-fonctionnalite
```

Puis, sur GitHub : ouvrir un *pull request* **dont la base est `dev`** (le lien proposé par `git push` vise `main` : ne pas l'utiliser tel quel), le fusionner, et revenir en local :

```powershell
git switch dev
git pull
python -m unittest -v
```

Quand `dev` est stable, le passer sur `main` sans commit de fusion superflu :

```powershell
git switch main
git pull
git merge --ff-only dev
git push
```

Conventions de messages de commit : `feat:` (nouvelle fonctionnalité), `fix:` (correction), `docs:` (documentation), `chore:` (maintenance), `test:` (tests).

Astuce : si le terminal reste bloqué sur `(END)` après une commande Git, appuyer sur `q`. Pour ne plus avoir ce comportement : `git config --global core.pager cat`.

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'candidatures'` (ou `db`, `sites`…) | Fichier absent, mal nommé (`.txt` caché) ou commande lancée hors du dossier du projet. | `dir *.py` ; vérifier les extensions ; se placer dans le dossier du projet. |
| `ModuleNotFoundError: No module named 'flask'` | Environnement virtuel non activé ou dépendances non installées. | Activer `.venv`, puis `pip install -r requirements.txt`. |
| `TemplateNotFound: xxx.html` | Le fichier n'est pas dans `templates/`, ou son nom est incorrect (majuscule, extension cachée). | `dir templates` : cinq fichiers attendus (voir [Structure](#structure-du-projet)). |
| `BuildError: Could not build url for endpoint …` | Un gabarit appelle une route qui n'existe pas dans `app.py` (fichiers de versions différentes). | Vérifier que `app.py` et `templates/` viennent de la même version. |
| `sqlite3.OperationalError: no such column` | Base créée avec un ancien schéma. | Arrêter le serveur, supprimer `instance/candidatures.db`, relancer (puis `seed`). |
| `Address already in use` | Un autre serveur occupe le port 5000. | Fermer l'autre instance (`Ctrl+C`) ; avec le lanceur, un port libre est choisi automatiquement. |
| `create_app() takes 0 positional arguments` | `app.py` est une ancienne version. | Remplacer par la version courante. |
| Fichiers barrés dans VS Code | Fichier supprimé du disque, souvent après un changement de branche (il n'existe que sur l'autre branche). | `git switch` vers la bonne branche ; fermer puis rouvrir les onglets. |
| `L'exécution de scripts est désactivée` à l'activation de `.venv` | Politique d'exécution PowerShell. | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` (valable pour la session). |
| Le terminal reste figé sur `(END)` | Pager de Git. | Appuyer sur `q`. |

---

## Limites et pistes d'amélioration

- **Authentification** : ajouter une connexion par mot de passe maître, puis brancher `coffre.py` pour chiffrer les identifiants des sites (clé dérivée du mot de passe maître, conservée en mémoire côté serveur avec expiration).
- **Relances** : champ « relancer le… » avec mise en évidence des relances en retard.
- **Recherche et tri** : filtrer par texte (entreprise, technologie), trier par colonne.
- **Bouton « Copier »** sur les mots de passe, avec effacement du presse-papiers.
- **Export** des candidatures en CSV.
- **Tests de bout en bout** dans un vrai navigateur (le comportement « afficher au clic » des mots de passe repose sur du JavaScript, actuellement vérifié à la main).
- **Migrations de base** : aujourd'hui, un changement de schéma suppose de recréer la base.
- **Signature du `.exe`** pour éviter l'avertissement SmartScreen.

---

## Licence

Aucune licence n'est définie pour le moment : par défaut, tous droits réservés. Ajouter un fichier `LICENSE` pour autoriser la réutilisation du code.