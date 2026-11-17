# Atelier 0 — Installation du poste

`30 min` `Aucun code à écrire` 

L'atelier 0 n'a pas de « solution » à proprement parler : il s'agit d'obtenir un poste qui fonctionne.
Ce corrigé donne le déroulé complet, **ce que chaque étape doit afficher**, et comment le vérifier.

## 1. Forker et cloner

```bash
git clone git@github.com:<vous>/cicd-ia-labs.git && cd cicd-ia-labs
git checkout -b <prenom>
```

Contrôle : `git remote -v` affiche **votre** compte, pas celui du formateur, et `git branch` marque
votre branche d'une étoile.

> **L'erreur classique**
>
>
> Cloner le dépôt du formateur au lieu de son propre fork. Tout fonctionne en local, puis le premier
> `git push` est refusé. Corriger avec `git remote set-url origin git@github.com:<vous>/cicd-ia-labs.git`.

Le dépôt est le même pour tous. L'application Python est à la racine ; les déclinaisons sont dans
`declinaisons/php/`, `declinaisons/java/`, `declinaisons/node/` et `declinaisons/csharp/`.

## 2. Installer les dépendances

**Linux / macOS / WSL**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m playwright install --with-deps chromium
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m playwright install chromium
```

Contrôles :

| Commande | Résultat attendu |
|---|---|
| l'invite du terminal | commence par `(.venv)` |
| `python --version` | 3.11 ou plus |
| `pip show pytest` | affiche une version et un emplacement **dans `.venv`** |
| `pytest --version` | répond sans erreur |

## 3. Lancer l'application

```bash
uvicorn minishop.api:app --reload          # ou : make run
```

Le terminal affiche `Uvicorn running on http://127.0.0.1:8000`.

Quel que soit le langage, l'application répond sur le port 8000 : n'en lancez qu'une à la fois. Si la
commande occupe le terminal, laissez-le ouvert et utilisez-en un second pour la suite.

| Adresse | Ce que vous devez voir |
|---|---|
| <http://localhost:8000> | La boutique, avec cinq produits |
| <http://localhost:8000/docs> | La documentation interactive de l'API |
| <http://localhost:8000/health> | `{"status":"ok","version":"…"}` |

## 4. Lancer les tests fournis

```bash
pytest -m "not e2e and not visual"
```

```text
5 passed, 3 deselected
```

- **5 tests passent** : 3 tests unitaires des règles de prix et 2 tests d'API.
- **3 sont désélectionnés** : les tests navigateur (`e2e`, `visual`), qui ont besoin de l'application
  lancée.

Pour vérifier aussi la chaîne navigateur, application lancée dans l'autre terminal :

```bash
pytest -m e2e
```

## 5. Activer les GitHub Actions

Sur **votre fork** : onglet *Actions* → bouton vert « I understand my workflows, go ahead and enable
them ». Sans cette étape, aucun pipeline ne se déclenchera à l'atelier 2.

## 6. Accès à l'IA

Les outils du dossier `ai_tools/` sont des scripts Python, quel que soit le langage de l'application :
l'environnement Python de l'onglet « Python » de l'étape 2 est donc nécessaire à tous pour cette étape.

**Linux / macOS / WSL**

```bash
export LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=<clé fournie par le formateur>
python ai_tools/llm.py
```

**Windows (PowerShell)**

```powershell
$env:LLM_PROVIDER = "anthropic"; $env:ANTHROPIC_API_KEY = "<clé fournie par le formateur>"
python ai_tools/llm.py
```

Le script envoie une question au modèle et affiche sa réponse. Sans configuration, il indique que le
mode `offline` est actif : les ateliers restent faisables, avec des moteurs de secours.

> **La clé ne se commite jamais**
>
>
> Elle se définit dans le terminal, pas dans un fichier du dépôt. `export` ne vaut que pour le
> terminal courant : il faut la redéfinir dans chaque nouveau terminal.

## Liste de contrôle finale

- [x] La boutique s'affiche sur <http://localhost:8000>, la documentation sur `/docs`
- [x] Les tests fournis sont verts
- [x] Les Actions sont activées sur le fork
- [x] `python ai_tools/llm.py` répond (ou vous savez que vous êtes en mode `offline`)
- [x] `docker --version` répond : Docker servira à partir de l'atelier 10

## Si quelque chose ne marche pas

| Symptôme | Cause la plus fréquente |
|---|---|
| `Address already in use`, ou le port 8000 est occupé | Une autre instance de l'application tourne déjà, peut-être dans un autre langage |
| `Permission denied (publickey)` au clone | Clé SSH absente de votre compte GitHub : clonez en HTTPS |

Et selon le langage :

| Symptôme | Cause la plus fréquente |
|---|---|
| `ModuleNotFoundError: No module named 'pytest'` | Environnement virtuel non activé dans ce terminal |
| `No module named 'minishop'` | Commande lancée hors de la racine du dépôt |
| `Executable doesn't exist` (Playwright) | `python -m playwright install chromium` n'a pas été lancé |
